import json, os
import requests


def pick_model():
    """使えるGeminiのflash系モデルを自動で探す"""
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", timeout=30,
                     params={"key": os.environ["GEMINI_API_KEY"], "pageSize": 200})
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    bad = ("lite", "image", "tts", "live", "audio", "thinking", "exp", "latest", "robotics")
    flash = [n for n in names if "flash" in n and not any(b in n for b in bad)]
    stable = sorted([n for n in flash if "preview" not in n], reverse=True)
    preview = sorted([n for n in flash if "preview" in n], reverse=True)
    pool = stable + preview
    if not pool:
        raise RuntimeError("flashモデルが見つかりません: " + ", ".join(names[:15]))
    print("gemini model:", pool[0])
    return pool[0]


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
    model = pick_model()
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={os.environ['GEMINI_API_KEY']}")
    r = requests.post(url, timeout=90, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}})
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))
