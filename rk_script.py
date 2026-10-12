import json, os, re
import requests
from rk_prompt import build_prompt

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def list_models():
    """使えるflash系モデルを、使いやすい順に並べる"""
    r = requests.get(BASE, timeout=30,
                     params={"key": os.environ["GEMINI_API_KEY"], "pageSize": 200})
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    bad = ("lite", "image", "tts", "live", "audio", "thinking", "exp",
           "latest", "robotics", "omni")
    flash = [n for n in names if re.match(r"gemini-\d", n) and "flash" in n
             and not any(b in n for b in bad)]
    ver = lambda n: tuple(int(x) for x in re.findall(r"\d+", n))
    plain = sorted([n for n in flash if "preview" not in n], key=ver, reverse=True)
    prev = sorted([n for n in flash if "preview" in n], key=ver, reverse=True)
    pool = (plain + prev)[:6]
    print("candidates:", pool)
    return pool


def write_script(it):
    prompt = build_prompt(it)
    last = None
    for model in list_models():
        url = f"{BASE}/{model}:generateContent?key={os.environ['GEMINI_API_KEY']}"
        try:
            r = requests.post(url, timeout=90, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.8}})
        except requests.RequestException as e:
            print("model error:", model, type(e).__name__)
            last = "network"
            continue
        if r.status_code != 200:
            print("model skipped:", model, r.status_code)
            last = r.status_code
            continue
        try:
            parts = r.json()["candidates"][0]["content"]["parts"]
            data = json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))
        except Exception as e:
            print("bad response:", model, type(e).__name__)
            last = "format"
            continue
        print("gemini model:", model)
        return data
    raise RuntimeError(f"使えるモデルがありません(最後のエラー: {last})")
