import unittest

from app.repository import SupabaseRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def select(self, field):
        self.calls.append(("select", field))
        return self

    def neq(self, field, value):
        self.calls.append(("neq", field, value))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def order(self, field):
        self.calls.append(("order", field))
        return self

    def range(self, start, end):
        self.calls.append(("range", start, end))
        return self

    def execute(self):
        return FakeResponse(self.data)


class FakeClient:
    def __init__(self, data):
        self.query = FakeQuery(data)

    def table(self, name):
        self.query.calls.append(("table", name))
        return self.query


class FilterOptionsRepositoryTests(unittest.TestCase):
    def test_returns_unique_non_empty_sorted_values(self):
        client = FakeClient(
            [
                {"amphur": "บางบัวทอง"},
                {"amphur": "ปากเกร็ด"},
                {"amphur": "บางบัวทอง"},
                {"amphur": ""},
            ]
        )

        values = SupabaseRepository(client).list_filter_values(
            "amphur", province="นนทบุรี"
        )

        self.assertEqual(values, ["บางบัวทอง", "ปากเกร็ด"])
        self.assertIn(("eq", "province", "นนทบุรี"), client.query.calls)
        self.assertIn(("neq", "asset_type", ""), client.query.calls)

    def test_rejects_unknown_database_field(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            SupabaseRepository(FakeClient([])).list_filter_values("raw_detail")


if __name__ == "__main__":
    unittest.main()
