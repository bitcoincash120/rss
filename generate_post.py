#!/usr/bin/env python3
"""Create a markdown post and optional Marp cards."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

from generate_cards import render_one
from posts_md import POSTS_DIR, clamp_style, parse_post


def next_post_id() -> str:
    numbers = []
    for path in POSTS_DIR.glob("post-*.md"):
        match = re.fullmatch(r"post-(\d+)", path.stem)
        if match:
            numbers.append(int(match.group(1)))
    return f"post-{max(numbers, default=0) + 1:02d}"


def clamp_slides(value: int | str | None) -> int:
    try:
        return max(2, min(3, int(value or 3)))
    except (TypeError, ValueError):
        return 3


def normalize_cards(cards: list[str] | None, description: str) -> list[str]:
    out = [""] * 3
    for index, text in enumerate(list(cards or [])[:3]):
        out[index] = str(text or "").strip()
    if not any(out) and description:
        out[1] = description
    return out


def write_markdown(
    post_id: str,
    title: str,
    description: str,
    slides: int,
    date: str | None = None,
    cards: list[str] | None = None,
    style: str | None = None,
) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    when = date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    path = POSTS_DIR / f"{post_id}.md"
    parts = [
        f"---\ndate: {when}\nslides: {slides}\nstyle: {clamp_style(style)}\n---\n\n# {title.strip()}\n"
    ]
    copy = normalize_cards(cards, description)
    if any(copy):
        for index, text in enumerate(copy, 1):
            if text and (index <= slides):
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
) -> dict:
    title = (title or "").strip()
    copy = normalize_cards(cards, (description or "").strip())
    description = (description or "").strip() or next((text for text in (copy[1], copy[0], copy[2]) if text), "")
    if not title:
        raise ValueError("Нужен заголовок")
    if not description:
        raise ValueError("Нужен текст")
    slides_n = clamp_slides(slides)
    post_id = next_post_id()
    path = write_markdown(post_id, title, description, slides_n, date, copy, style)
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
    parser.add_argument("--slides", type=int, default=3)
    parser.add_argument("--card1", default="")
    parser.add_argument("--card2", default="")
    parser.add_argument("--card3", default="")
    parser.add_argument("--style", default="night")
    args = parser.parse_args()
    post = create_post(
        args.title,
        args.description,
        args.slides,
        cards=[args.card1, args.card2, args.card3],
        style=args.style,
    )
    print(f"wrote {post['path'].name}")


if __name__ == "__main__":
    main()
