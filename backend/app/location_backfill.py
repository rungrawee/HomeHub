import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from app.mapping import MappingError, build_source_key, clean_text


@dataclass(frozen=True)
class LocationBackfillSummary:
    rows_read: int = 0
    eligible: int = 0
    updated: int = 0
    not_found: int = 0
    unmappable: int = 0


def load_location_updates(csv_path: str | Path) -> list[tuple[str, dict[str, str]]]:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as csv_file:
        return list(build_location_updates(csv.DictReader(csv_file)))


def build_location_updates(
    rows: Iterable[dict[str, str]],
) -> Iterable[tuple[str, dict[str, str]]]:
    for row in rows:
        try:
            source_key = build_source_key(row)
        except MappingError:
            continue
        values = {
            "province": clean_text(row.get("จังหวัด_detail")),
            "amphur": clean_text(row.get("อำเภอ_detail")),
            "tambon": clean_text(row.get("ตำบล_detail")),
            "location": clean_text(row.get("Location")),
        }
        # Never replace valid database values with blanks from an incomplete row.
        values = {key: value for key, value in values.items() if value}
        if values.get("province") and values.get("amphur") and values.get("location"):
            yield source_key, values


def backfill_locations(
    csv_path: str | Path,
    repository: Any | None,
    *,
    apply: bool = False,
) -> LocationBackfillSummary:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    updates = list(build_location_updates(rows))
    unmappable = len(rows) - len(updates)
    if not apply:
        return LocationBackfillSummary(
            rows_read=len(rows), eligible=len(updates), unmappable=unmappable
        )
    if repository is None:
        raise ValueError("repository is required when apply=True")

    updated = 0
    not_found = 0
    for source_key, values in updates:
        if repository.update_asset_fields(source_key, values):
            updated += 1
        else:
            not_found += 1
    return LocationBackfillSummary(
        rows_read=len(rows),
        eligible=len(updates),
        updated=updated,
        not_found=not_found,
        unmappable=unmappable,
    )
