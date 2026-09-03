from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.services.recipients_store import RecipientsStore
from src.services.settings_store import SettingsStore
from src.services.smtp_sender import SMTPServiceError, send_batch
from src.ui.credentials_dialog import CredentialsDialog


@dataclass
class RuntimeCredentials:
    host: str
    port: int
    username: str
    password: str
    sender: str

    def clear_sensitive_data(self) -> None:
        self.password = ""
        self.username = ""


class SendWorker(QObject):
    progress = Signal(int, int, str)
    completed = Signal(list)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        credentials: RuntimeCredentials,
        recipients: list[str],
        subject: str,
        body: str,
        max_retries: int = 2,
    ) -> None:
        super().__init__()
        self._credentials = credentials
        self._recipients = recipients
        self._subject = subject
        self._body = body
        self._max_retries = max_retries

    def run(self) -> None:
        try:
            results = send_batch(
                host=self._credentials.host,
                port=self._credentials.port,
                username=self._credentials.username,
                password=self._credentials.password,
                sender=self._credentials.sender,
                recipients=self._recipients,
                subject=self._subject,
                body=self._body,
                progress_cb=lambda i, t, m: self.progress.emit(i, t, m),
                max_retries=self._max_retries,
            )
            self.completed.emit(results)
        except SMTPServiceError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Unerwarteter Fehler: {exc}")
        finally:
            self._credentials.clear_sensitive_data()
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore, recipients_store: RecipientsStore, style_path: Path) -> None:
        super().__init__()
        self._settings_store = settings_store
        self._recipients_store = recipients_store
        self._settings = self._settings_store.load()

        self.setWindowTitle("Proton Verteiler V3")
        self.resize(1280, 860)

        if style_path.exists():
            self.setStyleSheet(style_path.read_text(encoding="utf-8"))

        self._sender_combo = QComboBox()
        self._sender_combo.setMinimumWidth(350)

        self._new_sender_input = QLineEdit()
        self._new_sender_input.setPlaceholderText("Neue Proton-Absenderadresse")

        add_sender_btn = QPushButton("Absender +")
        add_sender_btn.clicked.connect(self._add_sender)

        remove_sender_btn = QPushButton("Entfernen")
        remove_sender_btn.clicked.connect(self._remove_sender)

        self._group_combo = QComboBox()
        self._group_combo.setMinimumWidth(250)
        self._group_combo.currentIndexChanged.connect(self._load_group_recipients)

        self._new_group_input = QLineEdit()
        self._new_group_input.setPlaceholderText("Neue Gruppe")

        add_group_btn = QPushButton("Gruppe +")
        add_group_btn.clicked.connect(self._add_group)

        rename_group_btn = QPushButton("Umbenennen")
        rename_group_btn.clicked.connect(self._rename_group)

        delete_group_btn = QPushButton("Gruppe löschen")
        delete_group_btn.clicked.connect(self._delete_group)

        self._recipients_table = QTableWidget(0, 2)
        self._recipients_table.setHorizontalHeaderLabels(["Name", "E-Mail"])
        self._recipients_table.setColumnWidth(0, 260)
        self._recipients_table.setColumnWidth(1, 620)
        self._recipients_table.horizontalHeader().setStretchLastSection(True)
        self._recipients_table.verticalHeader().setVisible(False)
        self._recipients_table.setAlternatingRowColors(True)
        self._recipients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._recipients_table.setMinimumHeight(220)
        self._recipients_table.setRowCount(0)

        add_recipient_btn = QPushButton("Empfänger +")
        add_recipient_btn.clicked.connect(self._add_recipient_row)

        delete_recipient_btn = QPushButton("Auswahl löschen")
        delete_recipient_btn.clicked.connect(self._delete_selected_recipient_rows)

        self._subject_input = QLineEdit()
        self._subject_input.setPlaceholderText("Betreff")

        self._body_input = QTextEdit()
        self._body_input.setPlaceholderText("Nachrichtentext")

        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)

        self._send_btn = QPushButton("Senden")
        self._send_btn.setObjectName("PrimaryButton")
        self._send_btn.clicked.connect(self._handle_send)

        self._save_btn = QPushButton("Empfänger speichern")
        self._save_btn.clicked.connect(self._save_recipients_from_table)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setMaximumHeight(150)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Bereit")

        self._build_layout(
            add_sender_btn,
            remove_sender_btn,
            add_group_btn,
            rename_group_btn,
            delete_group_btn,
            add_recipient_btn,
            delete_recipient_btn,
        )
        self._load_senders()
        self._load_groups()

    def _build_layout(
        self,
        add_sender_btn: QPushButton,
        remove_sender_btn: QPushButton,
        add_group_btn: QPushButton,
        rename_group_btn: QPushButton,
        delete_group_btn: QPushButton,
        add_recipient_btn: QPushButton,
        delete_recipient_btn: QPushButton,
    ) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(12)

        title = QLabel("Proton Verteiler V3")
        title.setObjectName("Title")
        subtitle = QLabel("Nutzt Proton Mail Bridge als lokalen SMTP-Endpunkt für den Versand.")
        subtitle.setObjectName("Subtitle")

        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        sender_label = QLabel("Von")
        sender_label.setObjectName("Section")

        sender_row = QHBoxLayout()
        sender_row.addWidget(self._sender_combo, 3)
        sender_row.addWidget(self._new_sender_input, 2)
        sender_row.addWidget(add_sender_btn)
        sender_row.addWidget(remove_sender_btn)

        groups_label = QLabel("Gruppen")
        groups_label.setObjectName("Section")

        groups_row = QHBoxLayout()
        groups_row.addWidget(self._group_combo, 3)
        groups_row.addWidget(self._new_group_input, 2)
        groups_row.addWidget(add_group_btn)
        groups_row.addWidget(rename_group_btn)
        groups_row.addWidget(delete_group_btn)

        recipients_label = QLabel("An")
        recipients_label.setObjectName("Section")

        recipients_actions = QHBoxLayout()
        recipients_actions.addWidget(add_recipient_btn)
        recipients_actions.addWidget(delete_recipient_btn)
        recipients_actions.addStretch()
        recipients_actions.addWidget(self._save_btn)

        message_label = QLabel("Nachricht")
        message_label.setObjectName("Section")

        send_row = QHBoxLayout()
        send_row.addStretch()
        send_row.addWidget(self._send_btn)

        card_layout.addWidget(sender_label)
        card_layout.addLayout(sender_row)
        card_layout.addWidget(groups_label)
        card_layout.addLayout(groups_row)
        card_layout.addWidget(recipients_label)
        card_layout.addLayout(recipients_actions)
        card_layout.addWidget(self._recipients_table, 4)
        card_layout.addWidget(message_label)
        card_layout.addWidget(self._subject_input)
        card_layout.addWidget(self._body_input, 2)
        card_layout.addWidget(self._progress_bar)
        card_layout.addWidget(self._log_output)
        card_layout.addLayout(send_row)

        root_layout.addWidget(card)
        self.setCentralWidget(root)

    def _load_senders(self) -> None:
        senders = self._settings.get("sender_addresses", [])
        self._sender_combo.clear()
        if senders:
            self._sender_combo.addItems(senders)
        last_sender = self._settings.get("last_sender", "")
        if last_sender and last_sender in senders:
            self._sender_combo.setCurrentText(last_sender)

    def _save_senders(self) -> None:
        senders = [self._sender_combo.itemText(i) for i in range(self._sender_combo.count())]
        self._settings["sender_addresses"] = senders
        self._settings["last_sender"] = self._sender_combo.currentText().strip()
        self._settings_store.save(self._settings)

    def _add_sender(self) -> None:
        value = self._new_sender_input.text().strip().lower()
        if not value:
            return

        existing = [self._sender_combo.itemText(i).lower() for i in range(self._sender_combo.count())]
        if value in existing:
            QMessageBox.information(self, "Hinweis", "Absender existiert bereits.")
            return

        self._sender_combo.addItem(value)
        self._sender_combo.setCurrentText(value)
        self._new_sender_input.clear()
        self._save_senders()

    def _remove_sender(self) -> None:
        index = self._sender_combo.currentIndex()
        if index < 0:
            return
        self._sender_combo.removeItem(index)
        self._save_senders()

    @staticmethod
    def _normalize_group_name(value: str) -> str:
        return (value or "Standard").strip() or "Standard"

    def _selected_group_name(self) -> str:
        if self._group_combo.count() == 0:
            return "Standard"
        current_name = self._group_combo.currentData()
        if current_name:
            return str(current_name).strip() or "Standard"
        return self._normalize_group_name(self._group_combo.currentText())

    def _load_groups(self) -> None:
        groups = self._recipients_store.load_groups()

        current_name = self._selected_group_name()
        self._group_combo.blockSignals(True)
        self._group_combo.clear()

        for group in groups:
            name = self._normalize_group_name(group.get("name", "Standard"))
            count = len(group.get("recipients", []))
            self._group_combo.addItem(f"{name} ({count})", name)

        if self._group_combo.count() == 0:
            self._group_combo.addItem("Standard (0)", "Standard")

        target_index = self._group_combo.findData(current_name)
        if target_index >= 0:
            self._group_combo.setCurrentIndex(target_index)
        else:
            self._group_combo.setCurrentIndex(0)

        self._group_combo.blockSignals(False)
        self._load_group_recipients()

    def _load_group_recipients(self) -> None:
        groups = self._recipients_store.load_groups()
        selected_name = self._selected_group_name()
        selected_group = next(
            (group for group in groups if self._normalize_group_name(group.get("name", "Standard")).lower() == selected_name.lower()),
            None,
        )

        recipients = selected_group.get("recipients", []) if selected_group else []
        self._recipients_table.setRowCount(0)
        for item in recipients:
            self._add_recipient_row(item.get("name", ""), item.get("email", ""))

    def _add_group(self) -> None:
        name = self._normalize_group_name(self._new_group_input.text())
        if not name:
            return

        groups = self._recipients_store.load_groups()
        if any(self._normalize_group_name(group.get("name", "Standard")).lower() == name.lower() for group in groups):
            QMessageBox.information(self, "Gruppe", "Diese Gruppe existiert bereits.")
            return

        groups.append({"name": name, "recipients": []})
        self._recipients_store.save_groups(groups)
        self._new_group_input.clear()
        self._load_groups()
        index = self._group_combo.findData(name)
        if index >= 0:
            self._group_combo.setCurrentIndex(index)

    def _rename_group(self) -> None:
        current_name = self._selected_group_name()
        new_name, ok = QInputDialog.getText(self, "Gruppe umbenennen", "Neuer Gruppenname:", text=current_name)
        if not ok:
            return

        name = self._normalize_group_name(new_name)
        if not name:
            return

        groups = self._recipients_store.load_groups()
        if any(
            self._normalize_group_name(group.get("name", "Standard")).lower() == name.lower()
            and self._normalize_group_name(group.get("name", "Standard")).lower() != current_name.lower()
            for group in groups
        ):
            QMessageBox.information(self, "Gruppe", "Ein anderer Eintrag mit diesem Namen existiert bereits.")
            return

        for group in groups:
            if self._normalize_group_name(group.get("name", "Standard")).lower() == current_name.lower():
                group["name"] = name
                break

        self._recipients_store.save_groups(groups)
        self._load_groups()

    def _delete_group(self) -> None:
        current_name = self._selected_group_name()
        if self._group_combo.count() <= 1:
            QMessageBox.information(self, "Gruppe", "Mindestens eine Gruppe muss bestehen bleiben.")
            return

        confirm = QMessageBox.question(
            self,
            "Gruppe löschen",
            f"Gruppe \"{current_name}\" wirklich löschen?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        groups = self._recipients_store.load_groups()
        updated = [group for group in groups if self._normalize_group_name(group.get("name", "Standard")).lower() != current_name.lower()]
        self._recipients_store.save_groups(updated)
        self._load_groups()

    def _add_recipient_row(self, name: str = "", email: str = "") -> None:
        row = self._recipients_table.rowCount()
        self._recipients_table.insertRow(row)
        self._recipients_table.setItem(row, 0, QTableWidgetItem(name))
        self._recipients_table.setItem(row, 1, QTableWidgetItem(email))

    def _delete_selected_recipient_rows(self) -> None:
        selected_rows = sorted({index.row() for index in self._recipients_table.selectedIndexes()}, reverse=True)
        for row in selected_rows:
            self._recipients_table.removeRow(row)

    def _collect_recipients_from_table(self) -> list[dict[str, str]]:
        recipients: list[dict[str, str]] = []
        for row in range(self._recipients_table.rowCount()):
            name_item = self._recipients_table.item(row, 0)
            email_item = self._recipients_table.item(row, 1)
            recipients.append({
                "name": name_item.text().strip() if name_item else "",
                "email": email_item.text().strip() if email_item else "",
            })
        return recipients

    def _save_recipients_from_table(self) -> bool:
        raw = self._collect_recipients_from_table()
        errors, cleaned = self._recipients_store.validate(raw)
        if errors:
            QMessageBox.warning(self, "Empfängerliste", "\n".join(errors[:8]))
            return False

        groups = self._recipients_store.load_groups()
        selected_name = self._selected_group_name()
        for group in groups:
            if self._normalize_group_name(group.get("name", "Standard")).lower() == selected_name.lower():
                group["recipients"] = cleaned
                break
        else:
            groups.append({"name": selected_name, "recipients": cleaned})

        self._recipients_store.save_groups(groups)
        self._load_groups()
        self._status.showMessage(f"Empfänger gespeichert: {len(cleaned)}")
        return True

    def _handle_send(self) -> None:
        sender = self._sender_combo.currentText().strip()
        if not sender:
            QMessageBox.warning(self, "Versand", "Bitte eine Absenderadresse eingeben oder auswählen.")
            return

        if not self._save_recipients_from_table():
            return

        active_group_name = self._selected_group_name()
        recipients = self._recipients_store.load_group(active_group_name)
        recipient_emails = [item["email"] for item in recipients]
        if not recipient_emails:
            QMessageBox.warning(self, "Versand", f"Empfängerliste in Gruppe \"{active_group_name}\" ist leer.")
            return

        subject = self._subject_input.text().strip()
        body = self._body_input.toPlainText().strip()
        if not subject or not body:
            QMessageBox.warning(self, "Versand", "Bitte Betreff und Nachricht ausfüllen.")
            return

        confirm = QMessageBox.question(
            self,
            "Versand bestätigen",
            f"Jetzt {len(recipient_emails)} E-Mails versenden?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        dialog = CredentialsDialog(self)
        if dialog.exec() != CredentialsDialog.DialogCode.Accepted:
            return

        credentials = dialog.credentials()
        if not credentials.username or not credentials.password or not credentials.sender:
            QMessageBox.warning(self, "Mail-Service", "Benutzername, Passwort und Absender sind erforderlich.")
            return

        self._settings["last_sender"] = sender
        self._settings_store.save(self._settings)

        self._send_btn.setEnabled(False)
        self._progress_bar.setValue(0)
        self._progress_bar.setMaximum(len(recipient_emails))
        self._log_output.clear()
        self._status.showMessage("Versand gestartet")

        runtime = RuntimeCredentials(
            host=credentials.host,
            port=credentials.port,
            username=credentials.username,
            password=credentials.password,
            sender=credentials.sender,
        )

        thread = QThread(self)
        worker = SendWorker(runtime, recipient_emails, subject, body, max_retries=2)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.completed.connect(self._on_completed)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._send_btn.setEnabled(True))
        thread.finished.connect(lambda: self._status.showMessage("Bereit"))

        self._last_thread = thread
        self._last_worker = worker
        thread.start()

    def _on_progress(self, index: int, total: int, message: str) -> None:
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(index)
        self._log_output.append(f"[{index}/{total}] {message}")

    def _on_completed(self, results: list) -> None:
        success = sum(1 for item in results if item.ok)
        failed = sum(1 for item in results if not item.ok)
        self._log_output.append(f"Versand abgeschlossen: {success} erfolgreich, {failed} fehlgeschlagen.")
        if failed:
            details = "\n".join(
                f"{item.recipient}: {item.error or 'Fehler'} (Versuche: {item.attempts})"
                for item in results
                if not item.ok
            )
            QMessageBox.warning(self, "Versand beendet", f"Einige E-Mails konnten nicht versendet werden:\n{details[:1200]}")
        else:
            QMessageBox.information(self, "Versand beendet", f"Alle {success} E-Mails wurden erfolgreich versendet.")

    def _on_failed(self, message: str) -> None:
        self._log_output.append(f"Fehler: {message}")
        QMessageBox.critical(self, "Versand fehlgeschlagen", message)
