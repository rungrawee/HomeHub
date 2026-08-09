import unittest
from pathlib import Path

from app.csv_loader import read_csv_rows
from app.mapping import map_csv_row


class RealCsvTests(unittest.TestCase):
    def test_current_scraper_csv_maps_without_losing_auction_history(self):
        csv_path = Path(__file__).parents[2] / "scraper" / "result.csv"
        if not csv_path.is_file():
            self.skipTest("scraper/result.csv is a local runtime artifact")

        rows = read_csv_rows(csv_path)
        mapped = [map_csv_row(row) for row in rows]
        source_keys = [item.values["source_key"] for item in mapped]
        auction_count = sum(len(item.auctions) for item in mapped)

        self.assertGreater(len(rows), 0)
        self.assertEqual(len(rows), len(mapped))
        self.assertTrue(all(source_keys))
        self.assertEqual(len(source_keys), len(set(source_keys)))
        self.assertGreater(auction_count, 0)


if __name__ == "__main__":
    unittest.main()
