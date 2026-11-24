"""Load post drafts from the public Google Sheet and mark imported rows."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

SHEET_ID = "19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI"
SHEET_GID = "0"
SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={SHEET_GID}#gid={SHEET_GID}"
)
SHEET_CSV = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1&gid={SHEET_GID}"
)
SITE_URL = "https://bitcoincash120.github.io/rss"
IMPORTED_STATUS = "импортирован"
WEBHOOK_ENV = "SHEET_WEBHOOK"
DEFAULT_WEBHOOK = (
    "https://script.google.com/macros/s/"
    "AKfycbz4rHUVVCe3imLSysN1EaQAxT5bm-WEVr9wwR6B9rN926tLP07wrCj8dKMFyxJ_UbDb/exec"
)
TITLE_KEYS = {"заголовок", "title", "headline", "тема", "name"}
TEXT_KEYS = {"текст", "text", "описание", "анонс", "description", "body"}
SLIDE_KEYS = {"карточки", "slides", "фото", "photos", "slide"}
STATUS_KEYS = {"статус", "status", "state"}
LINK_KEYS = {"ссылка", "link", "url", "пост"}
IMPORTED_MARKS = {"импортирован", "imported", "готово", "published", "опубликован"}
CARD_HEADER = re.compile(
    r"^(?:карточка|card|текст|slide)\s*(\d+)$",
    re.IGNORECASE,
)

HEADER_KEYS = TITLE_KEYS | TEXT_KEYS | SLIDE_KEYS | STATUS_KEYS | LINK_KEYS


def _norm(header: str) -> str:
    return re.sub(r"\s+", " ", str(header or "").strip().lower())


def _index(headers: list[str], keys: set[str], default: int) -> int:
    for i, header in enumerate(headers):
        name = _norm(header)
        if name in keys:
            return i
        for key in keys:
            if name.startswith(f"{key} ") or name.startswith(f"{key}\n"):
                return i
    return default


def _card_columns(headers: list[str]) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for i, header in enumerate(headers):
        name = _norm(header)
        match = re.match(r"^(карточка|card|текст|slide)\s*(\d+)$", name)
        if not match:
            match = re.match(r"^(карточка|card|текст|slide)(\d+)$", name.replace(" ", ""))
        if match:
            found.append((int(match.group(2)), i))
    found.sort()
    return found


def _colmap(headers: list[str]) -> dict:
    return {
        "title": _index(headers, TITLE_KEYS, 2 if len(headers) > 2 else 0),
        "text": _index(headers, TEXT_KEYS, -1),
        "slide": _index(headers, SLIDE_KEYS, -1),
        "status": _index(headers, STATUS_KEYS, 0),
        "link": _index(headers, LINK_KEYS, 1),
        "cards": _card_columns(headers),
    }


def _cell(values: list[str], index: int) -> str:
    if index < 0 or index >= len(values):
        return ""
    return str(values[index]).strip()


def _is_imported(status: str) -> bool:
    return status.strip().lower() in IMPORTED_MARKS


def _idea(values: list[str], cols: dict, row: int) -> dict | None:
    title = _cell(values, cols["title"])
    legacy = _cell(values, cols["text"])
    cards: list[str] = []
    if cols["cards"]:
        by_number = {number: _cell(values, index) for number, index in cols["cards"]}
        highest = max(by_number)
        cards = [by_number.get(index, "") for index in range(1, highest + 1)]
        while cards and not cards[-1]:
            cards.pop()
    cards = [text for text in cards if text]
    if not cards and legacy:
        cards = [legacy]
    description = next(iter(cards), "") or legacy
    if not title or not description:
        return None
    if title.lower() in TITLE_KEYS:
        return None
    idea: dict = {
        "title": title,
        "description": description,
        "cards": cards,
        "row": row,
        "imported": _is_imported(_cell(values, cols["status"])),
        "link": _cell(values, cols["link"]),
    }
    raw = _cell(values, cols["slide"])
    try:
        listed = int(raw) if raw else 0
    except ValueError:
        listed = 0
    idea["slides"] = max(1, len(cards) or listed or 1)
    return idea


def parse_csv(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    headers = [_norm(cell) for cell in rows[0]]
    named = any(
        header in HEADER_KEYS or CARD_HEADER.match(header) or CARD_HEADER.match(header.replace(" ", ""))
        for header in headers
    )
    start = 1 if named else 0
    cols = _colmap(headers)
    ideas = []
    for offset, row in enumerate(rows[start:]):
        idea = _idea(row, cols, start + offset + 1)
        if idea:
            ideas.append(idea)
    return ideas


def parse_gviz(table: dict) -> list[dict]:
    cols_meta = table.get("cols") or []
    headers = [_norm(col.get("label") or "") for col in cols_meta]
    colmap = _colmap(headers)
    ideas = []
    for index, row in enumerate(table.get("rows") or []):
        cells = row.get("c") or []
        values = []
        for cell in cells:
            value = "" if not cell else cell.get("f") or cell.get("v")
            values.append("" if value is None else str(value))
        idea = _idea(values, colmap, index + 2)
        if idea:
            ideas.append(idea)
    return ideas


def fetch_ideas(*, include_imported: bool = False) -> list[dict]:
    url = f"{SHEET_CSV}&_={int(time.time() * 1000)}"
    req = urllib.request.Request(url, headers={"User-Agent": "github-rss", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=12) as response:
        payload = response.read().decode("utf-8-sig")
    if payload.lstrip().startswith("/*") or "google.visualization" in payload[:80]:
        match = re.search(r"setResponse\((\{.*\})\)\s*;?\s*$", payload, re.S)
        if not match:
            return []
        table = json.loads(match.group(1)).get("table") or {}
        ideas = parse_gviz(table)
    else:
        ideas = parse_csv(payload)
    if include_imported:
        return ideas
    return [idea for idea in ideas if not idea.get("imported")]


def post_url(post_id: str, origin: str | None = None) -> str:
    base = str(origin or "").strip().rstrip("/")
    if not base:
        base = SITE_URL
    return f"{base}/#{post_id}"


def mark_imported(row: int, url: str) -> dict:
    webhook = os.environ.get(WEBHOOK_ENV, "").strip() or DEFAULT_WEBHOOK
    if not webhook:
        return {
            "ok": False,
            "error": "Нет SHEET_WEBHOOK: нечем записать статус в таблицу",
        }
    params = urllib.parse.urlencode(
        {"row": int(row), "url": url, "status": IMPORTED_STATUS}
    )
    separator = "&" if "?" in webhook else "?"
    req = urllib.request.Request(
        f"{webhook}{separator}{params}",
        headers={"User-Agent": "github-rss"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": True, "raw": body}
