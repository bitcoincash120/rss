#!/usr/bin/env python3
"""Render a visual feed page from markdown posts."""

from __future__ import annotations

import html

from posts_md import ROOT, format_added_short, load_posts
from site_settings import rss_enabled


def cell_or_dash(value: str | None) -> str:
    text = str(value or "").strip()
    return html.escape(text) if text else "—"

OUT = ROOT / "feed.html"


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
    when = format_added_short(post) or "—"
    thumb = ""
    if post["image_files"]:
        src = html.escape(post["image_files"][0], quote=True)
        thumb = f'<img src="images/{src}" alt="">'
    post_id = html.escape(post["id"], quote=True)
    images = html.escape(",".join(post.get("image_files") or []), quote=True)
    title = html.escape(post["title"], quote=True)
    return f"""
    <tr class="row" data-open="{post_id}" data-images="{images}" tabindex="0" role="button">
      <td class="col-check" data-stop>
        <label class="check">
          <input type="checkbox" name="post" value="{post_id}" aria-label="Выбрать {title}">
        </label>
      </td>
      <td class="col-num">{index}</td>
      <td class="col-thumb">{thumb}</td>
      <td class="col-date"><time datetime="{html.escape(post["date"], quote=True)}">{html.escape(when)}</time></td>
      <td class="col-schedule">{cell_or_dash(post.get("hooppy_schedule"))}</td>
      <td class="col-title">{title}</td>
      <td class="col-count">{len(post["image_files"])}</td>
    </tr>
    """


def card_rows_html(post: dict) -> str:
    cards = list(post.get("cards") or [])
    rows = []
    for index, text in enumerate(cards, 1):
        if not text:
            continue
        rows.append(
            f"""
          <tr>
            <th>Карточка {index}</th>
            <td>{html.escape(text)}</td>
          </tr>"""
        )
    if not rows and post.get("description"):
        rows.append(
            f"""
          <tr>
            <th>Текст</th>
            <td>{html.escape(post["description"])}</td>
          </tr>"""
        )
    return "".join(rows)


def download_button_html(post: dict) -> str:
    files = post.get("image_files") or []
    if not files:
        return ""
    names = html.escape(",".join(files), quote=True)
    zip_name = html.escape(post["id"], quote=True)
    return (
        f'<p class="download-row"><button type="button" class="ghost" data-zip="{names}" '
        f'data-zip-name="{zip_name}">Скачать карточки</button></p>'
    )


def preview_html(post: dict) -> str:
    when = format_added_short(post) or "—"
    return f"""
    <dialog class="preview" id="{html.escape(post["id"], quote=True)}">
      <div class="sheet">
        <button type="button" class="close" data-close aria-label="Закрыть">×</button>
        <table>
          <tr>
            <th>Дата добавления</th>
            <td><time datetime="{html.escape(post["date"], quote=True)}">{html.escape(when)}</time></td>
          </tr>
          <tr>
            <th>Расписание</th>
            <td>{cell_or_dash(post.get("hooppy_schedule"))}</td>
          </tr>
          <tr>
            <th>Заголовок</th>
            <td>{html.escape(post["title"])}</td>
          </tr>
          {card_rows_html(post)}
          <tr>
            <th>Карточки</th>
            <td>{carousel_html(post)}{download_button_html(post)}</td>
          </tr>
        </table>
      </div>
    </dialog>
    """


def rss_action_html() -> str:
    hidden = "" if rss_enabled() else " hidden"
    return f'<a class="rss" data-rss href="rss.xml"{hidden}>RSS</a>'


def rss_head_html() -> str:
    if not rss_enabled():
        return ""
    return '<link rel="alternate" type="application/rss+xml" href="rss.xml">'


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
            <th class="col-check"><input type="checkbox" id="select-all" aria-label="Выбрать все"></th>
            <th>№</th>
            <th>Карточка</th>
            <th>Дата добавления</th>
            <th>Расписание</th>
            <th>Заголовок</th>
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
  {rss_head_html()}
  <link rel="stylesheet" href="site.css?v=import">
</head>
<body>
  <main class="wrap">
    <header class="hero">
      <p class="kicker">Лента</p>
      <div class="hero-row">
        <h1>Свежие публикации</h1>
        <div class="hero-actions">
          <a class="ghost" href="./">Импорт</a>
          <a class="ghost" href="new.html">Новый пост</a>
          <a class="ghost" href="admin.html">Админка</a>
          <button type="button" class="ghost" id="download-all">Скачать все картинки</button>
          <button type="button" class="ghost" id="delete-selected" disabled>Удалить</button>
          {rss_action_html()}
        </div>
      </div>
      <p class="lede">Все посты в таблице. Нажмите строку, чтобы открыть полный пост. Чтобы убрать публикацию с сайта, отметьте галочку и нажмите «Удалить» — строка в Google Таблице не изменится.</p>
      <p class="status" id="delete-status" role="status"></p>
    </header>
    {table}
  </main>
  {previews}
  <script src="feed.js?v=delete-posts"></script>
  <script src="settings.js?v=admin"></script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(posts)} posts)")


if __name__ == "__main__":
    main()
