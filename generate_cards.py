#!/usr/bin/env python3
"""Build Marp decks from posts.json and render JPEG cards."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS_DIR = ROOT / "cards"
OUT_DIR = CARDS_DIR / "out"
IMAGES_DIR = ROOT / "images"
POSTS_PATH = ROOT / "posts.json"
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
    return f"""---
marp: true
theme: cards
paginate: false
---

<!-- _class: hero -->

## Лента

# {title}

### Карточка 1 из 3

---

<!-- _class: quote -->

## Анонс

{body}

### Карточка 2 из 3

---

<!-- _class: compact -->

## Коротко

# {title}

{body}

### Карточка 3 из 3
"""


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


def publish_images(post_id: str) -> list[Path]:
    produced = sorted(OUT_DIR.glob(f"{post_id}.*.jpg")) + sorted(
        OUT_DIR.glob(f"{post_id}.*.jpeg")
    )
    if len(produced) < 3:
        raise RuntimeError(f"{post_id}: expected 3 cards, got {len(produced)}")
    IMAGES_DIR.mkdir(exist_ok=True)
    targets = [
        IMAGES_DIR / f"{post_id}.jpg",
        IMAGES_DIR / f"{post_id}-2.jpg",
        IMAGES_DIR / f"{post_id}-3.jpg",
    ]
    for src, dest in zip(produced[:3], targets):
        shutil.copyfile(src, dest)
    return targets


def main() -> int:
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    CARDS_DIR.mkdir(exist_ok=True)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()

    for post in posts:
        post_id = post["id"]
        md_path = CARDS_DIR / f"{post_id}.md"
        md_path.write_text(deck_markdown(post), encoding="utf-8")
        print(f"rendering {md_path.name}")
        render_deck(md_path)
        paths = publish_images(post_id)
        print(" -> " + ", ".join(p.name for p in paths))

    return 0


if __name__ == "__main__":
    sys.exit(main())
