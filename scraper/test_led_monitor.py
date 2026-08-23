import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from led_monitor import (
    calculate_final_price,
    extract_landsmaps_location,
    extract_sale_method,
    extract_standard_deposit,
    is_mortgage_attached,
    is_no_bid_status,
    landsmaps_name_candidates,
    load_config,
    normalize_landsmaps_name,
    normalize_text,
    parse_detail_pairs_from_body,
    result_key,
    save_to_csv,
    select_base_price,
)


class LedMonitorTests(unittest.TestCase):
    def test_normalize_text_collapses_whitespace(self):
        self.assertEqual(normalize_text("  นนทบุรี\n  เมือง  "), "นนทบุรี เมือง")

    def test_detail_parser_preserves_line_boundaries(self):
        result = parse_detail_pairs_from_body("เลขคดี : A/1\nจังหวัด: นนทบุรี")
        self.assertEqual(result["เลขคดี"], "A/1")
        self.assertEqual(result["จังหวัด"], "นนทบุรี")

    def test_detail_parser_reads_label_value_lines(self):
        result = parse_detail_pairs_from_body("โจทก์\nนายสมบัติ\nเนื้อที่\n10 ไร่ 0 งาน")
        self.assertEqual(result["โจทก์"], "นายสมบัติ")
        self.assertEqual(result["เนื้อที่_detail"], "10 ไร่ 0 งาน")

    def test_detail_parser_keeps_deed_label_text(self):
        result = parse_detail_pairs_from_body("ที่ดิน\nโฉนดเลขที่ 43339")
        self.assertEqual(result["โฉนดที่ดิน"], "43339")

    def test_result_key_deduplicates_same_listing(self):
        first = {"หมายเลขคดี": "A/1", "ล็อต": "1", "ลำดับ": "2", "จังหวัด": "นนทบุรี"}
        second = {"หมายเลขคดี": " A/1 ", "ล็อต": "1", "ลำดับ": "2", "จังหวัด": "นนทบุรี"}
        self.assertEqual(result_key(first), result_key(second))

    def test_landsmaps_name_normalizes_codes_and_suffixes(self):
        self.assertEqual(normalize_landsmaps_name("05-ไทรน้อย(บางบัวทอง)"), "ไทรน้อย")
        self.assertEqual(landsmaps_name_candidates("ไทรน้อย(บางบัวทอง)"), ["ไทรน้อย", "บางบัวทอง"])

    def test_extract_landsmaps_location_from_result_text(self):
        text = "ค่าพิกัดแปลง\n13.89266500,100.42568942\nข้อมูลการเดินทาง"
        self.assertEqual(
            extract_landsmaps_location(text), "13.89266500,100.42568942"
        )

    def test_extract_landsmaps_location_requires_coordinates(self):
        with self.assertRaises(LookupError):
            extract_landsmaps_location("ข้อมูลแปลงที่ดิน แต่ไม่มีพิกัด")

    def test_empty_rai_value_is_valid_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                '{"search":{"province":"นนทบุรี","rai_value":""}}',
                encoding="utf-8",
            )
            self.assertEqual(load_config(str(path))["search"]["rai_value"], "")

    def test_default_config_is_relative_to_scraper_module(self):
        config = load_config()
        self.assertEqual(config["search"]["province"], "นนทบุรี")

    def test_price_priority_skips_missing_amounts(self):
        text = (
            "ราคาที่กำหนดโดยคณะกรรมการกำหนดราคาทรัพย์ จำนวน ไม่มี บาท\n"
            "ราคาประเมินของเจ้าพนักงานบังคับคดี จำนวน 1,273,600.00 บาท"
        )
        self.assertEqual(select_base_price(text), Decimal("1273600.00"))

    def test_final_price_discount_by_no_bid_count(self):
        base = Decimal("100000")
        self.assertEqual(calculate_final_price(base, "-", 0), base)
        self.assertEqual(calculate_final_price(Decimal("2192500.00"), "-", 5), Decimal("1534750.00"))
        self.assertEqual(calculate_final_price(base, "งดขายไม่มีผู้สู้ราคา", 1), Decimal("90000.00"))
        self.assertEqual(calculate_final_price(base, "งดขายไม่มีผู้สู้ราคา", 2), Decimal("80000.00"))
        self.assertEqual(calculate_final_price(base, "งดขายไม่มีผู้สู้ราคา", 3), Decimal("70000.00"))

    def test_no_bid_status_matches_site_suffixes(self):
        self.assertTrue(is_no_bid_status("งดขายไม่มีผู้สู้ราคา "))
        self.assertTrue(is_no_bid_status("งดขายไม่มีผู้สู้ราคา (ไม่มีผู้ซื้อ)"))
        self.assertFalse(is_no_bid_status("-"))

    def test_mortgage_attached_listing_is_filtered(self):
        self.assertTrue(is_mortgage_attached({"_sale_method": "การจำนองติดไป"}))
        self.assertFalse(is_mortgage_attached({"_sale_method": "ปลอดการจำนอง"}))

    def test_sale_method_extracts_inline_value(self):
        text = "จะทำการขายโดย การจำนองติดไป ติดจำนองของธนาคาร ราคาประเมินของผู้เชี่ยวชาญ"
        self.assertIn("การจำนองติดไป", extract_sale_method(text))

    def test_standard_deposit_ignores_special_case_amount(self):
        text = "ผู้ประสงค์จะเข้าเสนอราคา ต้องวางหลักประกันเป็นจำนวน 150,000.00 บาท เว้นแต่ต้องวาง 110,000.00 บาท"
        self.assertEqual(extract_standard_deposit(text), Decimal("150000.00"))

    def test_save_to_csv_writes_utf8_bom_and_headers(self):
        row = {
            "ล็อต": "1",
            "หมายเลขคดี": "A/1",
            "จังหวัด": "นนทบุรี",
            "จังหวัด_detail": "นนทบุรี",
            "ที่อยู่จดหมายอิเล็กทรอนิกส์": "hidden@example.com",
            "ติดต่อผู้ดูแลเว็บไซต์": "support@example.com",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            save_to_csv([row], str(path))
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                saved = list(csv.DictReader(file))
            self.assertEqual(saved[0]["จังหวัด"], "นนทบุรี")
            self.assertNotIn("จังหวัด_detail", saved[0])
            self.assertNotIn("ที่อยู่จดหมายอิเล็กทรอนิกส์", saved[0])
            self.assertNotIn("ติดต่อผู้ดูแลเว็บไซต์", saved[0])


if __name__ == "__main__":
    unittest.main()
