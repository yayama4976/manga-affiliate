import base64, io, os, re
import requests

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ASK = ("この画像に、吹き出し(セリフの枠)、または大きな文字・効果音の文字が描かれていますか。"
       "背景の小さな文字や、画面・本の表示は無視してください。yesかnoだけ答えて。")
_models = []


def models():
    if not _models:
        r = requests.get(BASE, timeout=30,
                         params={"key": os.environ["GEMINI_API_KEY"], "pageSize": 200})
        names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        bad = ("lite", "image", "tts", "live", "audio", "thinking", "exp", "latest", "robotics", "omni")
        ok = [n for n in names if re.match(r"gemini-\d", n) and "flash" in n
              and not any(b in n for b in bad)]
        ver = lambda n: tuple(int(x) for x in re.findall(r"\d+", n))
        _models.extend(sorted(ok, key=ver, reverse=True)[:6])
    return _models


def has_text(img):
    """絵に吹き出しや大きな文字があれば True。判定できないときは False(止めない)"""
    small = img.copy()
    small.thumbnail((384, 384))
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=70)
    data = base64.b64encode(buf.getvalue()).decode()
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": data}},
                                    {"text": ASK}]}]}
    try:
        names = models()[:3]
    except Exception as e:
        print("text check error:", type(e).__name__)
        return False
    for m in names:
        url = f"{BASE}/{m}:generateContent?key={os.environ['GEMINI_API_KEY']}"
        try:
            r = requests.post(url, json=body, timeout=25)
        except requests.RequestException as e:
            print("text check error:", m, type(e).__name__)
            continue
        if r.status_code != 200:
            continue
        try:
            parts = r.json()["candidates"][0]["content"]["parts"]
        except Exception:
            continue
        ans = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip().lower()
        print("text check:", ans[:8])
        return ans.startswith("y")
    return False
