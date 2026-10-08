"""
楽天アフィリエイト全自動システム【無料構成】
  台本生成 : Google Gemini API 無料枠
  漫画の絵 : Cloudflare Workers AI の FLUX.1 [schnell] (無料枠 約230枚/日, Apache-2.0)
  サイト   : GitHub Pages (docs/ に静的HTML生成)
  実行     : GitHub Actions (cron)  ※公開リポジトリなら無料
  商品写真 : 楽天APIの実物写真を3コマ目に合成 / セリフはHTMLで重ねる(AIは日本語が崩れるため)

テスト: TEST_MODE=1 を付けると楽天IDなしで1本だけ生成(商品写真は入りません)
環境変数: RAKUTEN_APP_ID, RAKUTEN_AFFILIATE_ID, GEMINI_API_KEY, CF_ACCOUNT_ID, CF_API_TOKEN, SITE_URL
依存: pip install requests pillow
※無料枠の上限・規約・楽天APIの仕様は変わるため、運用前に最新を確認してください
"""
import base64, datetime, html, io, json, os, re, time
import requests
from PIL import Image

RANKING_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20170628"
GENRES = {"家電": "211742", "日用品": "215783", "インテリア・寝具": "100804",
          "ダイエット・健康": "100938", "美容・コスメ": "100939", "食品": "100227"}
SEASON = {10: ["加湿", "ヒーター", "毛布", "乾燥"], 11: ["ヒーター", "毛布", "おせち", "ギフト"],
          12: ["おせち", "福袋", "ギフト", "大掃除"]}
POSTS_PER_RUN = 3
DOCS = "docs"

# ---- キャラ固定: 毎回同じ説明文を画像プロンプトに付けて一貫性を保つ ----
STYLE = ("classic hand-drawn Japanese anime style, 4-koma comic panel, clean outlines, warm natural colors, "
         "soft lighting, detailed everyday background, no text, no letters, no speech bubbles")
HERO = ("Takumi, a 30-year-old Japanese man, short messy wavy dark brown hair, thick eyebrows, "
        "small goatee on the chin, warm tan skin, gentle smile, beige crew-neck t-shirt")
NEKO = "Neko-tencho, a chubby gray tabby cat with a red collar and a small gold bell, smug half-closed eyes"


# ================= 商品選定 =================
def fetch_ranking(gid):
    r = requests.get(RANKING_URL, timeout=20, params={
        "applicationId": os.environ["RAKUTEN_APP_ID"],
        "affiliateId": os.environ["RAKUTEN_AFFILIATE_ID"], "genreId": gid, "format": "json"})
    r.raise_for_status()
    return [i["Item"] for i in r.json().get("Items", [])]


def score(it):
    s = (31 - it.get("rank", 30)) * 2 + min(it.get("reviewCount", 0), 1000) / 50
    s += max(it.get("reviewAverage", 0) - 4.0, 0) * 10
    if any(k in it["itemName"] for k in SEASON.get(datetime.date.today().month, [])):
        s += 15
    return s


def pick_items(posted):
    if os.environ.get("TEST_MODE"):   # 楽天ID未取得でも漫画生成だけ試せるテストモード
        return [{"itemCode": "test:001", "itemName": "超音波式 卓上加湿器 6畳対応(テスト商品)", "itemPrice": 3980,
                 "reviewAverage": 4.5, "reviewCount": 120, "genre": "家電", "affiliateUrl": "#", "itemUrl": "#"}]
    pool = []
    for name, gid in GENRES.items():
        for it in fetch_ranking(gid):
            if it["itemCode"] not in posted and it.get("reviewAverage", 0) >= 4.0:
                it["genre"] = name
                pool.append(it)
    return sorted(pool, key=score, reverse=True)[:POSTS_PER_RUN]


# ================= 台本 (Gemini 無料枠) =================
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
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"gemini-2.5-flash:generateContent?key={os.environ['GEMINI_API_KEY']}")
    r = requests.post(url, timeout=90, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}})
    r.raise_for_status()
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])


# ================= 画像 (Cloudflare FLUX 無料枠) =================
def gen_image(scene, path):
    scene = scene.replace("hero", HERO).replace("Hero", HERO).replace("neko", NEKO).replace("Neko", NEKO)
    url = (f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID']}"
           "/ai/run/@cf/black-forest-labs/flux-1-schnell")
    for attempt in range(3):
        try:
            r = requests.post(url, timeout=120, headers={"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"},
                              json={"prompt": f"{STYLE}. {scene}", "steps": 6})
            r.raise_for_status()
            img = Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"]))).convert("RGB")
            img.thumbnail((640, 640))
            img.save(path, "WEBP", quality=80)   # 容量節約(リポジトリ肥大化防止)
            return True
        except Exception as e:
            print("image retry:", e)
            time.sleep(5)
    return False


# ================= HTML生成 (セリフ重ね + 実物写真合成) =================
BUBBLE_POS = ["top:8px;left:8px", "top:52%;right:8px"]
BUBBLE_POS_P3 = ["bottom:8px;left:8px", "bottom:70px;right:8px"]
CHAR = {"hero": ("タクミ", "#fff3b0"), "neko": ("ネコ店長", "#d6f0ff")}


def photo_url(it):
    imgs = it.get("mediumImageUrls") or []
    u = imgs[0].get("imageUrl", "") if imgs else ""
    return re.sub(r"\?_ex=\d+x\d+", "?_ex=500x500", u)


def panel_html(i, p, ok, it, link):
    pos = BUBBLE_POS_P3 if i == 2 else BUBBLE_POS
    bg = f'<img src="p{i+1}.webp" alt="" style="width:100%;display:block">' if ok else \
         '<div style="aspect-ratio:1;background:#eee"></div>'
    bubbles = ""
    for ln, ps in zip(p["lines"][:2], pos):
        name, color = CHAR.get(ln["who"], CHAR["hero"])
        bubbles += (f'<div style="position:absolute;{ps};max-width:58%;background:{color};color:#222;'
                    f'border:2.5px solid #222;border-radius:16px;padding:6px 10px;font-size:14px;'
                    f'font-weight:700;line-height:1.45"><small>{name}</small><br>{html.escape(ln["text"])}</div>')
    photo = ""
    if i == 2 and photo_url(it):   # 3コマ目: 楽天の実物写真をそのまま合成
        photo = (f'<a href="{link}" rel="nofollow sponsored" target="_blank" style="position:absolute;'
                 f'left:50%;top:8%;transform:translateX(-50%);width:44%;background:#fff;border:3px solid #222;'
                 f'border-radius:8px;padding:4px"><img src="{photo_url(it)}" alt="商品写真" '
                 f'style="width:100%;display:block"></a>')
    cap = (f'<div style="position:absolute;left:0;right:0;bottom:0;background:#222;color:#fff;'
           f'text-align:center;font-size:13px;padding:6px">{html.escape(p["caption"])}</div>'
           if p.get("caption") else "")
    return (f'<div style="position:relative;border:3px solid #222;overflow:hidden;background:#fff">'
            f'{bg}{photo}{bubbles}{cap}</div>')


def page_html(it, d, oks):
    link = it["affiliateUrl"] or it["itemUrl"]
    grid = "".join(panel_html(i, p, oks[i], it, link) for i, p in enumerate(d["panels"][:4]))
    pts = "".join(f"<li>{html.escape(x)}</li>" for x in d["points"])
    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d['title'])}</title>
<style>body{{font-family:"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7;max-width:720px;margin:0 auto;padding:16px}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:8px;background:#222;padding:8px}}
.c{{display:block;width:fit-content;margin:20px auto;background:#bf0000;color:#fff;padding:14px 28px;
border-radius:6px;text-decoration:none;font-weight:bold}}</style></head><body>
<p><small>※本記事はプロモーション(アフィリエイト広告)を含みます。画像の一部はAIで生成しています。</small></p>
<h1>{html.escape(d['title'])}</h1><div class="g">{grid}</div>
<h2>選ぶポイント</h2><ul>{pts}</ul>
<p><b>向いている人:</b>{html.escape(d['for'])}<br><b>向かない人:</b>{html.escape(d['not_for'])}</p>
<p><small>参考価格 {it['itemPrice']:,}円 / レビュー {it['reviewAverage']}({it['reviewCount']}件)※掲載時点</small></p>
<a class="c" href="{link}" rel="nofollow sponsored" target="_blank">楽天市場で価格・在庫を見る</a>
<p><a href="../../index.html">← 記事一覧へ</a></p></body></html>"""


def rebuild_index(posts):
    items = "".join(f'<li><a href="posts/{p["slug"]}/index.html">{html.escape(p["title"])}</a> '
                    f'<small>{p["date"]}</small></li>' for p in reversed(posts))
    open(f"{DOCS}/index.html", "w", encoding="utf-8").write(
        '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>4コマでわかる!おすすめ商品</title></head>'
        f'<body style="font-family:sans-serif;max-width:720px;margin:0 auto;padding:16px">'
        f'<h1>4コマでわかる!おすすめ商品</h1><p><small>※当サイトはアフィリエイト広告を含みます</small></p>'
        f'<ul>{items}</ul></body></html>')


# ================= メイン =================
def main():
    os.makedirs(f"{DOCS}/posts", exist_ok=True)
    posted = json.load(open("posted.json")) if os.path.exists("posted.json") else []
    meta_path = f"{DOCS}/posts.json"
    posts = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else []
    for it in pick_items(posted):
        try:
            d = write_script(it)
            slug = f"{datetime.date.today():%Y%m%d}-{it['itemCode'].replace(':', '-')}"
            os.makedirs(f"{DOCS}/posts/{slug}", exist_ok=True)
            oks = [gen_image(p["image_prompt"], f"{DOCS}/posts/{slug}/p{i+1}.webp")
                   for i, p in enumerate(d["panels"][:4])]
            if not all(oks):          # 絵が欠けた記事は公開しない
                print("skip (image failed):", slug)
                continue
            open(f"{DOCS}/posts/{slug}/index.html", "w", encoding="utf-8").write(page_html(it, d, oks))
            posts.append({"slug": slug, "title": d["title"], "date": str(datetime.date.today())})
            posted.append(it["itemCode"])
            print("generated:", slug)
        except Exception as e:
            print("skip:", it["itemCode"], e)
    json.dump(posted, open("posted.json", "w"))
    json.dump(posts, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False)
    rebuild_index(posts)


if __name__ == "__main__":
    main（）
