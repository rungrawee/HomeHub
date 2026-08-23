import unittest

from app.readiness import check_backend_readiness
from app.settings import Settings


class FakeQuery:
    def select(self, columns):
        self.columns = columns
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        return object()


class FakeClient:
    def table(self, name):
        self.table_name = name
        return FakeQuery()


class FailingClient(FakeClient):
    def table(self, name):
        raise RuntimeError("do not expose this detail")


class ReadinessTests(unittest.TestCase):
    def settings(self, **overrides):
        values = {
            "supabase_url": "https://example.supabase.co",
            "supabase_service_role_key": "secret",
            "cors_origins": "http://localhost:5173",
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_ready_when_configuration_and_connection_are_valid(self):
        report = check_backend_readiness(self.settings(), FakeClient())

        self.assertTrue(report.ready)
        self.assertTrue(report.supabase_reachable)
        self.assertIsNone(report.error)

    def test_rejects_wildcard_cors(self):
        report = check_backend_readiness(
            self.settings(cors_origins="*"), FakeClient()
        )

        self.assertFalse(report.ready)
        self.assertFalse(report.cors_valid)

    def test_reports_missing_credentials_without_exposing_values(self):
        report = check_backend_readiness(
            self.settings(supabase_service_role_key=""), None
        )

        self.assertFalse(report.ready)
        self.assertFalse(report.credentials_configured)
        self.assertNotIn("secret", report.error or "")

    def test_hides_connection_error_detail(self):
        report = check_backend_readiness(self.settings(), FailingClient())

        self.assertFalse(report.ready)
        self.assertEqual(report.error, "Supabase connection failed")
        self.assertNotIn("expose", report.error)


if __name__ == "__main__":
    unittest.main()
