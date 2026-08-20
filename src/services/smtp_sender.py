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
    attempts: int = 1


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
    max_retries: int = 2,
) -> list[SendResult]:
    if not recipients:
        return []

    if max_retries < 0:
        raise ValueError("max_retries muss 0 oder größer sein.")

    validate_smtp_target(host, port)

    results: list[SendResult] = []
    smtp = None

    try:
        smtp = smtplib.SMTP(host=host, port=port, timeout=20)
        smtp.starttls()
        smtp.login(username, password)

        total = len(recipients)
        for idx, recipient in enumerate(recipients, start=1):
            attempts = 0
            last_error = ""
            for attempt in range(1, max_retries + 2):
                attempts = attempt
                message = EmailMessage()
                message["From"] = sender
                message["To"] = recipient
                message["Subject"] = subject
                message.set_content(body)

                try:
                    smtp.send_message(message)
                    results.append(SendResult(recipient=recipient, ok=True, attempts=attempts))
                    if progress_cb:
                        progress_cb(idx, total, f"Gesendet an {recipient} (Versuch {attempt})")
                    break
                except Exception as exc:  # noqa: BLE001 - retry logic needs to treat transport issues generically
                    last_error = str(exc)
                    if attempt > max_retries:
                        results.append(SendResult(recipient=recipient, ok=False, error=last_error, attempts=attempts))
                        if progress_cb:
                            progress_cb(idx, total, f"Fehler bei {recipient} nach {attempt} Versuch(en): {exc}")
                        break
                    if progress_cb:
                        progress_cb(idx, total, f"Versuch {attempt} für {recipient} fehlgeschlagen, wiederhole ...")

            if not any(item.recipient == recipient and item.ok for item in results):
                if not any(item.recipient == recipient for item in results):
                    results.append(SendResult(recipient=recipient, ok=False, error=last_error or "Unbekannter Fehler", attempts=attempts))

        return results
    except ValueError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        raise SMTPServiceError("SMTP-Login fehlgeschlagen. Benutzername / Passwort / Bridge-Login prüfen.") from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise SMTPServiceError(f"Verbindung zur Proton Mail Bridge fehlgeschlagen: {exc}") from exc
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:  # noqa: BLE001 - connection shutdown should never break result reporting
                try:
                    smtp.close()
                except Exception:  # noqa: BLE001
                    pass
