import datetime, os, re, time
import requests

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20220601"
SITE = "https://yayama4976.github.io/manga-affiliate/"
KEYWORDS = {
    10: ["加湿器", "電気毛布", "セラミックヒーター", "ハンドクリーム", "着る毛布"],
    11: ["電気毛布", "ホットカーペット", "おせち", "ギフト", "家電 ブラックフライデー"],
    12: ["福袋", "おせち", "大掃除 洗剤", "ホットカーペット", "ギフト"],
}
DEFAULT = ["加湿器", "ブランケット", "収納ボックス", "掃除グッズ", "コーヒー"]
POSTS_PER_RUN = 3


_shown = []
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
PK = re.compile(r"pk_[A-Za-z0-9_\-]+")


def creds():
    app, key, aff = (os.environ[k] for k in ("RAKUTEN_APP_ID", "RAKUTEN_ACCESS_KEY", "RAKUTEN_AFFILIATE_ID"))
    m_app = UUID.search(app) or UUID.search(key)
    m_key = PK.search(key) or PK.search(app)
    if not _shown:
        _shown.append(1)
        print("rakuten diag: uuid", bool(m_app), "pk", bool(m_key),
              "len", len(app.strip()), len(key.strip()), len(aff.strip()), "dot", "." in aff)
    return (m_app.group(0) if m_app else app.strip(),
            m_key.group(0) if m_key else key.strip(), aff.strip())


def search(keyword):
    app, key, aff = creds()
    params = {"applicationId": app, "accessKey": key, "affiliateId": aff,
              "keyword": keyword, "hits": 20, "sort": "-reviewCount",
              "format": "json", "formatVersion": 2}
    site = (os.environ.get("SITE_URL") or SITE).strip()
    origin = re.sub(r"^(https?://[^/]+).*", r"\1", site)
    for _ in range(3):
        time.sleep(1.3)   # QPS=1を守る
        r = requests.get(SEARCH_URL, timeout=20, params=params,
                         headers={"Referer": site, "Origin": origin})
        if r.status_code != 429:
            break
        print("rakuten 429: retry")
        time.sleep(2)
    if r.status_code != 200:
        print("rakuten error:", keyword, r.status_code, " ".join(r.text.split())[:140])
        raise RuntimeError(f"rakuten {r.status_code}")
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
