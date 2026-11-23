import html
import json
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
    image = post.get("image")
    if image:
        safe_text = html.escape(description)
        safe_image = html.escape(image, quote=True)
        body = f'<p><img src="{safe_image}" alt=""/></p><p>{safe_text}</p>'
        mime = image_mime(image)
        fe.description(body)
        fe.content(body, type="CDATA")
        fe.enclosure(image, "0", mime)
        fe.media.thumbnail({"url": image})
        fe.media.content({"url": image, "medium": "image", "type": mime})
    else:
        fe.description(description)

fg.rss_file("rss.xml", pretty=True)
