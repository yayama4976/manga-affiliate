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


def gen_image(scene, path):
    scene = scene.replace("hero", HERO).replace("Hero", HERO).replace("neko", NEKO).replace("Neko", NEKO)
    acct = "".join(os.environ["CF_ACCOUNT_ID"].split())
    token = "".join(os.environ["CF_API_TOKEN"].split())   # 改行・空白を全部除く
    url = (f"https://api.cloudflare.com/client/v4/accounts/{acct}"
           "/ai/run/@cf/black-forest-labs/flux-1-schnell")
    head = {"Authorization": f"Bearer {token}"}
    for attempt in range(3):
        try:
            r = requests.post(url, timeout=120, headers=head,
                              json={"prompt": f"{STYLE}. {scene}", "steps": 6})
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
