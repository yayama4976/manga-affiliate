import base64, io, os, re
import requests

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
ASK = ("この画像に、文字・吹き出し・効果音の文字・看板の文字が描かれていますか。"
       "読めなくても文字らしきものがあればyes、なければno。yesかnoだけ答えて。")
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
    """絵に文字や吹き出しが描かれていれば True。判定できないときは False"""
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=70)
    data = base64.b64encode(buf.getvalue()).decode()
    body = {"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": data}},
                                    {"text": ASK}]}]}
    try:
        for m in models():
            url = f"{BASE}/{m}:generateContent?key={os.environ['GEMINI_API_KEY']}"
            r = requests.post(url, json=body, timeout=60)
            if r.status_code != 200:
                continue
            parts = r.json()["candidates"][0]["content"]["parts"]
            ans = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip().lower()
            print("text check:", ans[:8])
            return ans.startswith("y")
    except Exception as e:
        print("text check error:", type(e).__name__)
    return False
