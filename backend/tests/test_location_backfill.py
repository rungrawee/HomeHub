import tempfile
import unittest
from pathlib import Path

from app.location_backfill import backfill_locations, build_location_updates


class FakeRepository:
    def __init__(self):
        self.updates = []

    def update_asset_fields(self, source_key, values):
        self.updates.append((source_key, values))
        return source_key != "missing|2|999"


class LocationBackfillTests(unittest.TestCase):
    def test_skips_rows_without_complete_location_criteria(self):
        rows = [
            {
                "หมายเลขคดี": "case",
                "ลำดับ": "1",
                "โฉนดที่ดิน": "81662",
                "จังหวัด_detail": "นนทบุรี",
                "อำเภอ_detail": "บางบัวทอง",
                "ตำบล_detail": "บางรักพัฒนา",
                "Location": "13.8,100.4",
            },
            {
                "หมายเลขคดี": "case",
                "ลำดับ": "2",
                "โฉนดที่ดิน": "",
                "จังหวัด_detail": "",
                "อำเภอ_detail": "",
                "Location": "",
            },
        ]

        updates = list(build_location_updates(rows))

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0][0], "case|1|81662")
        self.assertEqual(updates[0][1]["location"], "13.8,100.4")

    def test_apply_updates_only_eligible_rows(self):
        csv_text = (
            "หมายเลขคดี,ลำดับ,โฉนดที่ดิน,จังหวัด_detail,อำเภอ_detail,ตำบล_detail,Location\n"
            "case,1,81662,นนทบุรี,บางบัวทอง,บางรักพัฒนา,\"13.8,100.4\"\n"
            "case,2,,,,,\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            path.write_text(csv_text, encoding="utf-8")
            repository = FakeRepository()

            summary = backfill_locations(path, repository, apply=True)

        self.assertEqual(summary.rows_read, 2)
        self.assertEqual(summary.eligible, 1)
        self.assertEqual(summary.updated, 1)
        self.assertEqual(summary.unmappable, 1)
        self.assertEqual(len(repository.updates), 1)


if __name__ == "__main__":
    unittest.main()
