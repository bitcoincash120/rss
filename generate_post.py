#!/usr/bin/env python3
"""Create a markdown post and optional Marp cards."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from generate_cards import render_one
from hooppy import format_planned_date
from posts_md import (
    DEFAULT_STYLE,
    IMAGES_DIR,
    POSTS_DIR,
    ROOT,
    cards_from_marp,
    clamp_style,
    count_marp_slides,
    normalize_marp_deck,
    parse_frontmatter,
    parse_post,
)

META_ORDER = (
    "date",
    "slides",
    "style",
    "planned_date",
    "hooppy_schedule",
    "hooppy_schedule_id",
)


def yaml_scalar(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if any(ch in text for ch in ":#{}[]&*?|>'\"%@`,"):
        return json.dumps(text, ensure_ascii=False)
    return text


def dump_frontmatter(meta: dict) -> str:
    lines = ["---"]
    seen: set[str] = set()
    for key in META_ORDER:
        raw = meta.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        lines.append(f"{key}: {yaml_scalar(raw)}")
        seen.add(key)
    for key, raw in meta.items():
        if key in seen or raw is None or str(raw).strip() == "":
            continue
        lines.append(f"{key}: {yaml_scalar(raw)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"

POST_ID_RE = re.compile(r"^post-\d+$")
CARDS_OUT = ROOT / "cards" / "out"


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
    planned_date: str | None = None,
    hooppy_schedule: str | None = None,
    hooppy_schedule_id: int | str | None = None,
) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    when = date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    path = POSTS_DIR / f"{post_id}.md"
    deck = normalize_marp_deck(marp or "")
    style_name = clamp_style(style or ("findoc" if deck else None))
    meta = {
        "date": when,
        "slides": slides,
        "style": style_name,
        "planned_date": format_planned_date(planned_date) if planned_date else "",
        "hooppy_schedule": hooppy_schedule,
        "hooppy_schedule_id": hooppy_schedule_id,
    }
    parts = [dump_frontmatter(meta), f"# {title.strip()}\n"]
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


def update_post_meta(post_id: str, fields: dict) -> dict:
    path = POSTS_DIR / f"{post_id}.md"
    if not path.is_file():
        raise ValueError(f"Пост {post_id} не найден")
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    for key, value in fields.items():
        if value is None or str(value).strip() == "":
            meta.pop(key, None)
        elif key == "planned_date":
            meta[key] = format_planned_date(value)
        else:
            meta[key] = value
    path.write_text(dump_frontmatter(meta) + body + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")
    return parse_post(path)


def _unlink(path: Path, removed: list[str]) -> None:
    if path.is_file():
        path.unlink()
        removed.append(path.name)


def files_for_post(post_id: str) -> list[Path]:
    files = [POSTS_DIR / f"{post_id}.md"]
    files.append(IMAGES_DIR / f"{post_id}.jpg")
    files.extend(sorted(IMAGES_DIR.glob(f"{post_id}-*.jpg")))
    files.append(IMAGES_DIR / f"{post_id}.png")
    files.extend(sorted(IMAGES_DIR.glob(f"{post_id}-*.png")))
    if CARDS_OUT.is_dir():
        files.extend(sorted(CARDS_OUT.glob(f"{post_id}.*.jpg")))
        files.extend(sorted(CARDS_OUT.glob(f"{post_id}.*.png")))
    return files


def delete_posts(ids: list[str] | str | None) -> list[dict]:
    raw_ids = ids if isinstance(ids, list) else [ids]
    seen: list[str] = []
    deleted: list[dict] = []
    for raw in raw_ids:
        post_id = str(raw or "").strip()
        if not post_id:
            continue
        if not POST_ID_RE.fullmatch(post_id):
            raise ValueError(f"Некорректный идентификатор: {post_id}")
        if post_id in seen:
            continue
        seen.append(post_id)
        removed: list[str] = []
        for path in files_for_post(post_id):
            _unlink(path, removed)
        if not removed:
            raise ValueError(f"Пост {post_id} не найден")
        deleted.append({"id": post_id, "files": removed})
    if not deleted:
        raise ValueError("Выберите посты для удаления")
    return deleted


def create_post(
    title: str,
    description: str,
    slides: int | str | None = 3,
    date: str | None = None,
    render: bool = True,
    cards: list[str] | None = None,
    style: str | None = None,
    marp: str | None = None,
    planned_date: str | None = None,
    hooppy_schedule: str | None = None,
    hooppy_schedule_id: int | str | None = None,
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
    path = write_markdown(
        post_id,
        title,
        description,
        slides_n,
        date,
        copy,
        style,
        deck,
        planned_date=planned_date,
        hooppy_schedule=hooppy_schedule,
        hooppy_schedule_id=hooppy_schedule_id,
    )
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
