#!/usr/bin/env python3
"""Build Marp decks from markdown posts and render JPEG cards."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from posts_md import (
    ROOT,
    card_image_name,
    clamp_style,
    count_marp_slides,
    format_datetime_ru,
    load_posts,
    normalize_marp_deck,
)

CARDS_DIR = ROOT / "cards"
OUT_DIR = CARDS_DIR / "out"
IMAGES_DIR = ROOT / "images"
PREVIEWS_DIR = ROOT / "previews"
THEME_PATH = CARDS_DIR / "theme.css"
FINDOC_THEME = CARDS_DIR / "fin-doc.css"
def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def card_copy(post: dict) -> list[str]:
    cards = [str(text or "").strip() for text in list(post.get("cards") or [])]
    filled = [text for text in cards if text]
    if filled:
        return filled
    fallback = str(post.get("description") or "").strip()
    return [fallback] if fallback else [""]


def findoc_kind(index: int, total: int) -> str:
    if index == 1:
        return "hero"
    if index == total and total > 1:
        return "cta"
    return ("list", "facts", "body")[(index - 2) % 3]


def retarget_marp(marp: str, style: str) -> str:
    skin = clamp_style(style)
    text = normalize_marp_deck(marp)
    if not text:
        return ""
    if re.search(r"(?im)^theme:\s*\S+", text):
        text = re.sub(r"(?im)^theme:\s*\S+", "theme: fin-doc", text, count=1)
    else:
        text = re.sub(r"(?im)^(marp:\s*true)\s*$", r"\1\ntheme: fin-doc", text, count=1)
    if not re.search(r"(?im)^size:\s*", text):
        text = re.sub(r"(?im)^(theme:\s*\S+)", r"\1\nsize: carousel", text, count=1)
    if re.search(r"(?im)^class:\s*", text):
        text = re.sub(r"(?im)^class:\s*.*$", f"class: {skin}", text, count=1)
    else:
        text = re.sub(r"(?im)^(theme:\s*\S+)", rf"\1\nclass: {skin}", text, count=1)
    return text


def findoc_slide(index: int, total: int, title: str, text: str, when: str) -> str:
    kind = findoc_kind(index, total)
    num = f"{index:02d}/{total:02d}"
    foot_right = "Сохраните" if index == total else "Листай →"
    dark = " dark" if kind == "hero" else ""
    body = text or title
    if kind == "hero":
        inner = f'<div class="kicker">Обзор</div>\n<h3 class="hero">{title}</h3>'
        if text:
            inner += f"\n<p>{text}</p>"
    elif kind == "list":
        inner = (
            f'<div class="kicker">Разбор</div>\n'
            f'<div class="list-item"><span class="idx">{index:02d}</span><div>{body}</div></div>'
        )
    elif kind == "facts":
        inner = (
            f'<div class="kicker">Факты</div>\n'
            f'<div class="fact-row"><span class="idx">{index:02d}</span><div>{body}</div></div>'
        )
    elif kind == "cta":
        inner = f'<div class="kicker">Следующий шаг</div>\n<div class="cta-word">Дальше</div>'
        if body:
            inner += f"\n<p>{body}</p>"
    else:
        inner = f'<div class="kicker">Карточка</div>\n<p>{body}</p>'
    return f"""<article class="slide{dark}">
<div class="head"><span>{when}</span><span>{num}</span></div>
<div class="content">
{inner}
</div>
<div class="foot"><span>Карточка {index} из {total}</span><span>{foot_right}</span></div>
</article>"""


def deck_markdown(post: dict) -> str:
    title = esc(post["title"])
    copy = [esc(text) for text in card_copy(post)]
    when = esc(format_datetime_ru(post) or "Черновик")
    total = max(1, int(post.get("slides") or len(copy) or 1))
    copy = copy[:total] or [""]
    total = len(copy)
    style = clamp_style(post.get("style"))
    marp = normalize_marp_deck(post.get("marp") or "")
    if marp:
        return retarget_marp(marp, style)
    slides = [
        findoc_slide(index, total, title, text, when) for index, text in enumerate(copy, 1)
    ]
    return (
        f"---\nmarp: true\ntheme: fin-doc\nclass: {style}\nsize: carousel\npaginate: false\n---\n\n"
        + "\n\n---\n\n".join(slides)
        + "\n"
    )


def chrome_path() -> str | None:
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        return env_path
    for candidate in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def marp_bin() -> Path:
    return ROOT / "node_modules" / ".bin" / "marp"


def render_deck(md_path: Path, *, image_scale: str = "1") -> None:
    env = os.environ.copy()
    chrome = chrome_path()
    if chrome:
        env["CHROME_PATH"] = chrome
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
        env["CHROME_NO_SANDBOX"] = "1"
    marp = marp_bin()
    if not marp.exists():
        raise FileNotFoundError("Marp CLI is not installed. Run npm install.")
    cmd = [
        str(marp),
        str(md_path),
        "--theme-set",
        str(THEME_PATH),
        "--theme-set",
        str(FINDOC_THEME),
        "--images",
        "jpeg",
        "--jpeg-quality",
        "88",
        "--image-scale",
        image_scale,
        "--html",
        "--allow-local-files",
        "-o",
        str(OUT_DIR / f"{md_path.stem}.jpg"),
    ]
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def slide_count(post: dict) -> int:
    marp_n = count_marp_slides(post.get("marp") or "")
    return max(1, int(post.get("slides") or marp_n or len(card_copy(post)) or 1), marp_n)


def expected_images(post: dict) -> list[Path]:
    count = slide_count(post)
    return [IMAGES_DIR / card_image_name(post["id"], index) for index in range(1, count + 1)]


def already_rendered(post: dict) -> list[Path] | None:
    paths = expected_images(post)
    if paths and all(path.is_file() for path in paths):
        return paths
    return None


def publish_images(post_id: str, count: int) -> list[Path]:
    produced = sorted(OUT_DIR.glob(f"{post_id}.*.jpg")) + sorted(
        OUT_DIR.glob(f"{post_id}.*.jpeg")
    )
    if len(produced) < count:
        raise RuntimeError(f"{post_id}: expected {count} cards, got {len(produced)}")
    IMAGES_DIR.mkdir(exist_ok=True)
    targets = []
    for index, src in enumerate(produced[:count], 1):
        dest = IMAGES_DIR / card_image_name(post_id, index)
        shutil.copyfile(src, dest)
        targets.append(dest)
    keep = {path.name for path in targets}
    first = IMAGES_DIR / f"{post_id}.jpg"
    if first.name not in keep and first.exists():
        first.unlink()
    prefix = f"{post_id}-"
    for path in IMAGES_DIR.glob(f"{post_id}-*.jpg"):
        suffix = path.stem[len(prefix) :]
        if suffix.isdigit() and path.name not in keep:
            path.unlink()
    return targets


def render_preview(idea: dict, *, force: bool = False) -> list[str]:
    row = int(idea.get("row") or 0)
    if row <= 0:
        raise ValueError("Нет номера строки таблицы")
    dest = PREVIEWS_DIR / f"row-{row}"
    dest.mkdir(parents=True, exist_ok=True)
    post = {
        "id": f"draft-row-{row}",
        "title": idea.get("title") or "",
        "description": idea.get("description") or "",
        "cards": idea.get("cards") or [],
        "marp": idea.get("marp") or "",
        "slides": idea.get("slides") or 1,
        "style": "findoc",
    }
    count = slide_count(post)
    names = [f"{index}.jpg" for index in range(1, count + 1)]
    paths = [dest / name for name in names]
    if not force and paths and all(path.is_file() for path in paths):
        return [f"previews/row-{row}/{name}" for name in names]
    CARDS_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / f"{post['id']}.md"
    md_path.write_text(deck_markdown(post), encoding="utf-8")
    render_deck(md_path, image_scale="1")
    produced = sorted(OUT_DIR.glob(f"{post['id']}.*.jpg")) + sorted(
        OUT_DIR.glob(f"{post['id']}.*.jpeg")
    )
    if len(produced) < count:
        raise RuntimeError(f"Строка {row}: ожидалось {count} карточек, собрано {len(produced)}")
    for index, src in enumerate(produced[:count], 1):
        shutil.copyfile(src, dest / f"{index}.jpg")
    return [f"previews/row-{row}/{name}" for name in names]


def render_one(post: dict, *, force: bool = False) -> list[Path]:
    if not force:
        existing = already_rendered(post)
        if existing:
            return existing
    CARDS_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = OUT_DIR / f"{post['id']}.md"
    md_path.write_text(deck_markdown(post), encoding="utf-8")
    scale = "3"
    render_deck(md_path, image_scale=scale)
    return publish_images(post["id"], slide_count(post))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Пересобрать карточки даже если JPEG уже есть",
    )
    args = parser.parse_args()
    posts = load_posts()
    CARDS_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for post in posts:
        if not args.force and already_rendered(post):
            print(f"skip {post['path'].name}")
            continue
        print(f"rendering {post['path'].name}")
        paths = render_one(post, force=True)
        print(" -> " + ", ".join(p.name for p in paths))

    return 0


if __name__ == "__main__":
    sys.exit(main())
