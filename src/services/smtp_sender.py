from __future__ import annotations

import ipaddress
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


class SMTPServiceError(Exception):
    pass


@dataclass
class SendResult:
    recipient: str
    ok: bool
    error: str = ""


def validate_smtp_target(host: str, port: int) -> None:
    if not host or not isinstance(host, str):
        raise ValueError("Host ist erforderlich.")

    host_value = host.strip()
    if host_value.startswith("localhost"):
        return

    try:
        ip = ipaddress.ip_address(host_value)
    except ValueError as exc:
        raise ValueError("Nur lokale SMTP-Targets sind erlaubt: 127.0.0.1, ::1 oder localhost.") from exc

    if ip.is_loopback:
        return

    if port not in range(1, 65536):
        raise ValueError("Port außerhalb des gültigen Bereichs.")

    raise ValueError("Nur lokale SMTP-Targets sind erlaubt: 127.0.0.1, ::1 oder localhost.")


def send_batch(
    host: str,
    port: int,
    username: str,
    password: str,
    sender: str,
    recipients: list[str],
    subject: str,
    body: str,
    progress_cb=None,
) -> list[SendResult]:
    if not recipients:
        return []

    validate_smtp_target(host, port)

    results: list[SendResult] = []

    try:
        smtp = smtplib.SMTP(host=host, port=port, timeout=20)
        smtp.starttls()
        smtp.login(username, password)

        total = len(recipients)
        for idx, recipient in enumerate(recipients, start=1):
            message = EmailMessage()
            message["From"] = sender
            message["To"] = recipient
            message["Subject"] = subject
            message.set_content(body)

            try:
                smtp.send_message(message)
                results.append(SendResult(recipient=recipient, ok=True))
                if progress_cb:
                    progress_cb(idx, total, f"Gesendet an {recipient}")
            except smtplib.SMTPException as exc:
                results.append(SendResult(recipient=recipient, ok=False, error=str(exc)))
                if progress_cb:
                    progress_cb(idx, total, f"Fehler bei {recipient}: {exc}")

        smtp.quit()
        return results
    except ValueError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        raise SMTPServiceError("SMTP-Login fehlgeschlagen. Benutzername / Passwort / Bridge-Login prüfen.") from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise SMTPServiceError(f"Verbindung zur Proton Mail Bridge fehlgeschlagen: {exc}") from exc
