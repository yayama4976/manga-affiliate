import base64, io, os, time
import requests
from PIL import Image

STYLE = ("classic hand-drawn Japanese anime style, 4-koma comic panel, clean outlines, "
         "warm natural colors, soft lighting, detailed everyday background, "
         "no text, no letters, no speech bubbles")
HERO = ("Takumi, a 30-year-old Japanese man, short messy wavy dark brown hair, thick eyebrows, "
        "small goatee on the chin, warm tan skin, gentle smile, beige crew-neck t-shirt")
NEKO = ("Neko-tencho, a chubby gray tabby cat with a red collar and a small gold bell, "
        "smug half-closed eyes")
_checked = []


def diag(acct, token):
    """原因調査用: 長さとトークンの有効性だけを表示(値は表示しない)"""
    if _checked:
        return
    _checked.append(1)
    print("diag len acct/token:", len(acct), len(token))
    try:
        v = requests.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                         headers={"Authorization": f"Bearer {token}"}, timeout=20)
        print("diag verify:", v.status_code, v.text[:150])
    except Exception as e:
        print("diag verify error:", type(e).__name__)


def gen_image(scene, path):
    scene = scene.replace("hero", HERO).replace("Hero", HERO).replace("neko", NEKO).replace("Neko", NEKO)
    acct = "".join(os.environ["CF_ACCOUNT_ID"].split())
    token = "".join(os.environ["CF_API_TOKEN"].split())
    diag(acct, token)
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
