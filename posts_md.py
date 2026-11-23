from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

DISPLAY_TZ = timezone(timedelta(hours=4))
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
IMAGES_DIR = ROOT / "images"
SITE_URL = "https://bitcoincash120.github.io/rss"
STYLES = ("night", "paper", "studio")
DEFAULT_STYLE = "night"


def clamp_style(value: str | None) -> str:
    name = str(value or "").strip().lower()
    return name if name in STYLES else DEFAULT_STYLE

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def image_names(post_id: str) -> list[str]:
    names = [f"{post_id}.jpg", f"{post_id}-2.jpg", f"{post_id}-3.jpg"]
    return [name for name in names if (IMAGES_DIR / name).is_file()]


CARD_HEADING = re.compile(r"^#{2,3}\s*(\d+)\s*$")


def split_body(body: str, fallback_title: str = "") -> tuple[str, str, list[str]]:
    title = fallback_title
    lead: list[str] = []
    buckets: dict[int, list[str]] = {}
    current: int | None = None
    found_title = False
    for raw in body.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not found_title and stripped.startswith("# "):
            title = stripped[2:].strip()
            found_title = True
            continue
        match = CARD_HEADING.match(stripped)
        if match:
            current = int(match.group(1))
            buckets.setdefault(current, [])
            continue
        if not stripped:
            continue
        if current is not None:
            buckets[current].append(stripped)
        else:
            lead.append(stripped)
    cards = [" ".join(buckets.get(index, [])).strip() for index in (1, 2, 3)]
    description = " ".join(lead).strip()
    if not description:
        description = next((text for text in (cards[1], cards[0], cards[2]) if text), "")
    return title, description, cards


def parse_post(path: Path) -> dict:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    title, description, cards = split_body(body, path.stem)
    post_id = meta.get("id") or path.stem
    date = meta.get("date") or ""
    try:
        slides = max(2, min(3, int(meta.get("slides") or 3)))
    except ValueError:
        slides = 3
    parsed_date = None
    if date:
        parsed_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
    return {
        "id": post_id,
        "title": title,
        "description": description,
        "cards": cards,
        "date": date,
        "parsed_date": parsed_date,
        "link": meta.get("link") or f"{SITE_URL}/#{post_id}",
        "images": [f"{SITE_URL}/images/{name}" for name in image_names(post_id)],
        "image_files": image_names(post_id),
        "slides": slides,
        "style": clamp_style(meta.get("style") or meta.get("theme")),
        "path": path,
    }


def load_posts() -> list[dict]:
    posts = [parse_post(path) for path in POSTS_DIR.glob("*.md")]
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    posts.sort(
        key=lambda post: (post["parsed_date"] or epoch, post["id"]),
        reverse=True,
    )
    return posts


def display_date(post: dict) -> datetime | None:
    parsed = post.get("parsed_date")
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(DISPLAY_TZ)


def format_date_ru(post: dict) -> str:
    parsed = display_date(post)
    if not parsed:
        return ""
    return f"{parsed.day} {MONTHS_RU[parsed.month]} {parsed.year}"


def format_time_ru(post: dict) -> str:
    parsed = display_date(post)
    if not parsed:
        return ""
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def format_datetime_ru(post: dict) -> str:
    day = format_date_ru(post)
    clock = format_time_ru(post)
    if day and clock:
        return f"{day}, {clock}"
    return day or clock
