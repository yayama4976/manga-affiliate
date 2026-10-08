import html, re

CHAR = {"hero": ("タクミ", "#fff3b0"), "neko": ("ネコ店長", "#d6f0ff")}


def nm(s):
    """台本に残った hero / neko を名前に直す"""
    return (s.replace("hero", "タクミ").replace("Hero", "タクミ")
             .replace("neko", "ネコ店長").replace("Neko", "ネコ店長"))


def photo_url(it):
    """楽天の商品写真(サムネ128pxを500pxに差し替え)。APIの形式違い(文字列/辞書)に対応"""
    imgs = it.get("mediumImageUrls") or []
    u = ""
    if imgs:
        first = imgs[0]
        u = first.get("imageUrl", "") if isinstance(first, dict) else str(first)
    return re.sub(r"\?_ex=\d+x\d+", "?_ex=500x500", u)


def who_key(who):
    """話者名のゆれ(hero / タクミ / ネコ店長 / cat など)を hero か neko にそろえる"""
    w = str(who).lower()
    return "neko" if any(k in w for k in ("neko", "ネコ", "猫", "cat")) else "hero"


def bubble(pos, who, text, width):
    name, color = CHAR[who_key(who)]
    return (f'<div style="position:absolute;{pos};max-width:{width};background:{color};'
            f'color:#222;border:2.5px solid #222;border-radius:16px;padding:5px 9px;'
            f'font-size:13px;font-weight:700;line-height:1.45"><small>{name}</small>'
            f'<br>{html.escape(nm(text))}</div>')


def panel_html(i, p, ok, it, link):
    photo_on = i == 2 and bool(photo_url(it))
    if photo_on:
        pos, width = ["bottom:8px;left:8px", "bottom:8px;right:8px"], "46%"
    else:
        pos, width = ["top:8px;left:8px", "bottom:8px;right:8px"], "62%"
    if ok:
        bg = f'<img src="p{i+1}.webp" alt="" style="width:100%;display:block">'
    else:
        bg = '<div style="aspect-ratio:1;background:#eee"></div>'
    bubbles = "".join(bubble(ps, ln["who"], ln["text"], width)
                      for ln, ps in zip(p["lines"][:2], pos))
    photo = ""
    if photo_on:   # 3コマ目: 楽天の実物写真を合成
        photo = (f'<a href="{link}" rel="nofollow sponsored" target="_blank" '
                 f'style="position:absolute;left:50%;top:6%;transform:translateX(-50%);'
                 f'width:44%;background:#fff;border:3px solid #222;border-radius:8px;padding:4px">'
                 f'<img src="{photo_url(it)}" alt="商品写真" style="width:100%;display:block"></a>')
    cap = ""
    if p.get("caption"):   # キャプションは絵の下に別帯で表示(吹き出しと重ならない)
        cap = (f'<div style="background:#222;color:#fff;text-align:center;font-size:13px;'
               f'padding:6px">{html.escape(nm(p["caption"]))}</div>')
    return (f'<div style="border:3px solid #222;background:#fff">'
            f'<div style="position:relative;overflow:hidden">{bg}{photo}{bubbles}</div>{cap}</div>')
