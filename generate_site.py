#!/usr/bin/env python3
"""Render a visual feed page from markdown posts."""

from __future__ import annotations

import html
from pathlib import Path

from posts_md import ROOT, format_date_ru, load_posts

OUT = ROOT / "index.html"


def carousel_html(post: dict) -> str:
    files = post["image_files"]
    if not files:
        return ""
    title = html.escape(post["title"], quote=True)
    slides = []
    for i, name in enumerate(files):
        on = ' class="is-on"' if i == 0 else ""
        slides.append(
            f'<img{on} src="images/{html.escape(name, quote=True)}" alt="{title}">'
        )
    slides = "".join(slides)
    dots = "".join(
        f'<button type="button" class="dot{" is-on" if i == 0 else ""}" data-go="{i}" aria-label="Карточка {i + 1}"></button>'
        for i in range(len(files))
    )
    nav = ""
    if len(files) > 1:
        nav = f"""
        <button type="button" class="nav prev" data-dir="-1" aria-label="Предыдущая карточка">‹</button>
        <button type="button" class="nav next" data-dir="1" aria-label="Следующая карточка">›</button>
        <div class="dots">{dots}</div>
        <p class="count"><span data-count>1</span> / {len(files)}</p>
        """
    return f'<div class="stage" data-carousel>{slides}{nav}</div>'


def post_html(post: dict) -> str:
    when = format_date_ru(post)
    time_tag = (
        f'<time datetime="{html.escape(post["date"], quote=True)}">{html.escape(when)}</time>'
        if when
        else ""
    )
    return f"""
    <article class="card" id="{html.escape(post["id"], quote=True)}">
      {carousel_html(post)}
      <div class="body">
        {time_tag}
        <h2>{html.escape(post["title"])}</h2>
        <p>{html.escape(post["description"])}</p>
      </div>
    </article>
    """


def main() -> None:
    posts = load_posts()
    items = "\n".join(post_html(post) for post in posts) or (
        '<p class="empty">Добавьте файл в папку posts, чтобы он появился здесь.</p>'
    )
    page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Моя RSS-лента</title>
  <link rel="alternate" type="application/rss+xml" href="rss.xml">
  <link rel="stylesheet" href="site.css">
</head>
<body>
  <main class="wrap">
    <header class="hero">
      <p class="kicker">Лента</p>
      <div class="hero-row">
        <h1>Свежие публикации</h1>
        <a class="rss" href="rss.xml">RSS</a>
      </div>
      <p class="lede">Посты написаны в markdown. Здесь они выглядят как карточки, в RSS уходит та же лента.</p>
    </header>
    <section class="feed">
      {items}
    </section>
  </main>
  <script>
    document.querySelectorAll("[data-carousel]").forEach((stage) => {{
      const slides = [...stage.querySelectorAll("img")];
      const dots = [...stage.querySelectorAll("[data-go]")];
      const count = stage.querySelector("[data-count]");
      if (slides.length < 2) return;
      let i = 0;
      const show = (next) => {{
        i = (next + slides.length) % slides.length;
        slides.forEach((img, idx) => img.classList.toggle("is-on", idx === i));
        dots.forEach((dot, idx) => dot.classList.toggle("is-on", idx === i));
        if (count) count.textContent = String(i + 1);
      }};
      show(0);
      stage.querySelectorAll("[data-dir]").forEach((btn) => {{
        btn.addEventListener("click", () => show(i + Number(btn.dataset.dir)));
      }});
      dots.forEach((dot) => {{
        dot.addEventListener("click", () => show(Number(dot.dataset.go)));
      }});
    }});
  </script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(posts)} posts)")


if __name__ == "__main__":
    main()
