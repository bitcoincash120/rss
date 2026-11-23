import html
from pathlib import Path
from urllib.parse import urlparse

from feedgen.feed import FeedGenerator

from posts_md import SITE_URL, load_posts


def image_mime(url: str) -> str:
    lower = url.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def enclosure_length(url: str) -> str:
    name = Path(urlparse(url).path).name
    local = Path("images") / name
    if local.is_file():
        return str(local.stat().st_size)
    return "0"


fg = FeedGenerator()
fg.load_extension("media", atom=False)
fg.id(f"{SITE_URL}/rss.xml")
fg.title("Моя RSS-лента")
fg.link(href=SITE_URL, rel="alternate")
fg.link(href=f"{SITE_URL}/rss.xml", rel="self")
fg.description("Свежие публикации и обновления")
fg.language("ru")

for post in reversed(load_posts()):
    fe = fg.add_entry()
    fe.id(post["id"])
    fe.title(post["title"])
    fe.link(href=post["link"])
    if post["date"]:
        fe.pubDate(post["date"])

    description = post["description"]
    images = post["images"]
    if images:
        safe_text = html.escape(description)
        img_tags = "".join(
            f'<p><img src="{html.escape(url, quote=True)}" alt=""/></p>'
            for url in images
        )
        body = f"{img_tags}<p>{safe_text}</p>"
        fe.description(body)
        fe.content(body, type="CDATA")
        first = images[0]
        fe.enclosure(first, enclosure_length(first), image_mime(first))
        fe.media.thumbnail({"url": first})
        for url in images:
            fe.media.content(
                {"url": url, "medium": "image", "type": image_mime(url)}
            )
    else:
        fe.description(description)

fg.rss_file("rss.xml", pretty=True)
