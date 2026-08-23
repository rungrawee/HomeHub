import unittest

from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import RepositoryError
from app.settings import Settings


class FakeRepository:
    def list_assets(self, **kwargs):
        del kwargs
        return [], 0


class FailingRepository:
    def list_assets(self, **kwargs):
        del kwargs
        raise RepositoryError("secret database detail")


class ApiSecurityTests(unittest.TestCase):
    def create_client(self, repository=None):
        settings = Settings(
            _env_file=None,
            cors_origins="https://frontend.example.com",
        )
        return TestClient(
            create_app(repository or FakeRepository(), settings),
            raise_server_exceptions=False,
        )

    def test_allows_only_configured_cors_origin(self):
        client = self.create_client()

        allowed = client.get(
            "/health", headers={"Origin": "https://frontend.example.com"}
        )
        blocked = client.get(
            "/health", headers={"Origin": "https://attacker.example.com"}
        )

        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "https://frontend.example.com",
        )
        self.assertIsNone(blocked.headers.get("access-control-allow-origin"))

    def test_adds_security_and_request_headers(self):
        response = self.create_client().get(
            "/health", headers={"X-Request-ID": "request-123"}
        )

        self.assertEqual(response.headers["x-request-id"], "request-123")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")

    def test_hides_repository_error_details(self):
        response = self.create_client(FailingRepository()).get("/assets")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json(), {"detail": "Data service temporarily unavailable"}
        )
        self.assertNotIn("secret", response.text)

    def test_rejects_reversed_ranges(self):
        client = self.create_client()

        price = client.get("/assets?min_price=200&max_price=100")
        dates = client.get(
            "/assets?auction_date_from=2026-08-01&auction_date_to=2026-04-01"
        )

        self.assertEqual(price.status_code, 422)
        self.assertEqual(dates.status_code, 422)


if __name__ == "__main__":
    unittest.main()
