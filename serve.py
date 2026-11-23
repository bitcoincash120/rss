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
        if self.path.rstrip("/") != "/api/posts":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            reload_builders()
            post = generate_post.create_post(
                payload.get("title") or "",
                payload.get("description") or "",
                payload.get("slides"),
                payload.get("date"),
            )
            generate_site.main()
            generate_rss.main()
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
    server = ThreadingHTTPServer(("127.0.0.1", 8770), Handler)
    print("http://127.0.0.1:8770/")
    server.serve_forever()


if __name__ == "__main__":
    main()
