import unittest

from app.repository import SupabaseRepository


class FakeResponse:
    data = [{"id": "asset-1"}]
    count = 21


class FakeQuery:
    def __init__(self):
        self.calls = []

    def select(self, columns, count):
        self.calls.append(("select", columns, count))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def neq(self, field, value):
        self.calls.append(("neq", field, value))
        return self

    def ilike(self, field, value):
        self.calls.append(("ilike", field, value))
        return self

    def gte(self, field, value):
        self.calls.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.calls.append(("lte", field, value))
        return self

    def order(self, field, desc):
        self.calls.append(("order", field, desc))
        return self

    def range(self, start, end):
        self.calls.append(("range", start, end))
        return self

    def execute(self):
        return FakeResponse()


class FakeClient:
    def __init__(self):
        self.query = FakeQuery()

    def table(self, name):
        self.query.calls.append(("table", name))
        return self.query


class AssetsRepositoryTests(unittest.TestCase):
    def test_applies_filters_count_and_page_range(self):
        client = FakeClient()

        rows, total = SupabaseRepository(client).list_assets(
            page=2,
            page_size=10,
            province="นนทบุรี",
            deed_number="81662",
            min_price="1000000",
            max_price="3000000",
            auction_date_from="2026-04-01",
            auction_date_to="2026-08-31",
        )

        self.assertEqual(rows, [{"id": "asset-1"}])
        self.assertEqual(total, 21)
        self.assertIn(("neq", "asset_type", ""), client.query.calls)
        self.assertIn(("neq", "province", ""), client.query.calls)
        self.assertIn(("neq", "amphur", ""), client.query.calls)
        self.assertIn(("eq", "province", "นนทบุรี"), client.query.calls)
        self.assertIn(("ilike", "deed_number", "%81662%"), client.query.calls)
        self.assertIn(("gte", "price_final", "1000000"), client.query.calls)
        self.assertIn(
            ("gte", "auctions.auction_date", "2026-04-01"), client.query.calls
        )
        self.assertIn(("range", 10, 19), client.query.calls)
        select_call = next(call for call in client.query.calls if call[0] == "select")
        self.assertIn("auctions!inner", select_call[1])
        self.assertEqual(select_call[2], "exact")


if __name__ == "__main__":
    unittest.main()
