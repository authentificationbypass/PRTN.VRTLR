from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.services.recipients_store import RecipientsStore
from src.services.settings_store import SettingsStore
from src.ui.main_window import MainWindow


def get_app_icon_path(project_root: Path | None = None) -> Path | None:
    base_dir = project_root or Path(__file__).resolve().parent.parent
    candidates = [
        base_dir / "ico" / "PRTN.MV.ico",
        Path(sys.executable).resolve().parent / "PRTN.MV.ico",
        Path(sys.executable).resolve().parent / "ico" / "PRTN.MV.ico",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def get_app_data_dir(project_root: Path | None = None) -> Path:
    base_dir = project_root or Path(__file__).resolve().parent.parent
    exe_dir = Path(sys.executable).resolve().parent

    if exe_dir.name and exe_dir.exists() and exe_dir != base_dir:
        return exe_dir / "data"
    return base_dir / "data"


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = get_app_data_dir(project_root)

    settings_store = SettingsStore(data_dir / "settings.json")
    recipients_store = RecipientsStore(data_dir / "recipients.json")
    style_path = Path(__file__).resolve().parent / "ui" / "style.qss"
    icon_path = get_app_icon_path(project_root)

    app = QApplication(sys.argv)
    app.setApplicationName("Proton Verteiler V3")
    app.setFont(QFont("Segoe UI", 10))

    app_icon = QIcon(str(icon_path)) if icon_path is not None else QIcon()
    app.setWindowIcon(app_icon)

    window = MainWindow(
        settings_store=settings_store,
        recipients_store=recipients_store,
        style_path=style_path,
    )
    window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
