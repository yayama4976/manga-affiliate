import datetime, os
import requests

RANKING_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20170628"
GENRES = {"家電": "211742", "日用品": "215783", "インテリア・寝具": "100804",
          "ダイエット・健康": "100938", "美容・コスメ": "100939", "食品": "100227"}
SEASON = {10: ["加湿", "ヒーター", "毛布", "乾燥"], 11: ["ヒーター", "毛布", "おせち", "ギフト"],
          12: ["おせち", "福袋", "ギフト", "大掃除"]}
POSTS_PER_RUN = 3


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
    if os.environ.get("TEST_MODE"):   # 楽天IDなしで漫画生成だけ試すテストモード
        return [{"itemCode": "test:001", "itemName": "超音波式 卓上加湿器 6畳対応(テスト商品)",
                 "itemPrice": 3980, "reviewAverage": 4.5, "reviewCount": 120,
                 "genre": "家電", "affiliateUrl": "#", "itemUrl": "#"}]
    pool = []
    for name, gid in GENRES.items():
        for it in fetch_ranking(gid):
            if it["itemCode"] not in posted and it.get("reviewAverage", 0) >= 4.0:
                it["genre"] = name
                pool.append(it)
    return sorted(pool, key=score, reverse=True)[:POSTS_PER_RUN]
