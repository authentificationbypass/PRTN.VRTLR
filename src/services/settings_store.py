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

        sender_addresses = raw.get("sender_addresses", [])
        if not isinstance(sender_addresses, list):
            sender_addresses = []

        last_sender = str(raw.get("last_sender", "")).strip()
        if last_sender and last_sender not in sender_addresses:
            last_sender = ""

        return {
            "sender_addresses": [str(item).strip() for item in sender_addresses if str(item).strip()],
            "last_sender": last_sender,
        }

    def save(self, settings: dict[str, Any]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        sender_addresses = settings.get("sender_addresses", [])
        if not isinstance(sender_addresses, list):
            sender_addresses = []

        normalized_addresses = [str(item).strip() for item in sender_addresses if str(item).strip()]
        deduplicated = []
        seen: set[str] = set()
        for item in normalized_addresses:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(item)

        last_sender = str(settings.get("last_sender", "")).strip()
        if last_sender and last_sender.lower() not in {item.lower() for item in deduplicated}:
            last_sender = ""

        payload = {
            "sender_addresses": deduplicated,
            "last_sender": last_sender,
        }
        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
