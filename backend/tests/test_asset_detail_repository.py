import unittest

from app.repository import SupabaseRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, data):
        self.response = FakeResponse(data)
        self.calls = []

    def select(self, columns):
        self.calls.append(("select", columns))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def execute(self):
        return self.response


class FakeClient:
    def __init__(self, data):
        self.query = FakeQuery(data)

    def table(self, name):
        self.query.calls.append(("table", name))
        return self.query


class AssetDetailRepositoryTests(unittest.TestCase):
    def test_returns_asset_and_sorts_auction_rounds(self):
        client = FakeClient(
            [
                {
                    "id": "asset-1",
                    "auctions": [
                        {
                            "auction_round": 2,
                            "auction_date": "2099-02-01",
                            "status": "-",
                        },
                        {
                            "auction_round": 1,
                            "auction_date": "2099-01-01",
                            "status": "งดขายไม่มีผู้สู้ราคา",
                        },
                    ],
                }
            ]
        )

        asset = SupabaseRepository(client).get_asset("asset-1")

        self.assertEqual(
            [row["auction_round"] for row in asset["auctions"]], [1, 2]
        )
        self.assertIn(("eq", "id", "asset-1"), client.query.calls)
        self.assertIn(("limit", 1), client.query.calls)
        select_call = next(call for call in client.query.calls if call[0] == "select")
        self.assertIn("image_url", select_call[1])

    def test_returns_none_when_not_found(self):
        self.assertIsNone(SupabaseRepository(FakeClient([])).get_asset("missing"))


if __name__ == "__main__":
    unittest.main()
