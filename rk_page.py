import html
from rk_panel import panel_html

CSS = ('body{font-family:"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.7;'
       'max-width:720px;margin:0 auto;padding:16px}'
       '.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));'
       'gap:8px;background:#222;padding:8px}'
       '.c{display:block;width:fit-content;margin:20px auto;background:#bf0000;color:#fff;'
       'padding:14px 28px;border-radius:6px;text-decoration:none;font-weight:bold}')
HEAD = ('<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">')


def page_html(it, d, oks):
    link = it["affiliateUrl"] or it["itemUrl"]
    t = html.escape(d["title"])
    grid = "".join(panel_html(i, p, oks[i], it, link) for i, p in enumerate(d["panels"][:4]))
    pts = "".join(f"<li>{html.escape(x)}</li>" for x in d["points"])
    return (f'{HEAD}<title>{t}</title><style>{CSS}</style></head><body>'
            '<p><small>※本記事はプロモーション(アフィリエイト広告)を含みます。'
            '画像の一部はAIで生成しています。</small></p>'
            f'<h1>{t}</h1><div class="g">{grid}</div><h2>選ぶポイント</h2><ul>{pts}</ul>'
            f'<p><b>向いている人:</b>{html.escape(d["for"])}<br>'
            f'<b>向かない人:</b>{html.escape(d["not_for"])}</p>'
            f'<p><small>参考価格 {it["itemPrice"]:,}円 / レビュー {it["reviewAverage"]}'
            f'({it["reviewCount"]}件)※掲載時点</small></p>'
            f'<a class="c" href="{link}" rel="nofollow sponsored" target="_blank">'
            '楽天市場で価格・在庫を見る</a><p><a href="../../index.html">← 記事一覧へ</a></p>'
            '</body></html>')


def rebuild_index(posts, docs):
    items = "".join(f'<li><a href="posts/{p["slug"]}/index.html">{html.escape(p["title"])}</a> '
                    f'<small>{p["date"]}</small></li>' for p in reversed(posts))
    with open(f"{docs}/index.html", "w", encoding="utf-8") as f:
        f.write(f'{HEAD}<title>4コマでわかる!おすすめ商品</title></head>'
                '<body style="font-family:sans-serif;max-width:720px;margin:0 auto;padding:16px">'
                '<h1>4コマでわかる!おすすめ商品</h1>'
                '<p><small>※当サイトはアフィリエイト広告を含みます</small></p>'
                f'<ul>{items}</ul></body></html>')
