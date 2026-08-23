from collections import Counter
from dataclasses import asdict, dataclass
from typing import Any


IMPORTANT_ASSET_FIELDS = (
    "location",
    "province",
    "amphur",
    "price_final",
    "deposit_amount",
)


@dataclass(frozen=True)
class DataQualityReport:
    assets: int
    auctions: int
    duplicate_source_keys: int
    orphan_auctions: int
    missing_fields: dict[str, int]

    @property
    def is_healthy(self) -> bool:
        return (
            self.assets > 0
            and self.duplicate_source_keys == 0
            and self.orphan_auctions == 0
            and all(count == 0 for count in self.missing_fields.values())
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "is_healthy": self.is_healthy}


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def build_data_quality_report(repository: Any) -> DataQualityReport:
    asset_columns = "id,source_key," + ",".join(IMPORTANT_ASSET_FIELDS)
    assets = repository.fetch_all("assets", asset_columns)
    auctions = repository.fetch_all("auctions", "id,asset_id")

    source_key_counts = Counter(
        asset.get("source_key") for asset in assets if asset.get("source_key")
    )
    duplicate_source_keys = sum(
        count - 1 for count in source_key_counts.values() if count > 1
    )
    asset_ids = {asset.get("id") for asset in assets}
    orphan_auctions = sum(
        1 for auction in auctions if auction.get("asset_id") not in asset_ids
    )
    missing_fields = {
        field: sum(1 for asset in assets if _is_missing(asset.get(field)))
        for field in IMPORTANT_ASSET_FIELDS
    }

    return DataQualityReport(
        assets=len(assets),
        auctions=len(auctions),
        duplicate_source_keys=duplicate_source_keys,
        orphan_auctions=orphan_auctions,
        missing_fields=missing_fields,
    )
