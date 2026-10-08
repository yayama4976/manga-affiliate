import datetime, json, os
from rk_items import pick_items
from rk_script import write_script
from rk_image import gen_image
from rk_page import page_html, rebuild_index

DOCS = "docs"


def main():
    os.makedirs(f"{DOCS}/posts", exist_ok=True)
    posted = json.load(open("posted.json")) if os.path.exists("posted.json") else []
    meta = f"{DOCS}/posts.json"
    posts = json.load(open(meta, encoding="utf-8")) if os.path.exists(meta) else []
    for it in pick_items(posted):
        try:
            d = write_script(it)
            slug = f"{datetime.date.today():%Y%m%d}-{it['itemCode'].replace(':', '-')}"
            os.makedirs(f"{DOCS}/posts/{slug}", exist_ok=True)
            oks = [gen_image(p["image_prompt"], f"{DOCS}/posts/{slug}/p{i+1}.webp")
                   for i, p in enumerate(d["panels"][:4])]
            if not all(oks):
                print("skip (image failed):", slug)
                continue
            with open(f"{DOCS}/posts/{slug}/index.html", "w", encoding="utf-8") as f:
                f.write(page_html(it, d, oks))
            posts.append({"slug": slug, "title": d["title"], "date": str(datetime.date.today())})
            posted.append(it["itemCode"])
            print("generated:", slug)
        except Exception as e:
            print("skip:", it["itemCode"], e)
    json.dump(posted, open("posted.json", "w"))
    json.dump(posts, open(meta, "w", encoding="utf-8"), ensure_ascii=False)
    rebuild_index(posts, DOCS)


if __name__ == "__main__":
    main()
