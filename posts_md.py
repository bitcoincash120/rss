from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from html import unescape

DISPLAY_TZ = timezone(timedelta(hours=4))
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
IMAGES_DIR = ROOT / "images"
SITE_URL = "https://bitcoincash120.github.io/rss"
STYLES = ("night", "paper", "studio", "findoc")
DEFAULT_STYLE = "findoc"


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


def card_image_name(post_id: str, index: int) -> str:
    if index <= 1:
        return f"{post_id}.jpg"
    return f"{post_id}-{index}.jpg"


def image_names(post_id: str) -> list[str]:
    names: list[str] = []
    first = IMAGES_DIR / f"{post_id}.jpg"
    if first.is_file():
        names.append(first.name)
    numbered: list[tuple[int, str]] = []
    prefix = f"{post_id}-"
    for path in IMAGES_DIR.glob(f"{post_id}-*.jpg"):
        suffix = path.stem[len(prefix) :]
        if suffix.isdigit():
            numbered.append((int(suffix), path.name))
    numbered.sort()
    names.extend(name for _, name in numbered)
    return names


CARD_HEADING = re.compile(r"^#{2,3}\s*(\d+)\s*$")
ARTICLE_RE = re.compile(r"<article\b[\s\S]*?</article>", re.I)
MARP_DECK_RE = re.compile(r"(?:^|\n)(---[ \t]*\nmarp:[ \t]*true\b[\s\S]*)", re.I)
TAG_RE = re.compile(r"<[^>]+>")
H3_RE = re.compile(r"<h3\b[^>]*>([\s\S]*?)</h3>", re.I)
P_RE = re.compile(r"<p\b[^>]*>([\s\S]*?)</p>", re.I)
KICKER_RE = re.compile(r'<div class="kicker">([\s\S]*?)</div>', re.I)


def html_to_text(fragment: str) -> str:
    text = re.sub(r"<div[^>]*aria-hidden[^>]*>[\s\S]*?</div>", " ", fragment or "", flags=re.I)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_marp_deck(text: str) -> str:
    raw = str(text or "")
    match = MARP_DECK_RE.search(raw)
    if match:
        return match.group(1).strip()
    start = raw.lower().find("<article")
    if start >= 0:
        return raw[start:].strip()
    return ""


def count_marp_slides(marp: str) -> int:
    return len(ARTICLE_RE.findall(marp or ""))


def cards_from_marp(marp: str) -> list[str]:
    cards: list[str] = []
    for article in ARTICLE_RE.findall(marp or ""):
        heading = html_to_text(H3_RE.search(article).group(1) if H3_RE.search(article) else "")
        para = html_to_text(P_RE.search(article).group(1) if P_RE.search(article) else "")
        piece = "\n\n".join(part for part in (heading, para) if part)
        if not piece:
            piece = html_to_text(article)
            for noise in ("Листай →", "Сохраните", "@fin_doc_"):
                piece = piece.replace(noise, " ")
            piece = re.sub(r"\b\d{2}/\d{2}\b", " ", piece)
            piece = re.sub(r"\s+", " ", piece).strip()
        if piece:
            cards.append(piece)
    return cards


def normalize_marp_deck(marp: str) -> str:
    text = str(marp or "").strip()
    if not text:
        return ""
    if not MARP_DECK_RE.search("\n" + text) and ARTICLE_RE.search(text):
        text = (
            "---\nmarp: true\ntheme: fin-doc\nsize: carousel\nlang: ru\n"
            "paginate: false\n---\n\n" + text
        )
    # ChatGPT PNGs were rendered with Liberation Serif (Times metrics).
    # Georgia-first stacks wrap headlines differently on macOS.
    text = text.replace(
        "font-family:Georgia,'Liberation Serif',serif",
        "font-family:'Times New Roman','Liberation Serif',Georgia,serif",
    )
    text = text.replace(
        'font-family:Georgia,"Liberation Serif",serif',
        "font-family:'Times New Roman','Liberation Serif',Georgia,serif",
    )
    return text if text.endswith("\n") else text + "\n"


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
    if buckets:
        highest = max(buckets)
        cards = [" ".join(buckets.get(index, [])).strip() for index in range(1, highest + 1)]
        while cards and not cards[-1]:
            cards.pop()
    else:
        cards = []
    description = " ".join(lead).strip()
    if not description:
        description = next((text for text in cards if text), "")
    return title, description, cards


def parse_post(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    marp = extract_marp_deck(body) or (
        raw.strip() if str(meta.get("marp")).lower() in {"true", "yes"} else ""
    )
    prefix = body
    if marp and marp in body:
        prefix = body[: body.index(marp)]
    title, description, cards = split_body(prefix, meta.get("title") or path.stem)
    if marp:
        cards = cards_from_marp(marp) or cards
        if not description:
            description = next((text for text in cards if text), "")
        if (not title or title == path.stem) and meta.get("title"):
            title = meta.get("title") or title
    post_id = meta.get("id") or path.stem
    date = meta.get("date") or ""
    filled = [text for text in cards if text]
    article_n = count_marp_slides(marp)
    try:
        slides = max(1, int(meta.get("slides") or article_n or len(filled) or 1))
    except ValueError:
        slides = max(1, article_n or len(filled) or 1)
    slides = max(slides, article_n, len(filled) or 1)
    parsed_date = None
    if date:
        parsed_date = datetime.fromisoformat(date.replace("Z", "+00:00"))
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
    style_raw = meta.get("style") or meta.get("theme")
    if marp and not style_raw:
        style_raw = "findoc"
    return {
        "id": post_id,
        "title": title,
        "description": description,
        "cards": cards,
        "marp": marp,
        "date": date,
        "parsed_date": parsed_date,
        "planned_date": str(meta.get("planned_date") or "").strip(),
        "hooppy_schedule": str(meta.get("hooppy_schedule") or "").strip(),
        "hooppy_schedule_id": str(meta.get("hooppy_schedule_id") or "").strip(),
        "link": meta.get("link") or f"{SITE_URL}/#{post_id}",
        "images": [f"{SITE_URL}/images/{name}" for name in image_names(post_id)],
        "image_files": image_names(post_id),
        "slides": slides,
        "style": clamp_style(style_raw),
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


def format_short_dmy(day: int, month: int, year: int) -> str:
    return f"{int(day):02d}.{int(month):02d}.{int(year) % 100:02d}"


def format_added_short(post: dict) -> str:
    parsed = display_date(post)
    if not parsed:
        return ""
    date = format_short_dmy(parsed.day, parsed.month, parsed.year)
    clock = f"{parsed.hour:02d}:{parsed.minute:02d}"
    return f"{date}, {clock}"


SHORT_DATE_RE = re.compile(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})")


def format_planned_short(raw: str | None) -> str:
    text = str(raw or "").strip()
    match = SHORT_DATE_RE.match(text)
    if not match:
        return text
    year = int(match.group(3))
    if year < 100:
        year += 2000
    return format_short_dmy(int(match.group(1)), int(match.group(2)), year)
