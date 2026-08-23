import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class FakeRepository:
    def __init__(self):
        self.arguments = None

    def list_assets(self, **kwargs):
        self.arguments = kwargs
        return ([{"id": "asset-1", "deed_number": "81662"}], 21)


class AssetsApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.client = TestClient(create_app(self.repository))

    def test_lists_assets_with_filters_and_pagination(self):
        response = self.client.get(
            "/assets",
            params={
                "province": "นนทบุรี",
                "amphur": "บางบัวทอง",
                "min_price": "1000000",
                "auction_date_from": "2026-04-01",
                "page": 2,
                "page_size": 10,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["deed_number"], "81662")
        self.assertEqual(
            response.json()["pagination"],
            {"page": 2, "page_size": 10, "total": 21, "total_pages": 3},
        )
        self.assertEqual(self.repository.arguments["province"], "นนทบุรี")
        self.assertEqual(self.repository.arguments["min_price"], "1000000")
        self.assertEqual(
            self.repository.arguments["auction_date_from"], "2026-04-01"
        )

    def test_rejects_invalid_pagination_and_price(self):
        self.assertEqual(self.client.get("/assets?page=0").status_code, 422)
        self.assertEqual(self.client.get("/assets?page_size=101").status_code, 422)
        self.assertEqual(self.client.get("/assets?min_price=-1").status_code, 422)


if __name__ == "__main__":
    unittest.main()
