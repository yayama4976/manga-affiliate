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
def pick_model():
    """使えるGeminiのflash系モデルを自動で探す(モデル名の変更に強くする)"""
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", timeout=30,
                     params={"key": os.environ["GEMINI_API_KEY"], "pageSize": 200})
    r.raise_for_status()
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    bad = ("lite", "image", "tts", "live", "aud
