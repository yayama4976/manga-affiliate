import json, os, re
import requests

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
    pool = (plain + prev)[:5]
    print("candidates:", pool)
    return pool


def write_script(it):
    prompt = f"""楽天商品の紹介を4コマ漫画の台本にしてください。JSONのみ出力。
商品名: {it['itemName']} / 価格: {it['itemPrice']}円 / レビュー: {it['reviewAverage']}({it['reviewCount']}件)
キャラ: hero=ちょっとズボラな在宅ワーカーの男性 / neko=物知りで毒舌なネコ店長
構成: 1=悩み 2=深掘り・失敗談 3=商品登場 4=オチ
ルール: 各コマのセリフは最大2個・1個25字以内 / クスッと笑えるオチ /
誇大表現・効果効能の断定禁止 / 商品情報にない事実は書かない
image_promptは英語で、そのコマの情景・構図・表情を具体的に(文字は入れない、キャラ名は hero/neko と書く)
形式: {{"title":"悩み系キーワード入りタイトル",
"panels":[{{"image_prompt":"...","lines":[{{"who":"hero","text":"..."}}],"caption":""}}x4],
"points":["選ぶポイント3つ"],"for":"向く人","not_for":"向かない人"}}"""
    last = None
    for model in list_models():
        url = f"{BASE}/{model}:generateContent?key={os.environ['GEMINI_API_KEY']}"
        r = requests.post(url, timeout=90, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}})
        if r.status_code in (400, 403, 404, 429):
            print("model skipped:", model, r.status_code)
            last = r.status_code
            continue
        r.raise_for_status()
        parts = r.json()["candidates"][0]["content"]["parts"]
        print("gemini model:", model)
        return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))
    raise RuntimeError(f"使えるモデルがありません(最後のエラー: {last})")
