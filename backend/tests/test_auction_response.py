import unittest
from datetime import date

from app.repository import prepare_asset_auctions


class AuctionResponseTests(unittest.TestCase):
    def test_keeps_only_public_statuses_and_finds_next_date(self):
        asset = {
            "auctions": [
                {
                    "auction_round": 1,
                    "auction_date": "2026-08-01",
                    "status": "งดขายไม่มีผู้สู้ราคา",
                },
                {
                    "auction_round": 2,
                    "auction_date": "2026-09-10",
                    "status": "-",
                },
                {
                    "auction_round": 3,
                    "auction_date": "2026-10-01",
                    "status": "ขายได้",
                },
            ]
        }

        result = prepare_asset_auctions(asset, today=date(2026, 8, 23))

        self.assertEqual(len(result["auctions"]), 2)
        self.assertEqual(
            {auction["status"] for auction in result["auctions"]},
            {"-", "งดขายไม่มีผู้สู้ราคา"},
        )
        self.assertEqual(result["next_auction_date"], "2026-09-10")

    def test_returns_none_when_no_upcoming_auction_exists(self):
        result = prepare_asset_auctions(
            {
                "auctions": [
                    {
                        "auction_round": 1,
                        "auction_date": "2026-01-01",
                        "status": "-",
                    }
                ]
            },
            today=date(2026, 8, 23),
        )

        self.assertIsNone(result["next_auction_date"])


if __name__ == "__main__":
    unittest.main()
