import os
import sys
import types
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.settings import Settings
from app.supabase_client import create_supabase_client


class SupabaseClientTests(unittest.TestCase):
    def test_missing_credentials_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "SUPABASE_URL"):
            create_supabase_client(Settings(_env_file=None))

    def test_client_uses_server_credentials(self):
        calls = []

        def fake_create_client(url, key):
            calls.append((url, key))
            return "fake-client"

        fake_module = types.SimpleNamespace(create_client=fake_create_client)
        settings = Settings(
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="server-secret",
        )
        with patch.dict(sys.modules, {"supabase": fake_module}):
            client = create_supabase_client(settings)

        self.assertEqual(client, "fake-client")
        self.assertEqual(calls, [("https://example.supabase.co", "server-secret")])

    def test_environment_names_are_loaded(self):
        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "server-secret",
            },
            clear=False,
        ):
            settings = Settings()

        self.assertEqual(settings.supabase_url, "https://example.supabase.co")
        self.assertEqual(settings.supabase_service_role_key, "server-secret")

    def test_settings_can_load_a_backend_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "SUPABASE_URL=https://file.supabase.co\n"
                "SUPABASE_SERVICE_ROLE_KEY=file-secret\n",
                encoding="utf-8",
            )
            settings = Settings(_env_file=env_path)

        self.assertEqual(settings.supabase_url, "https://file.supabase.co")
        self.assertEqual(settings.supabase_service_role_key, "file-secret")


if __name__ == "__main__":
    unittest.main()
