"""Load post drafts from the public Google Sheet."""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.request

SHEET_ID = "19ZlYXpbgZ8lvlkniXU-BoxVuLewfFX0xh-nX97DN2VI"
SHEET_GID = "0"
SHEET_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?gid={SHEET_GID}#gid={SHEET_GID}"
)
SHEET_CSV = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={SHEET_GID}"
)

TITLE_KEYS = {"заголовок", "title", "headline", "тема", "name"}
TEXT_KEYS = {"текст", "text", "описание", "анонс", "description", "body"}
SLIDE_KEYS = {"карточки", "slides", "фото", "photos", "slide"}


def _index(headers: list[str], keys: set[str], default: int) -> int:
    for i, header in enumerate(headers):
        if header in keys:
            return i
    return default


def _idea(values: list[str], title_i: int, text_i: int, slide_i: int) -> dict | None:
    title = values[title_i].strip() if title_i < len(values) else ""
    description = values[text_i].strip() if text_i < len(values) else ""
    if not title or not description:
        return None
    if title.lower() in TITLE_KEYS or description.lower() in TEXT_KEYS:
        return None
    idea: dict = {"title": title, "description": description}
    raw = values[slide_i].strip() if slide_i < len(values) else ""
    if raw in {"2", "3"}:
        idea["slides"] = int(raw)
    return idea


def parse_csv(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    headers = [cell.strip().lower() for cell in rows[0]]
    named = any(header in TITLE_KEYS | TEXT_KEYS | SLIDE_KEYS for header in headers)
    start = 1 if named else 0
    title_i = _index(headers, TITLE_KEYS, 0)
    text_i = _index(headers, TEXT_KEYS, 1)
    slide_i = _index(headers, SLIDE_KEYS, 2)
    ideas = []
    for row in rows[start:]:
        idea = _idea(row, title_i, text_i, slide_i)
        if idea:
            ideas.append(idea)
    return ideas


def fetch_ideas() -> list[dict]:
    req = urllib.request.Request(SHEET_CSV, headers={"User-Agent": "github-rss"})
    with urllib.request.urlopen(req, timeout=12) as response:
        payload = response.read().decode("utf-8-sig")
    if payload.lstrip().startswith("/*") or "google.visualization" in payload[:80]:
        match = re.search(r"setResponse\((\{.*\})\)\s*;?\s*$", payload, re.S)
        if not match:
            return []
        table = json.loads(match.group(1)).get("table") or {}
        return parse_gviz(table)
    return parse_csv(payload)


def parse_gviz(table: dict) -> list[dict]:
    cols = table.get("cols") or []
    headers = [str(col.get("label") or "").strip().lower() for col in cols]
    named = any(header in TITLE_KEYS | TEXT_KEYS | SLIDE_KEYS for header in headers)
    title_i = _index(headers, TITLE_KEYS, 0)
    text_i = _index(headers, TEXT_KEYS, 1)
    slide_i = _index(headers, SLIDE_KEYS, 2)
    ideas = []
    for row in table.get("rows") or []:
        cells = row.get("c") or []
        values = []
        for cell in cells:
            value = "" if not cell else cell.get("f") or cell.get("v")
            values.append("" if value is None else str(value))
        idea = _idea(values, title_i, text_i, slide_i)
        if idea:
            ideas.append(idea)
    if not named:
        return ideas
    return ideas
