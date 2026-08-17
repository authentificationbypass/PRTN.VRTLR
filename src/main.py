from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from src.services.recipients_store import RecipientsStore
from src.services.settings_store import SettingsStore
from src.ui.main_window import MainWindow


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"

    settings_store = SettingsStore(data_dir / "settings.json")
    recipients_store = RecipientsStore(data_dir / "recipients.json")
    style_path = Path(__file__).resolve().parent / "ui" / "style.qss"

    app = QApplication(sys.argv)
    app.setApplicationName("Proton Verteiler V3")
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow(
        settings_store=settings_store,
        recipients_store=recipients_store,
        style_path=style_path,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
