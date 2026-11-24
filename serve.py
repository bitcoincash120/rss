#!/usr/bin/env python3
"""Serve the feed locally and accept new posts from /new.html."""

from __future__ import annotations

import importlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import generate_cards
import generate_post
import generate_rss
import generate_site
import hooppy
import posts_md
import sheet_ideas
import site_settings
from posts_md import ROOT


def reload_builders() -> None:
    importlib.reload(posts_md)
    importlib.reload(site_settings)
    importlib.reload(generate_cards)
    importlib.reload(generate_post)
    importlib.reload(generate_site)
    importlib.reload(generate_rss)
    importlib.reload(hooppy)


def rebuild_public() -> None:
    generate_site.main()
    generate_rss.main()


def request_origin(handler: SimpleHTTPRequestHandler, payload: dict) -> str:
    origin = str(payload.get("origin") or "").strip().rstrip("/")
    if origin:
        return origin
    header = (handler.headers.get("Origin") or "").strip().rstrip("/")
    if header:
        return header
    host = handler.headers.get("Host") or "127.0.0.1:3000"
    return f"http://{host}"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)
        if path == "/api/import/preview":
            try:
                row = int((query.get("row") or ["0"])[0])
                importlib.reload(sheet_ideas)
                importlib.reload(generate_cards)
                idea = next((item for item in sheet_ideas.fetch_ideas() if int(item.get("row") or 0) == row), None)
                if not idea:
                    self._json(404, {"ok": False, "error": f"Строка {row} не найдена или уже импортирована"})
                    return
                style = (query.get("style") or ["blue"])[0]
                images = generate_cards.render_preview(idea, style=style)
                self._json(200, {"ok": True, "row": row, "style": style, "images": images, "slides": len(images)})
            except Exception as exc:  # noqa: BLE001
                self._json(502, {"ok": False, "error": str(exc), "images": []})
            return
        if path == "/api/ideas":
            try:
                importlib.reload(sheet_ideas)
                ideas = sheet_ideas.fetch_ideas()
                self._json(200, {"ideas": ideas, "source": "sheet", "url": sheet_ideas.SHEET_URL})
            except Exception as exc:  # noqa: BLE001
                self._json(502, {"error": str(exc), "ideas": [], "url": sheet_ideas.SHEET_URL})
            return
        if path == "/api/settings":
            importlib.reload(site_settings)
            self._json(200, {"settings": site_settings.load_settings()})
            return
        if path == "/api/hooppy/token":
            importlib.reload(hooppy)
            saved = hooppy.token()
            self._json(200, {"ok": True, "saved": bool(saved), "token": saved})
            return
        if path == "/api/hooppy/schedules":
            try:
                importlib.reload(hooppy)
                schedules = hooppy.fetch_schedules(self.headers.get("X-Hooppy-Token") or self.headers.get("Authorization"))
            except ValueError as exc:
                self._json(401, {"ok": False, "error": str(exc), "schedules": []})
                return
            except Exception as exc:  # noqa: BLE001
                self._json(502, {"ok": False, "error": str(exc), "schedules": []})
                return
            self._json(200, {"ok": True, "schedules": schedules})
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = self.path.rstrip("/")
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "Некорректный JSON"})
            return
        if path == "/api/ideas/imported":
            try:
                importlib.reload(sheet_ideas)
                marked = sheet_ideas.mark_imported(
                    int(payload.get("row") or 0),
                    payload.get("url") or "",
                )
            except Exception as exc:  # noqa: BLE001
                self._json(502, {"ok": False, "error": str(exc)})
                return
            self._json(200 if marked.get("ok") else 502, marked)
            return
        if path == "/api/hooppy/token":
            try:
                importlib.reload(hooppy)
                incoming = payload.get("token") if "token" in payload else payload.get("hooppy_token")
                if incoming is None or not str(incoming).strip():
                    self._json(200, {"ok": True, "saved": hooppy.has_token(), "kept": True})
                    return
                saved = hooppy.save_token(str(incoming))
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(200, {"ok": True, "saved": saved})
            return
        if path == "/api/settings":
            try:
                reload_builders()
                settings = site_settings.save_settings(payload)
                rebuild_public()
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(200, {"ok": True, "settings": settings})
            return
        if path == "/api/posts/delete":
            try:
                reload_builders()
                deleted = generate_post.delete_posts(payload.get("ids") or payload.get("id"))
                rebuild_public()
            except ValueError as exc:
                self._json(400, {"ok": False, "error": str(exc)})
                return
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(200, {"ok": True, "deleted": deleted})
            return
        if path == "/api/import":
            self._import_posts(payload)
            return
        if path != "/api/posts":
            self.send_error(404)
            return
        try:
            reload_builders()
            post = generate_post.create_post(
                payload.get("title") or "",
                payload.get("description") or "",
                payload.get("slides"),
                payload.get("date"),
                cards=payload.get("cards"),
                style=payload.get("style"),
                marp=payload.get("marp"),
            )
            rebuild_public()
            sheet_marked = None
            row = payload.get("row")
            if row:
                importlib.reload(sheet_ideas)
                post_url = sheet_ideas.post_url(post["id"], request_origin(self, payload))
                sheet_marked = sheet_ideas.mark_imported(int(row), post_url)
                print("sheet_marked", sheet_marked)
            hooppy_sent = None
            hooppy_error = None
            schedule_id = payload.get("schedule_id") or payload.get("schedule")
            if schedule_id:
                try:
                    importlib.reload(hooppy)
                    hooppy_sent = hooppy.publish_to_schedule(
                        post,
                        schedule_id=schedule_id,
                        explicit_token=self.headers.get("X-Hooppy-Token") or self.headers.get("Authorization"),
                    )
                    print("hooppy_sent", (hooppy_sent or {}).get("id"), (hooppy_sent or {}).get("schedule_name"), flush=True)
                    schedule_name = (hooppy_sent or {}).get("schedule_name") or payload.get("schedule_name") or ""
                    post = generate_post.update_post_meta(
                        post["id"],
                        {
                            "hooppy_schedule": schedule_name,
                            "hooppy_schedule_id": (hooppy_sent or {}).get("schedule_id") or schedule_id,
                        },
                    )
                    rebuild_public()
                except Exception as exc:  # noqa: BLE001
                    hooppy_error = str(exc)
                    print("hooppy_error", hooppy_error, flush=True)
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._json(500, {"error": str(exc)})
            return
        self._json(
            201,
            {
                "id": post["id"],
                "title": post["title"],
                "url": f"/feed.html#{post['id']}",
                "images": post.get("image_files") or [],
                "cards_error": post.get("cards_error"),
                "sheet_marked": bool(sheet_marked and sheet_marked.get("ok")),
                "sheet_error": None
                if sheet_marked and sheet_marked.get("ok")
                else (sheet_marked or {}).get("error")
                if row
                else "Нет номера строки таблицы",
                "hooppy": hooppy_sent,
                "hooppy_error": hooppy_error,
            },
        )

    def _ndjson_begin(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

    def _ndjson(self, payload: dict) -> None:
        self.wfile.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        self.wfile.flush()

    def _import_posts(self, payload: dict) -> None:
        schedule_id = payload.get("schedule_id") or payload.get("schedule")
        rows = payload.get("rows") or payload.get("ids") or []
        try:
            rows = [int(row) for row in rows if str(row).strip()]
        except (TypeError, ValueError):
            self._json(400, {"error": "Нужны номера строк таблицы"})
            return
        if not schedule_id:
            self._json(400, {"error": "Выберите расписание Hooppy"})
            return
        if not rows:
            self._json(400, {"error": "Выберите посты для импорта"})
            return
        token_header = self.headers.get("X-Hooppy-Token") or self.headers.get("Authorization")
        origin = request_origin(self, payload)
        self._ndjson_begin()
        try:
            reload_builders()
            importlib.reload(sheet_ideas)
            ideas = {int(item.get("row") or 0): item for item in sheet_ideas.fetch_ideas()}
            schedule_name = str(payload.get("schedule_name") or "")
            row_styles = payload.get("styles") if isinstance(payload.get("styles"), dict) else {}
            self._ndjson({"event": "start", "total": len(rows), "message": f"К импорту {len(rows)} постов."})
            ok = 0
            fail = 0
            for index, row in enumerate(rows, 1):
                idea = ideas.get(row)
                title = (idea or {}).get("title") or f"Строка {row}"
                if not idea:
                    fail += 1
                    self._ndjson(
                        {
                            "event": "item",
                            "ok": False,
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "title": title,
                            "message": "Строка не найдена или уже импортирована.",
                        }
                    )
                    continue
                try:
                    self._ndjson(
                        {
                            "event": "progress",
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "title": title,
                            "step": "cards",
                            "message": f"{index}/{len(rows)} Собираю карточки: {title}",
                        }
                    )
                    post = generate_post.create_post(
                        idea.get("title") or "",
                        idea.get("description") or "",
                        idea.get("slides"),
                        cards=idea.get("cards"),
                        style=row_styles.get(str(row)) or payload.get("style") or "blue",
                        marp=idea.get("marp"),
                    )
                    self._ndjson(
                        {
                            "event": "progress",
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "title": title,
                            "step": "hooppy",
                            "message": f"{index}/{len(rows)} Отправляю в Hooppy: {title}",
                        }
                    )
                    hooppy_sent = hooppy.publish_to_schedule(
                        post,
                        schedule_id=schedule_id,
                        explicit_token=token_header,
                    )
                    schedule_name = (hooppy_sent or {}).get("schedule_name") or schedule_name
                    generate_post.update_post_meta(
                        post["id"],
                        {
                            "hooppy_schedule": schedule_name,
                            "hooppy_schedule_id": (hooppy_sent or {}).get("schedule_id") or schedule_id,
                        },
                    )
                    self._ndjson(
                        {
                            "event": "progress",
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "title": title,
                            "step": "sheet",
                            "message": f"{index}/{len(rows)} Помечаю строку в таблице: {title}",
                        }
                    )
                    post_url = sheet_ideas.post_url(post["id"], origin)
                    marked = sheet_ideas.mark_imported(row, post_url)
                    ok += 1
                    self._ndjson(
                        {
                            "event": "item",
                            "ok": True,
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "id": post["id"],
                            "title": title,
                            "images": post.get("image_files") or [],
                            "hooppy": hooppy_sent,
                            "sheet_marked": bool(marked and marked.get("ok")),
                            "message": f"{index}/{len(rows)} Готово: {post['id']} → {schedule_name or 'Hooppy'}.",
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    fail += 1
                    print("import_error", row, exc, flush=True)
                    self._ndjson(
                        {
                            "event": "item",
                            "ok": False,
                            "index": index,
                            "total": len(rows),
                            "row": row,
                            "title": title,
                            "message": str(exc),
                        }
                    )
            rebuild_public()
            self._ndjson(
                {
                    "event": "done",
                    "ok": ok,
                    "fail": fail,
                    "total": len(rows),
                    "message": f"Импорт закончен: {ok} успешно, {fail} с ошибкой.",
                }
            )
        except Exception as exc:  # noqa: BLE001
            self._ndjson({"event": "done", "ok": 0, "fail": len(rows), "total": len(rows), "message": str(exc)})

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    reload_builders()
    rebuild_public()
    server = ThreadingHTTPServer(("127.0.0.1", 3000), Handler)
    print("http://127.0.0.1:3000/")
    server.serve_forever()


if __name__ == "__main__":
    main()
