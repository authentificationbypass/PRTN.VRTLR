from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "sender_addresses": [],
    "last_sender": "",
}


class SettingsStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            return DEFAULT_SETTINGS.copy()

        try:
            with self._file_path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
        except (json.JSONDecodeError, OSError):
            return DEFAULT_SETTINGS.copy()

        if not isinstance(raw, dict):
            return DEFAULT_SETTINGS.copy()

        return {
            "sender_addresses": [],
            "last_sender": "",
        }

    def save(self, settings: dict[str, Any]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sender_addresses": [],
            "last_sender": "",
        }
        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
