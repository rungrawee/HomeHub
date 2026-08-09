import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


class MappingError(ValueError):
    """Raised when a validated CSV row cannot be mapped to the DB model."""


def clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\xa0", " ").split())


def parse_amount(value: str | None) -> str:
    cleaned = clean_text(value).replace(",", "")
    if not cleaned or cleaned in {"-", "ไม่มี"}:
        return "0.00"
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as error:
        raise MappingError(f"Invalid monetary value: {value!r}") from error
    if amount < 0:
        raise MappingError(f"Monetary value cannot be negative: {value!r}")
    return f"{amount:.2f}"


def build_source_key(row: dict[str, str]) -> str:
    parts = [
        clean_text(row.get("หมายเลขคดี")),
        clean_text(row.get("ลำดับ")),
        clean_text(row.get("โฉนดที่ดิน")),
    ]
    if not parts[0] or not parts[1]:
        raise MappingError("หมายเลขคดี and ลำดับ are required for source_key")
    return "|".join(parts)


@dataclass(frozen=True)
class AuctionRecord:
    auction_round: int
    auction_date: str
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "auction_round": self.auction_round,
            "auction_date": self.auction_date,
            "status": self.status,
        }


@dataclass(frozen=True)
class MappedAsset:
    values: dict[str, object]
    auctions: tuple[AuctionRecord, ...]


def thai_date_to_iso(value: str) -> str:
    try:
        day, month, year = (int(part) for part in value.split("/"))
        if year >= 2400:
            year -= 543
        return date(year, month, day).isoformat()
    except (ValueError, TypeError) as error:
        raise MappingError(f"Invalid auction date: {value!r}") from error


def extract_auctions(detail_raw_text: str | None) -> tuple[AuctionRecord, ...]:
    auctions = []
    pattern = re.compile(
        r"^\s*(?P<round>\d+)\s+(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<status>.+?)\s*$"
    )
    for line in (detail_raw_text or "").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        auctions.append(
            AuctionRecord(
                auction_round=int(match.group("round")),
                auction_date=thai_date_to_iso(match.group("date")),
                status=clean_text(match.group("status")),
            )
        )
    return tuple(auctions)


def map_csv_row(row: dict[str, str]) -> MappedAsset:
    values = {
        "source_key": build_source_key(row),
        "lot": clean_text(row.get("ล็อต")),
        "sequence": clean_text(row.get("ลำดับ")),
        "case_number": clean_text(row.get("หมายเลขคดี")),
        "asset_type": clean_text(row.get("ประเภททรัพย์_detail")),
        "deed_number": clean_text(row.get("โฉนดที่ดิน")),
        "rai": clean_text(row.get("ไร่")),
        "ngan": clean_text(row.get("งาน")),
        "square_wah": clean_text(row.get("ตรว")),
        "area_detail": clean_text(row.get("เนื้อที่_detail")),
        "price": parse_amount(row.get("ราคา")),
        "price_final": parse_amount(row.get("ราคา_final")),
        "deposit_amount": parse_amount(row.get("deposit_amount")),
        "tambon": clean_text(row.get("ตำบล_detail")),
        "amphur": clean_text(row.get("อำเภอ_detail")),
        "province": clean_text(row.get("จังหวัด_detail")),
        "owner_name": clean_text(row.get("ผู้ถือกรรมสิทธิ์")),
        "officer_name": clean_text(row.get("เจ้าของสำนวน")),
        "sale_location": clean_text(row.get("สถานที่จำหน่าย")),
        "location": clean_text(row.get("Location")),
        "detail_url": clean_text(row.get("detail_url")),
        "raw_detail": row.get("detail_raw_text", ""),
    }
    return MappedAsset(values=values, auctions=extract_auctions(row.get("detail_raw_text")))
