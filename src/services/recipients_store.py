from __future__ import annotations

import json
import re
from pathlib import Path

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RecipientsStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path

    def _backup_file(self, raw_text: str | None = None) -> None:
        if not self._file_path.exists():
            return
        backup_path = self._file_path.with_name(f"{self._file_path.name}.bak")
        content = raw_text if raw_text is not None else self._file_path.read_text(encoding="utf-8")
        backup_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _normalize_group_name(value: str) -> str:
        return str(value or "Standard").strip() or "Standard"

    @staticmethod
    def _normalize_recipient(item: dict[str, object]) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        email = str(item.get("email", "")).strip()
        if not email:
            return None
        return {
            "name": str(item.get("name", "")).strip(),
            "email": email,
        }

    def load(self) -> list[dict[str, str]]:
        groups = self.load_groups()
        recipients: list[dict[str, str]] = []
        for group in groups:
            for item in group.get("recipients", []):
                if isinstance(item, dict):
                    recipient = self._normalize_recipient(item)
                    if recipient is not None:
                        recipients.append(recipient)
        return recipients

    def load_group(self, group_name: str) -> list[dict[str, str]]:
        target_name = self._normalize_group_name(group_name).lower()
        for group in self.load_groups():
            if self._normalize_group_name(group.get("name", "Standard")).lower() == target_name:
                recipients = group.get("recipients", [])
                return [
                    item for item in (
                        self._normalize_recipient(item) for item in recipients if isinstance(item, dict)
                    ) if item is not None
                ]
        return []

    def load_groups(self) -> list[dict[str, list[dict[str, str]]]]:
        if not self._file_path.exists():
            return [{"name": "Standard", "recipients": []}]

        try:
            with self._file_path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
        except (json.JSONDecodeError, OSError):
            try:
                self._backup_file()
            except OSError:
                pass
            return [{"name": "Standard", "recipients": []}]

        if isinstance(raw, dict):
            raw = raw.get("groups", [])

        if not isinstance(raw, list):
            return [{"name": "Standard", "recipients": []}]

        groups: list[dict[str, list[dict[str, str]]]] = []
        legacy: list[dict[str, str]] = []

        for entry in raw:
            if not isinstance(entry, dict):
                continue

            if "recipients" in entry:
                recipients = entry.get("recipients", [])
                if not isinstance(recipients, list):
                    continue
                clean_group: list[dict[str, str]] = []
                for item in recipients:
                    normalized = self._normalize_recipient(item)
                    if normalized is not None:
                        clean_group.append(normalized)
                group_name = self._normalize_group_name(entry.get("name", "Standard"))
                groups.append({"name": group_name, "recipients": clean_group})
            else:
                normalized = self._normalize_recipient(entry)
                if normalized is not None:
                    legacy.append(normalized)

        if groups:
            seen: set[str] = set()
            deduplicated: list[dict[str, list[dict[str, str]]]] = []
            for group in groups:
                name = self._normalize_group_name(group.get("name", "Standard"))
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                deduplicated.append({"name": name, "recipients": group.get("recipients", [])})
            return deduplicated or [{"name": "Standard", "recipients": []}]

        if legacy:
            return [{"name": "Standard", "recipients": legacy}]

        return [{"name": "Standard", "recipients": []}]

    def save(self, recipients: list[dict[str, str]]) -> None:
        self.save_groups([{"name": "Standard", "recipients": recipients}])

    def save_groups(self, groups: list[dict[str, list[dict[str, str]]]]) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

        normalized_groups: list[dict[str, list[dict[str, str]]]] = []
        seen: set[str] = set()

        for group in groups:
            if not isinstance(group, dict):
                continue
            name = self._normalize_group_name(group.get("name", "Standard"))
            if name.lower() in seen:
                continue
            seen.add(name.lower())

            recipients = group.get("recipients", [])
            if not isinstance(recipients, list):
                recipients = []

            clean_recipients: list[dict[str, str]] = []
            for item in recipients:
                if not isinstance(item, dict):
                    continue
                normalized = self._normalize_recipient(item)
                if normalized is not None:
                    clean_recipients.append(normalized)

            normalized_groups.append({"name": name, "recipients": clean_recipients})

        if not normalized_groups:
            normalized_groups = [{"name": "Standard", "recipients": []}]

        temp_path = self._file_path.with_suffix(f"{self._file_path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(normalized_groups, file, indent=2, ensure_ascii=False)
        temp_path.replace(self._file_path)

    @staticmethod
    def validate(recipients: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
        errors: list[str] = []
        cleaned: list[dict[str, str]] = []
        seen: set[str] = set()

        for index, recipient in enumerate(recipients, start=1):
            name = str(recipient.get("name", "")).strip()
            email = str(recipient.get("email", "")).strip().lower()

            if not email:
                errors.append(f"Zeile {index}: E-Mail darf nicht leer sein.")
                continue

            if not EMAIL_PATTERN.match(email):
                errors.append(f"Zeile {index}: Ungueltige E-Mail-Adresse ({email}).")
                continue

            if email in seen:
                errors.append(f"Zeile {index}: Duplikat ({email}).")
                continue

            seen.add(email)
            cleaned.append({"name": name, "email": email})

        return errors, cleaned
