import unittest

from fastapi.testclient import TestClient

from app.main import create_app


class FakeRepository:
    def __init__(self):
        self.calls = []

    def list_filter_values(self, field, **filters):
        self.calls.append((field, filters))
        return {
            "province": ["นนทบุรี"],
            "amphur": ["บางบัวทอง"],
            "tambon": ["บางรักพัฒนา"],
        }[field]


class FilterOptionsApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = FakeRepository()
        self.client = TestClient(create_app(self.repository))

    def test_lists_provinces(self):
        response = self.client.get("/filters/provinces")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": ["นนทบุรี"]})
        self.assertEqual(self.repository.calls[-1], ("province", {}))

    def test_lists_amphurs_for_province(self):
        response = self.client.get(
            "/filters/amphurs", params={"province": "นนทบุรี"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": ["บางบัวทอง"]})
        self.assertEqual(
            self.repository.calls[-1],
            ("amphur", {"province": "นนทบุรี"}),
        )

    def test_lists_tambons_for_province_and_amphur(self):
        response = self.client.get(
            "/filters/tambons",
            params={"province": "นนทบุรี", "amphur": "บางบัวทอง"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"items": ["บางรักพัฒนา"]})

    def test_requires_parent_filters(self):
        self.assertEqual(self.client.get("/filters/amphurs").status_code, 422)
        self.assertEqual(
            self.client.get(
                "/filters/tambons", params={"province": "นนทบุรี"}
            ).status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()
