#!/usr/bin/env python3
"""Create a markdown post and optional Marp cards."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from generate_cards import render_one
from posts_md import (
    DEFAULT_STYLE,
    POSTS_DIR,
    cards_from_marp,
    clamp_style,
    count_marp_slides,
    normalize_marp_deck,
    parse_post,
)


def next_post_id() -> str:
    numbers = []
    for path in POSTS_DIR.glob("post-*.md"):
        match = re.fullmatch(r"post-(\d+)", path.stem)
        if match:
            numbers.append(int(match.group(1)))
    return f"post-{max(numbers, default=0) + 1:02d}"


def clamp_slides(value: int | str | None, cards: list[str] | None = None) -> int:
    filled = [str(text or "").strip() for text in list(cards or []) if str(text or "").strip()]
    try:
        listed = int(value or 0)
    except (TypeError, ValueError):
        listed = 0
    return max(1, len(filled) or listed or 1)


def normalize_cards(cards: list[str] | None, description: str) -> list[str]:
    out = [str(text or "").strip() for text in list(cards or [])]
    while out and not out[-1]:
        out.pop()
    if not any(out) and description.strip():
        out = [description.strip()]
    return out


def write_markdown(
    post_id: str,
    title: str,
    description: str,
    slides: int,
    date: str | None = None,
    cards: list[str] | None = None,
    style: str | None = None,
    marp: str | None = None,
) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    when = date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    path = POSTS_DIR / f"{post_id}.md"
    deck = normalize_marp_deck(marp or "")
    style_name = clamp_style(style or ("findoc" if deck else None))
    parts = [
        f"---\ndate: {when}\nslides: {slides}\nstyle: {style_name}\n---\n\n# {title.strip()}\n"
    ]
    if deck:
        parts.append("\n" + deck)
    else:
        copy = normalize_cards(cards, description)
        if any(copy):
            for index, text in enumerate((item for item in copy if item), 1):
                if index <= slides:
                    parts.append(f"\n## {index}\n\n{text}\n")
        elif description.strip():
            parts.append(f"\n{description.strip()}\n")
    path.write_text("".join(parts), encoding="utf-8")
    return path


def create_post(
    title: str,
    description: str,
    slides: int | str | None = 3,
    date: str | None = None,
    render: bool = True,
    cards: list[str] | None = None,
    style: str | None = None,
    marp: str | None = None,
) -> dict:
    title = (title or "").strip()
    deck = normalize_marp_deck(marp or "")
    copy = cards_from_marp(deck) if deck else normalize_cards(cards, (description or "").strip())
    description = (
        (description or "").strip()
        or next((text for text in copy if text), "")
        or (title if deck else "")
    )
    if not title:
        raise ValueError("Нужен заголовок")
    if not description and not deck:
        raise ValueError("Нужна разметка Marp или текст карточек")
    slides_n = max(clamp_slides(slides, copy), count_marp_slides(deck), 1)
    post_id = next_post_id()
    path = write_markdown(post_id, title, description, slides_n, date, copy, style, deck)
    post = parse_post(path)
    if render:
        try:
            render_one(post)
            post = parse_post(path)
        except FileNotFoundError:
            post["cards_error"] = "Marp CLI не установлен"
        except Exception as exc:  # noqa: BLE001
            post["cards_error"] = str(exc)
    return post


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--slides", type=int, default=0)
    parser.add_argument("--card", action="append", default=[], dest="cards")
    parser.add_argument("--style", default=DEFAULT_STYLE)
    parser.add_argument("--marp", default="", help="Полная разметка Marp")
    parser.add_argument("--marp-file", default="", help="Файл с разметкой Marp")
    args = parser.parse_args()
    marp = args.marp
    if args.marp_file:
        marp = Path(args.marp_file).read_text(encoding="utf-8")
    post = create_post(
        args.title,
        args.description,
        args.slides or None,
        cards=args.cards,
        style=args.style,
        marp=marp,
    )
    print(f"wrote {post['path'].name}")


if __name__ == "__main__":
    main()
