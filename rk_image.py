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
HERO = ("Takumi, a 30-year-old Japanese man, short messy wavy dark brown hair, thick eyebrows, "
        "small goatee on the chin, warm tan skin, gentle smile, beige crew-neck t-shirt")
NEKO = ("Neko-tencho, a chubby gray tabby cat with a red collar and a small gold bell, "
        "smug half-closed eyes")
_quota = []   # Cloudflareの上限(429)に達したら、以降の画像生成を止める


def clean_token(raw):
    """貼り付けに余計な文字(Bearer, 引用符など)が混ざっていても、トークン本体だけ取り出す"""
    runs = re.findall(r"[A-Za-z0-9_\-]{30,}", raw)
    return runs[-1] if runs else "".join(raw.split())


def gen_image(scene, path):
    if _quota:
        return False
    scene = BAN.sub("", QUOTED.sub("", scene))
    scene = re.sub(r"\s{2,}", " ", DANGLE.sub("", scene)).strip()
    scene = scene.replace("hero", HERO).replace("Hero", HERO).replace("neko", NEKO).replace("Neko", NEKO)
    acct = "".join(os.environ["CF_ACCOUNT_ID"].split())
    raw = os.environ["CF_API_TOKEN"]
    token = clean_token(raw)
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}"
           "/ai/run/@cf/black-forest-labs/flux-1-schnell")
    head = {"Authorization": f"Bearer {token}"}
    redrawn = False
    for attempt in range(4):
        try:
            r = requests.post(url, timeout=120, headers=head,
                              json={"prompt": f"{STYLE}. {scene}", "steps": 6})
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
            if not redrawn and has_text(img):   # 文字や吹き出しが描かれていたら1回だけ描き直す
                redrawn = True
                print("text in image, redraw")
                continue
            img.save(path, "WEBP", quality=80)
            return True
        except Exception as e:
            print("image retry:", type(e).__name__, str(e)[:150])
            time.sleep(5)
    return False
