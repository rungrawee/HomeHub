import csv
import tempfile
import unittest
from pathlib import Path

from app.importer import import_csv


class FakeRepository:
    def __init__(self):
        self.assets = []
        self.auctions = []

    def upsert_asset(self, values):
        self.assets.append(values)
        return f"asset-{len(self.assets)}"

    def upsert_auctions(self, asset_id, auctions):
        self.auctions.extend((asset_id, auction) for auction in auctions)
        return len(auctions)


class ImporterTests(unittest.TestCase):
    def test_imports_assets_before_auction_history(self):
        headers = [
            "หมายเลขคดี", "ลำดับ", "โฉนดที่ดิน", "ประเภททรัพย์_detail",
            "จังหวัด_detail", "อำเภอ_detail", "ตำบล_detail", "ราคา_final",
            "deposit_amount", "Location", "detail_raw_text",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerow([
                    "CASE-1", "1", "131507", "ที่ดิน", "นนทบุรี", "บางบัวทอง",
                    "บางรักพัฒนา", "1,534,750.00", "150,000.00", "13.9,100.2",
                    "1 23/04/2569 งดขายไม่มีผู้สู้ราคา",
                ])

            repository = FakeRepository()
            summary = import_csv(path, repository)

        self.assertEqual(summary.rows_read, 1)
        self.assertEqual(summary.assets_upserted, 1)
        self.assertEqual(summary.auctions_upserted, 1)
        self.assertEqual(repository.auctions[0][0], "asset-1")


if __name__ == "__main__":
    unittest.main()
