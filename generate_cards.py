#!/usr/bin/env python3
"""Build Marp decks from markdown posts and render JPEG cards."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from posts_md import ROOT, load_posts

CARDS_DIR = ROOT / "cards"
OUT_DIR = CARDS_DIR / "out"
IMAGES_DIR = ROOT / "images"
THEME_PATH = CARDS_DIR / "theme.css"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def deck_markdown(post: dict) -> str:
    title = esc(post["title"])
    body = esc(post["description"])
    total = post.get("slides") or 3
    slides = [
        f"""<!-- _class: hero -->

## Лента

# {title}

### Карточка 1 из {total}""",
        f"""<!-- _class: quote -->

## Анонс

{body}

### Карточка 2 из {total}""",
    ]
    if total >= 3:
        slides.append(
            f"""<!-- _class: compact -->

## Коротко

# {title}

{body}

### Карточка 3 из {total}"""
        )
    return "---\nmarp: true\ntheme: cards\npaginate: false\n---\n\n" + "\n\n---\n\n".join(slides) + "\n"


def render_deck(md_path: Path) -> None:
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    env = os.environ.copy()
    if chrome.exists():
        env["CHROME_PATH"] = str(chrome)
    marp = ROOT / "node_modules" / ".bin" / "marp"
    cmd = [
        str(marp),
        str(md_path),
        "--theme-set",
        str(THEME_PATH),
        "--images",
        "jpeg",
        "--jpeg-quality",
        "88",
        "--image-scale",
        "1",
        "--allow-local-files",
        "-o",
        str(OUT_DIR / f"{md_path.stem}.jpg"),
    ]
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def publish_images(post_id: str, count: int) -> list[Path]:
    produced = sorted(OUT_DIR.glob(f"{post_id}.*.jpg")) + sorted(
        OUT_DIR.glob(f"{post_id}.*.jpeg")
    )
    if len(produced) < count:
        raise RuntimeError(f"{post_id}: expected {count} cards, got {len(produced)}")
    IMAGES_DIR.mkdir(exist_ok=True)
    names = [f"{post_id}.jpg", f"{post_id}-2.jpg", f"{post_id}-3.jpg"]
    targets = []
    for src, name in zip(produced[:count], names[:count]):
        dest = IMAGES_DIR / name
        shutil.copyfile(src, dest)
        targets.append(dest)
    leftover = IMAGES_DIR / f"{post_id}-3.jpg"
    if count < 3 and leftover.exists():
        leftover.unlink()
    return targets


def main() -> int:
    posts = load_posts()
    CARDS_DIR.mkdir(exist_ok=True)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()

    for post in posts:
        post_id = post["id"]
        md_path = OUT_DIR / f"{post_id}.md"
        md_path.write_text(deck_markdown(post), encoding="utf-8")
        print(f"rendering {post['path'].name}")
        render_deck(md_path)
        paths = publish_images(post_id, post.get("slides") or 3)
        print(" -> " + ", ".join(p.name for p in paths))

    return 0


if __name__ == "__main__":
    sys.exit(main())
