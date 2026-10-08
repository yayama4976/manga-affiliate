import datetime, os
import requests

# 楽天APIは2026年に刷新(旧app.rakuten.co.jp系は廃止)。新: applicationId + accessKey + Referer
SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
SITE = "https://yayama4976.github.io/manga-affiliate/"
KEYWORDS = {
    10: ["加湿器", "電気毛布", "セラミックヒーター", "ハンドクリーム", "着る毛布"],
    11: ["電気毛布", "ホットカーペット", "おせち", "ギフト", "家電 ブラックフライデー"],
    12: ["福袋", "おせち", "大掃除 洗剤", "ホットカーペット", "ギフト"],
}
DEFAULT = ["加湿器", "ブランケット", "収納ボックス", "掃除グッズ", "コーヒー"]
POSTS_PER_RUN = 3


def search(keyword):
    r = requests.get(SEARCH_URL, timeout=20,
                     headers={"Referer": os.environ.get("SITE_URL") or SITE},
                     params={"applicationId": os.environ["RAKUTEN_APP_ID"].strip(),
                             "accessKey": os.environ["RAKUTEN_ACCESS_KEY"].strip(),
                             "affiliateId": os.environ["RAKUTEN_AFFILIATE_ID"].strip(),
                             "keyword": keyword, "hits": 20, "sort": "-reviewCount",
                             "format": "json", "formatVersion": 2})
    if r.status_code != 200:
        print("rakuten error:", keyword, r.status_code, r.text[:200])
    r.raise_for_status()
    return [i.get("Item", i) for i in r.json().get("Items", [])]


def num(it, key):
    try:
        return float(it.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def score(it):
    return min(num(it, "reviewCount"), 2000) / 40 + max(num(it, "reviewAverage") - 4.0, 0) * 20


def pick_items(posted):
    if os.environ.get("TEST_MODE"):   # 楽天IDなしで漫画生成だけ試すテストモード
        return [{"itemCode": "test:001", "itemName": "超音波式 卓上加湿器 6畳対応(テスト商品)",
                 "itemPrice": 3980, "reviewAverage": 4.5, "reviewCount": 120,
                 "genre": "家電", "affiliateUrl": "#", "itemUrl": "#"}]
    month = datetime.date.today().month
    picks, seen = [], set(posted)
    for kw in KEYWORDS.get(month, DEFAULT):
        try:
            cands = [it for it in search(kw) if it.get("itemCode") not in seen
                     and num(it, "reviewAverage") >= 4.2 and num(it, "reviewCount") >= 30]
        except Exception as e:
            print("search skip:", kw, type(e).__name__)
            continue
        if cands:
            best = max(cands, key=score)
            best["genre"] = kw
            seen.add(best["itemCode"])
            picks.append(best)
    return sorted(picks, key=score, reverse=True)[:POSTS_PER_RUN]
