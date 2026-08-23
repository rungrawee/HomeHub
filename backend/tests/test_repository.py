import unittest

from app.repository import RepositoryError, SupabaseRepository
from app.mapping import AuctionRecord


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def upsert(self, values, on_conflict):
        self.calls.append(("upsert", values, on_conflict))
        return self

    def select(self, columns):
        self.calls.append(("select", columns))
        return self

    def range(self, start, end):
        self.calls.append(("range", start, end))
        return self

    def execute(self):
        return self.response


class FakeClient:
    def __init__(self, response):
        self.query = FakeQuery(response)
        self.table_name = None

    def table(self, name):
        self.table_name = name
        return self.query


class RepositoryTests(unittest.TestCase):
    def test_upsert_asset_uses_source_key_conflict(self):
        client = FakeClient(FakeResponse([{"id": "asset-1"}]))
        repository = SupabaseRepository(client)
        asset_id = repository.upsert_asset({"source_key": "CASE|1|81662"})

        self.assertEqual(asset_id, "asset-1")
        self.assertEqual(client.table_name, "assets")
        self.assertEqual(client.query.calls[0][2], "source_key")

    def test_missing_source_key_is_rejected(self):
        with self.assertRaisesRegex(RepositoryError, "source_key"):
            SupabaseRepository(FakeClient(FakeResponse([]))).upsert_asset({})

    def test_empty_supabase_response_is_rejected(self):
        client = FakeClient(FakeResponse([]))
        with self.assertRaises(RepositoryError):
            SupabaseRepository(client).upsert_asset({"source_key": "CASE|1|81662"})

    def test_upsert_auctions_uses_composite_conflict_key(self):
        client = FakeClient(FakeResponse([]))
        repository = SupabaseRepository(client)
        count = repository.upsert_auctions(
            "asset-1",
            [AuctionRecord(1, "2026-04-23", "งดขายไม่มีผู้สู้ราคา")],
        )

        self.assertEqual(count, 1)
        self.assertEqual(client.table_name, "auctions")
        call = client.query.calls[-1]
        self.assertEqual(call[2], "asset_id,auction_round,auction_date")
        self.assertEqual(call[1][0]["asset_id"], "asset-1")

    def test_empty_auctions_do_not_call_supabase(self):
        client = FakeClient(FakeResponse([]))
        self.assertEqual(SupabaseRepository(client).upsert_auctions("asset-1", []), 0)
        self.assertEqual(client.query.calls, [])

    def test_fetch_all_selects_requested_page(self):
        client = FakeClient(FakeResponse([{"id": "asset-1"}]))

        rows = SupabaseRepository(client).fetch_all("assets", "id", page_size=2)

        self.assertEqual(rows, [{"id": "asset-1"}])
        self.assertEqual(client.table_name, "assets")
        self.assertIn(("select", "id"), client.query.calls)
        self.assertIn(("range", 0, 1), client.query.calls)


if __name__ == "__main__":
    unittest.main()
