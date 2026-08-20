import json
import tempfile
import unittest
from pathlib import Path

from src.services.recipients_store import RecipientsStore
from src.services.settings_store import SettingsStore
from src.services.smtp_sender import SendResult, send_batch, validate_smtp_target


class RecipientsStoreGroupTests(unittest.TestCase):
    def test_load_legacy_flat_list_and_migrate_to_default_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipients.json"
            path.write_text(
                json.dumps([
                    {"name": "Anna", "email": "anna@example.com"},
                    {"name": "Bert", "email": "Hbert@example.com"},
                ]),
                encoding="utf-8",
            )

            store = RecipientsStore(path)

            self.assertEqual(
                store.load(),
                [
                    {"name": "Anna", "email": "anna@example.com"},
                    {"name": "Bert", "email": "Hbert@example.com"},
                ],
            )
            self.assertEqual(
                store.load_groups(),
                [
                    {
                        "name": "Standard",
                        "recipients": [
                            {"name": "Anna", "email": "anna@example.com"},
                            {"name": "Bert", "email": "Hbert@example.com"},
                        ],
                    }
                ],
            )

    def test_save_and_load_grouped_recipients(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipients.json"
            store = RecipientsStore(path)

            groups = [
                {
                    "name": "Verein",
                    "recipients": [
                        {"name": "Anna", "email": "anna@example.com"},
                        {"name": "Bert", "email": "Hbert@example.com"},
                    ],
                },
                {
                    "name": "Projekt",
                    "recipients": [
                        {"name": "Clara", "email": "clara@example.com"},
                    ],
                },
            ]

            store.save_groups(groups)

            self.assertEqual(store.load_groups(), groups)
            self.assertEqual(
                store.load(),
                [
                    {"name": "Anna", "email": "anna@example.com"},
                    {"name": "Bert", "email": "Hbert@example.com"},
                    {"name": "Clara", "email": "clara@example.com"},
                ],
            )

    def test_load_specific_group_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipients.json"
            store = RecipientsStore(path)

            store.save_groups([
                {
                    "name": "Standard",
                    "recipients": [
                        {"name": "Anna", "email": "anna@example.com"},
                    ],
                },
                {
                    "name": "Projekt",
                    "recipients": [
                        {"name": "Bert", "email": "Hbert@example.com"},
                    ],
                },
            ])

            self.assertEqual(
                store.load_group("Standard"),
                [{"name": "Anna", "email": "anna@example.com"}],
            )
            self.assertEqual(
                store.load_group("Projekt"),
                [{"name": "Bert", "email": "Hbert@example.com"}],
            )

    def test_settings_store_persists_sender_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            store = SettingsStore(path)

            store.save({
                "sender_addresses": ["user@example.com", "hilfe@example.com"],
                "last_sender": "hilfe@example.com",
            })

            self.assertEqual(store.load(), {
                "sender_addresses": ["user@example.com", "hilfe@example.com"],
                "last_sender": "hilfe@example.com",
            })

    def test_validate_smtp_target_rejects_non_local_hosts(self):
        with self.assertRaises(ValueError):
            validate_smtp_target("smtp.gmail.com", 587)

    def test_find_project_icon_path(self):
        from src.main import get_app_icon_path

        project_root = Path(__file__).resolve().parent.parent
        icon_path = get_app_icon_path(project_root)

        self.assertTrue(icon_path is not None)
        self.assertTrue(icon_path.exists())
        self.assertEqual(icon_path.name, "PRTN.MV.ico")

    def test_get_app_data_dir_is_portable(self):
        from src.main import get_app_data_dir

        project_root = Path(__file__).resolve().parent.parent
        data_dir = get_app_data_dir(project_root)

        self.assertTrue(data_dir.name == "data")
        self.assertTrue(str(data_dir).endswith("data") or str(data_dir).endswith("Proton Verteiler V3"))


class SmtpRetryTests(unittest.TestCase):
    def test_send_batch_retries_failed_recipients_and_reports_attempts(self):
        class FakeSMTP:
            def __init__(self, host, port, timeout):
                self.host = host
                self.port = port
                self.timeout = timeout
                self.sent = []

            def starttls(self):
                return None

            def login(self, username, password):
                self.username = username
                self.password = password

            def send_message(self, message):
                recipient = message["To"]
                if recipient == "first@example.com" and len(self.sent) == 0:
                    self.sent.append("failed")
                    raise RuntimeError("temporary send failure")
                if recipient == "second@example.com":
                    self.sent.append("failed")
                    raise RuntimeError("permanent failing recipient")
                self.sent.append("ok")

            def quit(self):
                return None

        class FakeSMTPFactory:
            instance = None

            @staticmethod
            def create(*args, **kwargs):
                FakeSMTPFactory.instance = FakeSMTP(*args, **kwargs)
                return FakeSMTPFactory.instance

        original_factory = __import__("src.services.smtp_sender", fromlist=["smtplib"]).smtplib.SMTP
        import src.services.smtp_sender as smtp_sender_module
        smtp_sender_module.smtplib.SMTP = FakeSMTPFactory.create
        try:
            results = send_batch(
                host="127.0.0.1",
                port=1025,
                username="bridge-user",
                password="bridge-pass",
                sender="sender@example.com",
                recipients=["first@example.com", "second@example.com"],
                subject="Test",
                body="Hallo",
                max_retries=1,
            )
        finally:
            smtp_sender_module.smtplib.SMTP = original_factory

        self.assertEqual(len(results), 2)
        first = next(result for result in results if result.recipient == "first@example.com")
        second = next(result for result in results if result.recipient == "second@example.com")
        self.assertTrue(first.ok)
        self.assertEqual(first.attempts, 2)
        self.assertFalse(second.ok)
        self.assertEqual(second.attempts, 2)


if __name__ == "__main__":
    unittest.main()
