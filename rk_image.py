import base64, io, os, re, time
import requests
from PIL import Image
from rk_check import has_text

STYLE = ("classic hand-drawn Japanese anime illustration, clean outlines, "
         "warm natural colors, soft lighting, detailed everyday background")
BAN = re.compile(r"\b((speech|thought|dialogue)\s+bubbles?|word\s+balloons?|captions?|"
                 r"sound\s+effects?|onomatopoeia|subtitles?|signs?|text|letters?|writing|"
                 r"manga|comic|4-koma|panels?|"
                 r"say|says|saying|said|shout\w*|yell\w*|exclaim\w*|whisper\w*|mutter\w*)\b", re.I)
DANGLE = re.compile(r"\b(with an?|and|while|that|who)\s*(?=[,.;]|$)", re.I)
QUOTED = re.compile(r'["\u201c\u201d][^"\u201c\u201d]*["\u201c\u201d]')
APPEAR = re.compile(r"\b(wearing|dressed in)\b[^,.;]*|"
                    r"\b(orange|ginger|calico|tabby|striped|spotted|brown|black|white|"
                    r"gray|grey|silver|blonde|blond|blue|green|red|pink|purple|yellow)\b", re.I)
WHO_MAN = re.compile(r"hero|takumi|\b(man|guy|male|boy|he|his|him|person|worker)\b", re.I)
WHO_CAT = re.compile(r"neko|\b(cat|cats|kitten|feline)\b", re.I)
HERO = ("Takumi, a 30-year-old Japanese man, short messy wavy dark brown hair, thick eyebrows, "
        "small goatee on the chin, warm tan skin, gentle smile, beige crew-neck t-shirt")
NEKO = ("Neko-tencho, a chubby gray tabby cat with a red collar and a small gold bell, "
        "smug half-closed eyes")
_quota = []


def clean_token(raw):
    runs = re.findall(r"[A-Za-z0-9_\-]{30,}", raw)
    return runs[-1] if runs else "".join(raw.split())


def build_prompt(scene):
    scene = BAN.sub("", QUOTED.sub("", scene))
    scene = re.sub(r"\s{2,}", " ", DANGLE.sub("", scene)).strip()
    cast = []
    if WHO_MAN.search(scene):
        cast.append(HERO)
    if WHO_CAT.search(scene):
        cast.append(NEKO)
    if not cast:
        cast = [HERO, NEKO]
    scene = APPEAR.sub("", scene)
    scene = re.sub(r"(?i)hero", "Takumi", scene)
    scene = re.sub(r"(?i)neko", "Neko-tencho", scene)
    scene = re.sub(r"\s{2,}", " ", scene).strip()
    return f"{STYLE}. Characters: {' ; '.join(cast)}. Scene: {scene}"


def gen_image(scene, path):
    if _quota:
        return False
    full = build_prompt(scene)
    acct = "".join(os.environ["CF_ACCOUNT_ID"].split())
    token = clean_token(os.environ["CF_API_TOKEN"])
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}"
           "/ai/run/@cf/black-forest-labs/flux-1-schnell")
    head = {"Authorization": f"Bearer {token}"}
    redrawn = False
    for attempt in range(4):
        try:
            r = requests.post(url, timeout=120, headers=head,
                              json={"prompt": full, "steps": 6})
            if r.status_code == 429:
                print("Cloudflare 429: 無料枠の上限(または混雑)。画像づくりを止めます")
                _quota.append(1)
                return False
            if r.status_code in (401, 403):
                print("image auth error:", r.status_code, r.text[:200])
                return False
            if r.status_code != 200:
                print("image http error:", r.status_code, r.text[:200])
                time.sleep(5)
                continue
            img = Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"])))
            img = img.convert("RGB")
            img.thumbnail((640, 640))
            if not redrawn and has_text(img):
                redrawn = True
                print("text in image, redraw")
                continue
            img.save(path, "WEBP", quality=80)
            return True
        except Exception as e:
            print("image retry:", type(e).__name__, str(e)[:150])
            time.sleep(5)
    return False
