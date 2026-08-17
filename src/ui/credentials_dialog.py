from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


@dataclass
class SMTPCredentials:
    host: str
    port: int
    username: str
    password: str
    sender: str


class CredentialsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Proton Mail Bridge Zugang")
        self.setModal(True)
        self.resize(560, 340)

        self._host_input = QLineEdit("127.0.0.1")
        self._port_input = QSpinBox()
        self._port_input.setMinimum(1)
        self._port_input.setMaximum(65535)
        self._port_input.setValue(1025)

        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Mailbox-Adresse oder Proton Benutzername")

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Bridge-Passwort")

        self._sender_input = QLineEdit()
        self._sender_input.setPlaceholderText("Absenderadresse, z.B. deineadresse@proton.me")

        info = QLabel(
            "Für Proton Mail Bridge wird normalerweise ein lokaler SMTP-Host verwendet, z. B. 127.0.0.1:1025. Der Bridge muss lokal laufen und mit dem Proton-Konto verbunden sein."
        )
        info.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Host", self._host_input)
        form.addRow("Port", self._port_input)
        form.addRow("Benutzername", self._username_input)
        form.addRow("Passwort", self._password_input)
        form.addRow("Absender", self._sender_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def credentials(self) -> SMTPCredentials:
        return SMTPCredentials(
            host=self._host_input.text().strip() or "127.0.0.1",
            port=self._port_input.value(),
            username=self._username_input.text().strip(),
            password=self._password_input.text(),
            sender=self._sender_input.text().strip(),
        )
