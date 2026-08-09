import argparse

from app.importer import import_csv
from app.repository import SupabaseRepository
from app.supabase_client import create_supabase_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Import LED scraper CSV into Supabase")
    parser.add_argument("csv_path", help="Path to result.csv")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and map the CSV without connecting to Supabase",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Import only the first N valid rows",
    )
    args = parser.parse_args()

    repository = None
    if not args.dry_run:
        repository = SupabaseRepository(create_supabase_client())
    summary = import_csv(
        args.csv_path,
        repository,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    print(f"Rows read: {summary.rows_read}")
    if args.dry_run:
        print(f"Assets planned: {summary.assets_planned}")
        print(f"Auctions planned: {summary.auctions_planned}")
    else:
        print(f"Assets upserted: {summary.assets_upserted}")
        print(f"Auctions upserted: {summary.auctions_upserted}")


if __name__ == "__main__":
    main()
