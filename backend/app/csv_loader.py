import csv
from pathlib import Path


REQUIRED_COLUMNS = frozenset(
    {
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
    }
)


class CsvValidationError(ValueError):
    """Raised when the scraper CSV cannot be safely imported."""


def clean_csv_value(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\xa0", " ").split())


def read_csv_rows(
    path: str | Path,
    required_columns: frozenset[str] = REQUIRED_COLUMNS,
) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = {clean_csv_value(name) for name in (reader.fieldnames or [])}
        missing = sorted(required_columns - fieldnames)
        if missing:
            raise CsvValidationError(
                "CSV is missing required columns: " + ", ".join(missing)
            )

        rows = []
        row_errors = []
        for row_number, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                row_errors.append(f"row {row_number}: has more values than headers")
                continue

            row = {}
            for key, value in raw_row.items():
                if key is None:
                    continue
                clean_key = clean_csv_value(key)
                # Keep detail_raw_text intact; auction parsing needs its rows.
                row[clean_key] = (
                    (value or "").strip()
                    if clean_key == "detail_raw_text"
                    else clean_csv_value(value)
                )
            missing_values = [
                column
                for column in ("หมายเลขคดี", "ลำดับ")
                if not row.get(column)
            ]
            if missing_values:
                row_errors.append(
                    f"row {row_number}: missing values for "
                    + ", ".join(missing_values)
                )
                continue
            rows.append(row)

    if row_errors:
        raise CsvValidationError("CSV validation failed: " + "; ".join(row_errors))
    return rows
