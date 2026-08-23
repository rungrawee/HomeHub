import argparse
from dataclasses import asdict
import json

from app.location_backfill import backfill_locations
from app.repository import SupabaseRepository
from app.supabase_client import create_supabase_client


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill non-empty location fields from scraper CSV"
    )
    parser.add_argument("csv_path", help="Path to result.csv")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write updates to Supabase; the default is a read-only dry run",
    )
    args = parser.parse_args()

    repository = None
    if args.apply:
        repository = SupabaseRepository(create_supabase_client())
    summary = backfill_locations(args.csv_path, repository, apply=args.apply)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
