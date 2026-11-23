#!/usr/bin/env python3
"""Serve the feed locally and accept new posts from /new.html."""

from __future__ import annotations

import importlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import generate_cards
import generate_post
import generate_rss
import generate_site
import posts_md
import sheet_ideas
from posts_md import ROOT


def reload_builders() -> None:
    importlib.reload(posts_md)
    importlib.reload(generate_cards)
    importlib.reload(generate_post)
    importlib.reload(generate_site)
    importlib.reload(generate_rss)


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
        if self.path.split("?", 1)[0].rstrip("/") == "/api/ideas":
            try:
                importlib.reload(sheet_ideas)
                ideas = sheet_ideas.fetch_ideas()
                self._json(200, {"ideas": ideas, "source": "sheet", "url": sheet_ideas.SHEET_URL})
            except Exception as exc:  # noqa: BLE001
                self._json(502, {"error": str(exc), "ideas": [], "url": sheet_ideas.SHEET_URL})
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
            )
            generate_site.main()
            generate_rss.main()
            sheet_marked = None
            row = payload.get("row")
            if row:
                importlib.reload(sheet_ideas)
                post_url = sheet_ideas.post_url(post["id"], request_origin(self, payload))
                sheet_marked = sheet_ideas.mark_imported(int(row), post_url)
                print("sheet_marked", sheet_marked)
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
                "url": f"/#{post['id']}",
                "images": post.get("image_files") or [],
                "cards_error": post.get("cards_error"),
                "sheet_marked": bool(sheet_marked and sheet_marked.get("ok")),
                "sheet_error": None
                if sheet_marked and sheet_marked.get("ok")
                else (sheet_marked or {}).get("error")
                if row
                else "Нет номера строки таблицы",
            },
        )

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    reload_builders()
    generate_site.main()
    generate_rss.main()
    server = ThreadingHTTPServer(("127.0.0.1", 3000), Handler)
    print("http://127.0.0.1:3000/")
    server.serve_forever()


if __name__ == "__main__":
    main()
