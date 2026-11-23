import json
from feedgen.feed import FeedGenerator

SITE_URL = "https://github.io"

fg = FeedGenerator()
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
    fe.description(post["description"])
    fe.pubDate(post["date"])

fg.rss_file("rss.xml", pretty=True)
