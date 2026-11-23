#!/usr/bin/env python3
"""Render a visual feed page from markdown posts."""

from __future__ import annotations

import html
from pathlib import Path

from posts_md import ROOT, format_date_ru, format_datetime_ru, format_time_ru, load_posts

OUT = ROOT / "index.html"


def excerpt(text: str, limit: int = 88) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


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
    nav = ""
    if len(files) > 1:
        dots = "".join(
            f'<button type="button" class="dot{" is-on" if i == 0 else ""}" data-go="{i}" aria-label="Карточка {i + 1}"></button>'
            for i in range(len(files))
        )
        nav = f"""
        <button type="button" class="nav prev" data-dir="-1" aria-label="Предыдущая карточка">‹</button>
        <button type="button" class="nav next" data-dir="1" aria-label="Следующая карточка">›</button>
        <div class="dots">{dots}</div>
        <p class="count"><span data-count>1</span> / {len(files)}</p>
        """
    return f'<div class="stage" data-carousel>{"".join(slides)}{nav}</div>'


def row_html(post: dict, index: int) -> str:
    day = format_date_ru(post) or "—"
    clock = format_time_ru(post)
    thumb = ""
    if post["image_files"]:
        src = html.escape(post["image_files"][0], quote=True)
        thumb = f'<img src="images/{src}" alt="">'
    post_id = html.escape(post["id"], quote=True)
    time_html = f'<span class="clock">{html.escape(clock)}</span>' if clock else ""
    return f"""
    <tr class="row" data-open="{post_id}" tabindex="0" role="button">
      <td class="col-num">{index}</td>
      <td class="col-thumb">{thumb}</td>
      <td class="col-date"><time datetime="{html.escape(post["date"], quote=True)}"><span class="day">{html.escape(day)}</span>{time_html}</time></td>
      <td class="col-title">{html.escape(post["title"])}</td>
      <td class="col-excerpt">{html.escape(excerpt(post["description"]))}</td>
      <td class="col-count">{len(post["image_files"])}</td>
    </tr>
    """


def preview_html(post: dict) -> str:
    when = format_datetime_ru(post) or "—"
    return f"""
    <dialog class="preview" id="{html.escape(post["id"], quote=True)}">
      <div class="sheet">
        <button type="button" class="close" data-close aria-label="Закрыть">×</button>
        <table>
          <tr>
            <th>Дата и время</th>
            <td><time datetime="{html.escape(post["date"], quote=True)}">{html.escape(when)}</time></td>
          </tr>
          <tr>
            <th>Заголовок</th>
            <td>{html.escape(post["title"])}</td>
          </tr>
          <tr>
            <th>Текст</th>
            <td>{html.escape(post["description"])}</td>
          </tr>
          <tr>
            <th>Карточки</th>
            <td>{carousel_html(post)}</td>
          </tr>
        </table>
      </div>
    </dialog>
    """


def main() -> None:
    posts = load_posts()
    rows = "\n".join(row_html(post, i) for i, post in enumerate(posts, 1))
    previews = "\n".join(preview_html(post) for post in posts)
    table = (
        f"""
    <div class="table-wrap">
      <table class="feed">
        <thead>
          <tr>
            <th>№</th>
            <th>Карточка</th>
            <th>Дата и время</th>
            <th>Заголовок</th>
            <th>Анонс</th>
            <th>Фото</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
    """
        if posts
        else '<p class="empty">Добавьте файл в папку posts, чтобы он появился здесь.</p>'
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
        <div class="hero-actions">
          <a class="ghost" href="new.html">Новый пост</a>
          <a class="rss" href="rss.xml">RSS</a>
        </div>
      </div>
      <p class="lede">Все посты в таблице. Нажмите строку, чтобы открыть полный пост.</p>
    </header>
    {table}
  </main>
  {previews}
  <script>
    const openPreview = (id) => {{
      const dialog = document.getElementById(id);
      if (dialog && typeof dialog.showModal === "function") {{
        dialog.showModal();
        history.replaceState(null, "", "#" + id);
      }}
    }};
    const closePreview = (dialog) => {{
      dialog.close();
      if (location.hash.slice(1) === dialog.id) history.replaceState(null, "", location.pathname);
    }};
    document.querySelectorAll("[data-open]").forEach((row) => {{
      const open = () => openPreview(row.dataset.open);
      row.addEventListener("click", open);
      row.addEventListener("keydown", (event) => {{
        if (event.key === "Enter" || event.key === " ") {{
          event.preventDefault();
          open();
        }}
      }});
    }});
    document.querySelectorAll("dialog.preview").forEach((dialog) => {{
      dialog.querySelector("[data-close]")?.addEventListener("click", () => closePreview(dialog));
      dialog.addEventListener("click", (event) => {{
        if (event.target === dialog) closePreview(dialog);
      }});
    }});
    if (location.hash) openPreview(location.hash.slice(1));
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
        btn.addEventListener("click", (event) => {{
          event.stopPropagation();
          show(i + Number(btn.dataset.dir));
        }});
      }});
      dots.forEach((dot) => {{
        dot.addEventListener("click", (event) => {{
          event.stopPropagation();
          show(Number(dot.dataset.go));
        }});
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
