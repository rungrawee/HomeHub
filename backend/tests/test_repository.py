import unittest

from app.repository import RepositoryError, SupabaseRepository


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


if __name__ == "__main__":
    unittest.main()
