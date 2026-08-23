import unittest
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import create_app


ASSET_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeRepository:
    def __init__(self, asset):
        self.asset = asset
        self.requested_id = None

    def get_asset(self, asset_id):
        self.requested_id = asset_id
        return self.asset


class AssetDetailApiTests(unittest.TestCase):
    def test_returns_asset_detail(self):
        repository = FakeRepository(
            {"id": str(ASSET_ID), "deed_number": "81662", "auctions": []}
        )
        response = TestClient(create_app(repository)).get(f"/assets/{ASSET_ID}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["deed_number"], "81662")
        self.assertEqual(repository.requested_id, str(ASSET_ID))

    def test_returns_404_when_asset_does_not_exist(self):
        response = TestClient(create_app(FakeRepository(None))).get(
            f"/assets/{ASSET_ID}"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Asset not found")

    def test_rejects_invalid_uuid(self):
        response = TestClient(create_app(FakeRepository(None))).get(
            "/assets/not-a-uuid"
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
