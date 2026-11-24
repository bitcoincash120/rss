"""Hooppy API client: token, schedules and publishing."""

from __future__ import annotations

import json
import os
import re
import secrets
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from html import escape
from pathlib import Path

from posts_md import IMAGES_DIR, ROOT

API = "https://api.hooppy.ru/api"
TOKEN_ENV = "HOOPPY_TOKEN"
TOKEN_PATH = ROOT / ".hooppy_token"
STATES = {
    1: "активно",
    2: "ожидает запуска",
    3: "остановлено",
}


def token(explicit: str | None = None) -> str:
    value = str(explicit or "").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if value:
        return value
    env = os.environ.get(TOKEN_ENV, "").strip()
    if env:
        return env
    if TOKEN_PATH.is_file():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    return ""


def save_token(value: str) -> bool:
    text = str(value or "").strip()
    if text.lower().startswith("bearer "):
        text = text[7:].strip()
    if not text:
        return TOKEN_PATH.is_file()
    TOKEN_PATH.write_text(text + "\n", encoding="utf-8")
    try:
        TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
    return True


def has_token(explicit: str | None = None) -> bool:
    return bool(token(explicit))


def _get(path: str, tok: str) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "User-Agent": "github-rss",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        try:
            payload = json.loads(detail)
            detail = str(payload.get("message") or payload.get("error") or detail)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(detail or f"Hooppy {exc.code}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Hooppy вернул не JSON") from exc
    return data if isinstance(data, dict) else {}


def _normalize(item: dict) -> dict | None:
    try:
        sid = int(item.get("id") or 0)
    except (TypeError, ValueError):
        return None
    if sid <= 0:
        return None
    try:
        state = int(item.get("state") or 0)
    except (TypeError, ValueError):
        state = 0
    try:
        posts_count = int(item.get("posts_count") or 0)
    except (TypeError, ValueError):
        posts_count = 0
    return {
        "id": sid,
        "name": str(item.get("name") or "").strip() or f"Расписание {sid}",
        "state": state,
        "state_label": STATES.get(state, "неизвестно"),
        "posts_count": posts_count,
    }


def fetch_schedules(explicit_token: str | None = None) -> list[dict]:
    tok = token(explicit_token)
    if not tok:
        raise ValueError("Нет токена Hooppy. Сохраните его в админке.")
    rows: list[dict] = []
    try:
        data = _get("/posts/schedules/json", tok)
        rows = list(data.get("schedules") or data.get("list") or [])
    except RuntimeError:
        page = 1
        while page <= 50:
            data = _get(f"/posts/schedules?page={page}", tok)
            chunk = list(data.get("list") or [])
            rows.extend(chunk)
            total = int(data.get("total_rows") or 0)
            limit = int(data.get("rows_limit") or 20) or 20
            if not chunk or not data.get("is_has_more") and page * limit >= total:
                break
            page += 1
    seen: set[int] = set()
    out: list[dict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        parsed = _normalize(item)
        if not parsed or parsed["id"] in seen:
            continue
        seen.add(parsed["id"])
        out.append(parsed)
    return out


DATE_RE = re.compile(
    r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})(?:\s+[T ]?(\d{1,2})[:.](\d{2}))?\s*$"
)
ISO_RE = re.compile(
    r"^\s*(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{1,2}):(\d{2}))?"
)
GVIZ_RE = re.compile(r"Date\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def _pad(value: int | str, size: int = 2) -> str:
    return str(value).strip().zfill(size)


def _year(value: int) -> int:
    if value < 100:
        return 2000 + value
    return value


def parse_publication_date(raw: str | None, *, times: list | None = None) -> dict | None:
    text = str(raw or "").strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return None
    day = month = year = None
    hours = minutes = None
    match = DATE_RE.match(text.replace(",", "."))
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), _year(int(match.group(3)))
        if match.group(4) is not None:
            hours, minutes = int(match.group(4)), int(match.group(5))
    else:
        match = ISO_RE.match(text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if match.group(4) is not None:
                hours, minutes = int(match.group(4)), int(match.group(5))
        else:
            match = GVIZ_RE.search(text)
            if match:
                year, month, day = int(match.group(1)), int(match.group(2)) + 1, int(match.group(3))
            elif re.fullmatch(r"\d+(\.0+)?", text):
                serial = int(float(text))
                if 20000 < serial < 80000:
                    parsed = datetime(1899, 12, 30) + timedelta(days=serial)
                    year, month, day = parsed.year, parsed.month, parsed.day
    if not day or not month or not year:
        return None
    try:
        when = datetime(year, month, day)
    except ValueError:
        return None
    if hours is None or minutes is None:
        hours, minutes = _slot_for_weekday(when.weekday(), times)
    return {
        "date": f"{day:02d}.{month:02d}.{year:04d}",
        "hours": _pad(hours),
        "minutes": _pad(minutes),
        "display": f"{day:02d}.{month:02d}.{year:04d}",
    }


def format_planned_date(raw: str | None) -> str:
    parsed = parse_publication_date(raw)
    return parsed["display"] if parsed else str(raw or "").strip()


def _slot_for_weekday(weekday: int, times: list | None) -> tuple[int, int]:
    rows = list(times or [])
    if weekday < len(rows):
        slot = _first_slot(rows[weekday])
        if slot:
            return slot
    for row in rows:
        slot = _first_slot(row)
        if slot:
            return slot
    return 10, 0


def _first_slot(row) -> tuple[int, int] | None:
    if not isinstance(row, list):
        return None
    for item in row:
        if not isinstance(item, dict):
            continue
        try:
            return int(item.get("hours") or 0), int(item.get("minutes") or 0)
        except (TypeError, ValueError):
            continue
    return None


def _json_request(method: str, path: str, tok: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "User-Agent": "github-rss",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{API}{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        try:
            parsed = json.loads(detail)
            detail = str(parsed.get("message") or parsed.get("error") or detail)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(detail or f"Hooppy {exc.code}") from exc
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Hooppy вернул не JSON") from exc
    return data if isinstance(data, dict) else {}


def _upload_photo(path: Path, tok: str) -> dict:
    file_id = secrets.token_hex(6) + "_" + secrets.token_hex(5)
    filename = path.name
    content = path.read_bytes()
    boundary = "----rss" + uuid.uuid4().hex
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file_id"\r\n\r\n{file_id}\r\n'
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8"),
        content,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(parts)
    req = urllib.request.Request(
        f"{API}/files/media/upload",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "github-rss",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        try:
            parsed = json.loads(detail)
            detail = str(parsed.get("message") or parsed.get("error") or detail)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(detail or "Hooppy не принял картинку") from exc
    data = json.loads(raw)
    photo = data.get("photo") if isinstance(data, dict) else None
    if not isinstance(photo, dict):
        raise RuntimeError("Hooppy не вернул загруженное фото")
    return photo


def _post_text(title: str, description: str) -> str:
    chunks = []
    heading = escape((title or "").strip())
    body = escape((description or "").strip())
    if heading:
        chunks.append(f"<p><b>{heading}</b></p>")
    if body and body != heading:
        chunks.append(f"<p>{body}</p>")
    return "".join(chunks) or "<p></p>"


def _pages_from_schedule(config: dict) -> dict:
    pages = config.get("selected_pages_by_source_ids") or {}
    if isinstance(pages, dict) and pages:
        return {"selected_pages_by_source_ids": pages}
    ids = config.get("selected_pages_ids") or []
    if ids:
        return {"selected_pages_ids": list(ids)}
    raise ValueError("В расписании не выбраны страницы для публикации")


def publish_to_schedule(
    post: dict,
    *,
    schedule_id: int | str,
    explicit_token: str | None = None,
) -> dict:
    tok = token(explicit_token)
    if not tok:
        raise ValueError("Нет токена Hooppy. Сохраните его в админке.")
    try:
        sid = int(schedule_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Нужно выбрать расписание Hooppy") from exc
    if sid <= 0:
        raise ValueError("Нужно выбрать расписание Hooppy")
    config = _get(f"/posts/schedules/{sid}/edit", tok)
    photos = []
    for name in post.get("image_files") or []:
        path = IMAGES_DIR / Path(str(name)).name
        if path.is_file():
            photos.append(_upload_photo(path, tok))
    attachments: list[dict] = []
    if photos:
        attachments.append({"type": "photos", "data": photos})
    texts = [{"text": _post_text(post.get("title") or "", post.get("description") or ""), "source_id": 0}]
    payload = {
        "publication_when_type": 3,
        "publication_how_type": int(config.get("publication_how_type") or 1),
        "schedules_ids": [sid],
        "texts": texts,
        "attachments": attachments,
    }
    created = _json_request("POST", "/posts", tok, payload)
    return {
        "id": created.get("id"),
        "schedule_id": sid,
        "schedule_name": str(config.get("name") or ""),
        "when_type": 3,
    }


def _pack_attachments(items: list) -> list:
    photos = []
    extra = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        typ = str(item.get("type") or "")
        data = item.get("data")
        if typ in {"photo", "video"} and isinstance(data, dict):
            photos.append(data)
        elif typ in {"photos", "videos"} and isinstance(data, list):
            photos.extend(part for part in data if isinstance(part, dict))
        elif typ:
            extra.append({"type": typ, "data": data})
    packed = []
    if photos:
        packed.append({"type": "photos", "data": photos})
    packed.extend(extra)
    return packed


def set_publication_date(
    post_id: int | str,
    *,
    planned_date: str,
    schedule_id: int | str | None = None,
    explicit_token: str | None = None,
) -> dict:
    tok = token(explicit_token)
    if not tok:
        raise ValueError("Нет токена Hooppy. Сохраните его в админке.")
    pid = int(post_id)
    edit = _get(f"/posts/{pid}/edit", tok)
    config = None
    sid = schedule_id or edit.get("schedule_id")
    if sid:
        config = _get(f"/posts/schedules/{int(sid)}/edit", tok)
    planned = parse_publication_date(planned_date, times=(config or {}).get("times"))
    if not planned:
        raise ValueError("Нет даты публикации")
    if config:
        pages = _pages_from_schedule(config)
    elif edit.get("selected_pages_by_source_ids"):
        pages = {"selected_pages_by_source_ids": edit["selected_pages_by_source_ids"]}
    elif edit.get("selected_pages_ids"):
        pages = {"selected_pages_ids": edit["selected_pages_ids"]}
    else:
        raise ValueError("Нет страниц для публикации")
    texts = [
        {"text": item.get("text") or "", "source_id": int(item.get("source_id") or 0)}
        for item in (edit.get("texts") or [])
    ] or [{"text": "<p></p>", "source_id": 0}]
    payload = {
        "publication_when_type": 2,
        "publication_how_type": 1,
        "publication_date": {
            "date": planned["date"],
            "hours": planned["hours"],
            "minutes": planned["minutes"],
        },
        "texts": texts,
        "attachments": _pack_attachments(edit.get("attachments") or []),
        **pages,
    }
    _json_request("PUT", f"/posts/{pid}", tok, payload)
    return planned
