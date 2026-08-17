import json
import tempfile
import unittest
from pathlib import Path

from src.services.recipients_store import RecipientsStore
from src.services.settings_store import SettingsStore
from src.services.smtp_sender import validate_smtp_target


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
                        {"name": "Bert", "email": "bert@example.com"},
                    ],
                },
            ])

            self.assertEqual(
                store.load_group("Standard"),
                [{"name": "Anna", "email": "anna@example.com"}],
            )
            self.assertEqual(
                store.load_group("Projekt"),
                [{"name": "Bert", "email": "bert@example.com"}],
            )

    def test_settings_store_keeps_sender_data_out_of_persistent_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "settings.json"
            store = SettingsStore(path)

            store.save({
                "sender_addresses": ["user@example.com"],
                "last_sender": "user@example.com",
            })

            self.assertEqual(store.load(), {"sender_addresses": [], "last_sender": ""})

    def test_validate_smtp_target_rejects_non_local_hosts(self):
        with self.assertRaises(ValueError):
            validate_smtp_target("smtp.gmail.com", 587)


if __name__ == "__main__":
    unittest.main()
