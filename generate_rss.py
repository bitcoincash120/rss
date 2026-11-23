import html
import json
from pathlib import Path
from urllib.parse import urlparse
from feedgen.feed import FeedGenerator

SITE_URL = "https://bitcoincash120.github.io/rss"


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


def post_images(post: dict) -> list[str]:
    images = list(post.get("images") or [])
    if not images and post.get("image"):
        images.append(post["image"])
    return images


fg = FeedGenerator()
fg.load_extension("media", atom=False)
fg.id(f"{SITE_URL}/rss.xml")
fg.title("Моя RSS-лента")
fg.link(href=SITE_URL, rel="alternate")
fg.link(href=f"{SITE_URL}/rss.xml", rel="self")
fg.description("Свежие публикации и обновления")
fg.language("ru")

with open("posts.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

for post in reversed(posts):
    fe = fg.add_entry()
    fe.id(post["id"])
    fe.title(post["title"])
    fe.link(href=post["link"])
    fe.pubDate(post["date"])

    description = post["description"]
    images = post_images(post)
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
