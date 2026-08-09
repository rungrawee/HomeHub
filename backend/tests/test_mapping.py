import unittest

from app.mapping import MappingError, extract_auctions, map_csv_row, parse_amount


class MappingTests(unittest.TestCase):
    def test_parse_amount_preserves_decimal_precision(self):
        self.assertEqual(parse_amount("1,534,750.00"), "1534750.00")
        self.assertEqual(parse_amount("ไม่มี"), "0.00")

    def test_invalid_amount_is_rejected(self):
        with self.assertRaises(MappingError):
            parse_amount("not-a-price")

    def test_source_key_changes_when_deed_changes(self):
        base = {
            "หมายเลขคดี": "CASE-1",
            "ลำดับ": "1",
            "โฉนดที่ดิน": "81662",
        }
        changed = {**base, "โฉนดที่ดิน": "131507"}
        first = map_csv_row({**base, "ราคา_final": "0", "deposit_amount": "0"})
        second = map_csv_row({**changed, "ราคา_final": "0", "deposit_amount": "0"})
        self.assertNotEqual(first.values["source_key"], second.values["source_key"])

    def test_extracts_thai_auction_dates_and_statuses(self):
        raw = (
            "1\t23/04/2569\tงดขายไม่มีผู้สู้ราคา\t\n"
            "2\t14/05/2569\tงดขายไม่มีผู้สู้ราคา\t\n"
            "6\t06/08/2569\t-\t\n"
        )
        auctions = extract_auctions(raw)
        self.assertEqual(len(auctions), 3)
        self.assertEqual(auctions[0].auction_date, "2026-04-23")
        self.assertEqual(auctions[2].status, "-")

    def test_maps_asset_and_keeps_no_bid_history(self):
        row = {
            "หมายเลขคดี": "ผบE.11389/2566",
            "ลำดับ": "100 - 1",
            "โฉนดที่ดิน": "131507",
            "ประเภททรัพย์_detail": "ที่ดินพร้อมสิ่งปลูกสร้าง",
            "จังหวัด_detail": "นนทบุรี",
            "อำเภอ_detail": "บางบัวทอง",
            "ตำบล_detail": "บางรักพัฒนา",
            "ราคา": "2,192,500.00",
            "ราคา_final": "1,534,750.00",
            "deposit_amount": "150,000.00",
            "detail_raw_text": (
                "1 23/04/2569 งดขายไม่มีผู้สู้ราคา\n"
                "2 14/05/2569 งดขายไม่มีผู้สู้ราคา\n"
                "3 04/06/2569 งดขายไม่มีผู้สู้ราคา\n"
                "4 25/06/2569 งดขายไม่มีผู้สู้ราคา\n"
                "5 16/07/2569 งดขายไม่มีผู้สู้ราคา\n"
                "6 06/08/2569 -"
            ),
        }
        mapped = map_csv_row(row)
        self.assertEqual(mapped.values["source_key"], "ผบE.11389/2566|100 - 1|131507")
        self.assertEqual(mapped.values["price_final"], "1534750.00")
        self.assertEqual(len(mapped.auctions), 6)


if __name__ == "__main__":
    unittest.main()
