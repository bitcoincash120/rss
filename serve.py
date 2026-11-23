#!/usr/bin/env python3
"""Serve the feed locally and accept new posts from /new.html."""

from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from generate_post import create_post
from generate_rss import main as generate_rss
from generate_site import main as generate_site
from posts_md import ROOT


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/posts":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            post = create_post(
                payload.get("title") or "",
                payload.get("description") or "",
                payload.get("slides"),
                payload.get("date"),
            )
            generate_site()
            generate_rss()
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

    def log_message(self, format: str, *args) -> None:
        super().log_message(format, *args)


def main() -> None:
    generate_site()
    generate_rss()
    server = ThreadingHTTPServer(("127.0.0.1", 8770), Handler)
    print("http://127.0.0.1:8770/new.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
