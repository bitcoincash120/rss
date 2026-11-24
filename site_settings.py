"""Persistent site settings, including whether RSS should be generated."""

from __future__ import annotations

import json
from pathlib import Path

from posts_md import ROOT

SETTINGS_PATH = ROOT / "site_settings.json"
DEFAULTS = {"generate_rss": False}


def load_settings() -> dict:
    data = dict(DEFAULTS)
    if SETTINGS_PATH.is_file():
        try:
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            data["generate_rss"] = bool(loaded.get("generate_rss"))
    return data


def save_settings(payload: dict | None = None) -> dict:
    current = load_settings()
    incoming = payload if isinstance(payload, dict) else {}
    current["generate_rss"] = bool(incoming.get("generate_rss", current.get("generate_rss")))
    SETTINGS_PATH.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return current


def rss_enabled() -> bool:
    return bool(load_settings().get("generate_rss"))
