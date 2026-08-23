import unittest

from app.data_quality import build_data_quality_report


class FakeRepository:
    def __init__(self, assets, auctions):
        self.assets = assets
        self.auctions = auctions

    def fetch_all(self, table, columns):
        del columns
        return self.assets if table == "assets" else self.auctions


class DataQualityTests(unittest.TestCase):
    def test_healthy_report(self):
        repository = FakeRepository(
            [
                {
                    "id": "asset-1",
                    "source_key": "case|1|81662",
                    "location": "13.8,100.4",
                    "province": "นนทบุรี",
                    "amphur": "บางบัวทอง",
                    "price_final": "1534750.00",
                    "deposit_amount": "150000.00",
                }
            ],
            [{"id": "auction-1", "asset_id": "asset-1"}],
        )

        report = build_data_quality_report(repository)

        self.assertTrue(report.is_healthy)
        self.assertEqual(report.assets, 1)
        self.assertEqual(report.auctions, 1)
        self.assertEqual(report.missing_fields["location"], 0)

    def test_reports_duplicates_missing_fields_and_orphans(self):
        repository = FakeRepository(
            [
                {
                    "id": "asset-1",
                    "source_key": "duplicate",
                    "location": "",
                    "province": "นนทบุรี",
                    "amphur": None,
                    "price_final": "100.00",
                    "deposit_amount": "150000.00",
                },
                {
                    "id": "asset-2",
                    "source_key": "duplicate",
                    "location": "13.8,100.4",
                    "province": "นนทบุรี",
                    "amphur": "บางบัวทอง",
                    "price_final": "200.00",
                    "deposit_amount": "150000.00",
                },
            ],
            [{"id": "auction-1", "asset_id": "missing-asset"}],
        )

        report = build_data_quality_report(repository)

        self.assertFalse(report.is_healthy)
        self.assertEqual(report.duplicate_source_keys, 1)
        self.assertEqual(report.orphan_auctions, 1)
        self.assertEqual(report.missing_fields["location"], 1)
        self.assertEqual(report.missing_fields["amphur"], 1)


if __name__ == "__main__":
    unittest.main()
