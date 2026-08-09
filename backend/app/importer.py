from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .csv_loader import read_csv_rows
from .mapping import map_csv_row


@dataclass
class ImportSummary:
    rows_read: int = 0
    assets_upserted: int = 0
    auctions_upserted: int = 0


def import_csv(path: str | Path, repository: Any) -> ImportSummary:
    summary = ImportSummary()
    for row in read_csv_rows(path):
        mapped = map_csv_row(row)
        asset_id = repository.upsert_asset(mapped.values)
        summary.rows_read += 1
        summary.assets_upserted += 1
        summary.auctions_upserted += repository.upsert_auctions(
            asset_id, list(mapped.auctions)
        )
    return summary
