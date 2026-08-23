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
    assets_planned: int = 0
    auctions_planned: int = 0


def import_csv(
    path: str | Path,
    repository: Any | None,
    dry_run: bool = False,
    limit: int | None = None,
) -> ImportSummary:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than zero")

    rows = read_csv_rows(path)
    if limit is not None:
        rows = rows[:limit]

    summary = ImportSummary()
    for row in rows:
        mapped = map_csv_row(row)
        summary.rows_read += 1
        if dry_run:
            summary.assets_planned += 1
            summary.auctions_planned += len(mapped.auctions)
            continue
        if repository is None:
            raise ValueError("repository is required unless dry_run=True")
        asset_id = repository.upsert_asset(mapped.values)
        summary.assets_upserted += 1
        summary.auctions_upserted += repository.sync_auctions(
            asset_id, list(mapped.auctions)
        )
    return summary
