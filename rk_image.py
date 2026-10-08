import base64, io, os, re, time
import requests
from PIL import Image

STYLE = ("classic hand-drawn Japanese anime illustration, clean outlines, warm natural colors, "
         "soft lighting, simple minimal background with plain walls, medium close-up of the characters")
HERO = ("Takumi, a 30-year-old Japanese man, short messy wavy dark brown hair, thick eyebrows, "
        "small goatee on the chin, warm tan skin, gentle smile, beige crew-neck t-shirt")
NEKO = ("Neko-tencho, a chubby gray tabby cat with a red collar and a small gold bell, "
        "smug half-closed eyes")
_checked = []


def clean_token(raw):
    """貼り付けに余計な文字(Bearer, 引用符など)が混ざっていても、トークン本体だけ取り出す"""
    runs = re.findall(r"[A-Za-z0-9_\-]{30,}", raw)
    return runs[-1] if runs else "".join(raw.split())


def diag(acct, raw, token):
    """原因調査用: 長さと有効性だけを表示(値は表示しない)"""
    if _checked:
        return
    _checked.append(1)
    extra = sorted(set(re.findall(r"[^A-Za-z0-9_\-\s]", raw)))
    print("diag len acct/raw/token:", len(acct), len(raw), len(token), "extra chars:", extra)
    try:
        v = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        print("diag verify:", v.status_code, v.text[:150])
    except Exception as e:
        print("diag verify error:", type(e).__name__)


def gen_image(scene, path):
    scene = scene.replace("hero", HERO).replace("Hero", HERO).replace("neko", NEKO).replace("Neko", NEKO)
    acct = "".join(os.environ["CF_ACCOUNT_ID"].split())
    raw = os.environ["CF_API_TOKEN"]
    token = clean_token(raw)
    diag(acct, raw, token)
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}"
           "/ai/run/@cf/black-forest-labs/flux-1-schnell")
    head = {"Authorization": f"Bearer {token}"}
    for attempt in range(3):
        try:
            r = requests.post(url, timeout=120, headers=head,
                              json={"prompt": f"{STYLE}. {scene}", "steps": 6})
            if r.status_code in (401, 403):
                print("image auth error:", r.status_code, r.text[:200])
                return False
            r.raise_for_status()
            img = Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"])))
            img = img.convert("RGB")
            img.thumbnail((640, 640))
            img.save(path, "WEBP", quality=80)
            return True
        except Exception as e:
            print("image retry:", e)
            time.sleep(5)
    return False
