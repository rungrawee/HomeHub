import csv
import tempfile
import unittest
from pathlib import Path

from app.importer import import_csv


class IdempotentFakeRepository:
    def __init__(self):
        self.assets = {}
        self.auctions = set()

    def upsert_asset(self, values):
        source_key = values["source_key"]
        self.assets[source_key] = values
        return f"asset:{source_key}"

    def sync_auctions(self, asset_id, auctions):
        self.auctions = {
            row for row in self.auctions if row[0] != asset_id
        }
        for auction in auctions:
            self.auctions.add(
                (
                    asset_id,
                    auction.auction_round,
                    auction.auction_date,
                    auction.status,
                )
            )
        return len(auctions)


class ImportFlowTests(unittest.TestCase):
    def test_importing_same_csv_twice_keeps_one_asset_and_one_auction(self):
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
                    "บางรักพัฒนา", "1,534,750.00", "150,000.00", "",
                    "1 23/04/2569 งดขายไม่มีผู้สู้ราคา",
                ])

            repository = IdempotentFakeRepository()
            first = import_csv(path, repository)
            second = import_csv(path, repository)

        self.assertEqual(first.rows_read, 1)
        self.assertEqual(second.rows_read, 1)
        self.assertEqual(len(repository.assets), 1)
        self.assertEqual(len(repository.auctions), 1)

    def test_latest_csv_replaces_changed_auction_history(self):
        headers = [
            "หมายเลขคดี", "ลำดับ", "โฉนดที่ดิน", "ประเภททรัพย์_detail",
            "จังหวัด_detail", "อำเภอ_detail", "ตำบล_detail", "ราคา_final",
            "deposit_amount", "Location", "detail_raw_text",
        ]
        base_values = [
            "CASE-1", "1", "131507", "ที่ดิน", "นนทบุรี", "บางบัวทอง",
            "บางรักพัฒนา", "1,534,750.00", "150,000.00", "13.9,100.2",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerow(base_values + ["1 23/07/2569 -"])

            repository = IdempotentFakeRepository()
            import_csv(path, repository)

            with path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerow(
                    base_values
                    + [
                        "1 23/07/2569 งดขายไม่มีผู้สู้ราคา\n"
                        "2 13/08/2569 -"
                    ]
                )
            import_csv(path, repository)

        statuses = {row[3] for row in repository.auctions}
        self.assertEqual(len(repository.auctions), 2)
        self.assertIn("งดขายไม่มีผู้สู้ราคา", statuses)
        self.assertNotIn(("asset:CASE-1|1|131507", 1, "2026-07-23", "-"), repository.auctions)


if __name__ == "__main__":
    unittest.main()
