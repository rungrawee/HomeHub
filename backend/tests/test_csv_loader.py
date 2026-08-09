import csv
import tempfile
import unittest
from pathlib import Path

from app.csv_loader import CsvValidationError, read_csv_rows


HEADERS = [
    "หมายเลขคดี",
    "ลำดับ",
    "โฉนดที่ดิน",
    "ประเภททรัพย์_detail",
    "จังหวัด_detail",
    "อำเภอ_detail",
    "ตำบล_detail",
    "ราคา_final",
    "deposit_amount",
    "Location",
]


class CsvLoaderTests(unittest.TestCase):
    def write_csv(self, headers=HEADERS, rows=None):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "result.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows or [])
        self.addCleanup(directory.cleanup)
        return path

    def test_reads_utf8_bom_and_normalizes_values(self):
        path = self.write_csv(
            rows=[[" CASE-1 ", " 1 ", "81662", "ที่ดิน", "นนทบุรี", "บางบัวทอง", "บางรักพัฒนา", "1,000.00", "150,000.00", "13.9,100.2"]]
        )
        rows = read_csv_rows(path)
        self.assertEqual(rows[0]["หมายเลขคดี"], "CASE-1")
        self.assertEqual(rows[0]["ลำดับ"], "1")

    def test_rejects_missing_required_column(self):
        path = self.write_csv(headers=HEADERS[:-1])
        with self.assertRaisesRegex(CsvValidationError, "Location"):
            read_csv_rows(path)

    def test_rejects_row_without_case_or_sequence(self):
        path = self.write_csv(
            rows=[["", "", "81662", "ที่ดิน", "นนทบุรี", "บางบัวทอง", "บางรักพัฒนา", "0", "0", ""]]
        )
        with self.assertRaisesRegex(CsvValidationError, "row 2"):
            read_csv_rows(path)

    def test_missing_location_value_is_allowed(self):
        path = self.write_csv(
            rows=[["CASE-1", "1", "", "ที่ดิน", "นนทบุรี", "บางบัวทอง", "บางรักพัฒนา", "0", "0", ""]]
        )
        self.assertEqual(read_csv_rows(path)[0]["Location"], "")


if __name__ == "__main__":
    unittest.main()
