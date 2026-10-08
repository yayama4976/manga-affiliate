import html, re

BUBBLE_POS = ["top:8px;left:8px", "top:52%;right:8px"]
BUBBLE_POS_P3 = ["bottom:8px;left:8px", "bottom:70px;right:8px"]
CHAR = {"hero": ("タクミ", "#fff3b0"), "neko": ("ネコ店長", "#d6f0ff")}


def photo_url(it):
    imgs = it.get("mediumImageUrls") or []
    u = imgs[0].get("imageUrl", "") if imgs else ""
    return re.sub(r"\?_ex=\d+x\d+", "?_ex=500x500", u)


def panel_html(i, p, ok, it, link):
    pos = BUBBLE_POS_P3 if i == 2 else BUBBLE_POS
    if ok:
        bg = f'<img src="p{i+1}.webp" alt="" style="width:100%;display:block">'
    else:
        bg = '<div style="aspect-ratio:1;background:#eee"></div>'
    bubbles = ""
    for ln, ps in zip(p["lines"][:2], pos):
        name, color = CHAR.get(ln["who"], CHAR["hero"])
        bubbles += (f'<div style="position:absolute;{ps};max-width:58%;background:{color};'
                    f'color:#222;border:2.5px solid #222;border-radius:16px;padding:6px 10px;'
                    f'font-size:14px;font-weight:700;line-height:1.45"><small>{name}</small>'
                    f'<br>{html.escape(ln["text"])}</div>')
    photo = ""
    if i == 2 and photo_url(it):   # 3コマ目: 楽天の実物写真を合成
        photo = (f'<a href="{link}" rel="nofollow sponsored" target="_blank" '
                 f'style="position:absolute;left:50%;top:8%;transform:translateX(-50%);'
                 f'width:44%;background:#fff;border:3px solid #222;border-radius:8px;padding:4px">'
                 f'<img src="{photo_url(it)}" alt="商品写真" style="width:100%;display:block"></a>')
    cap = ""
    if p.get("caption"):
        cap = (f'<div style="position:absolute;left:0;right:0;bottom:0;background:#222;'
               f'color:#fff;text-align:center;font-size:13px;padding:6px">'
               f'{html.escape(p["caption"])}</div>')
    return (f'<div style="position:relative;border:3px solid #222;overflow:hidden;'
            f'background:#fff">{bg}{photo}{bubbles}{cap}</div>')
