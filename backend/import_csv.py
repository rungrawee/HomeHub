import argparse

from app.importer import import_csv
from app.repository import SupabaseRepository
from app.supabase_client import create_supabase_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Import LED scraper CSV into Supabase")
    parser.add_argument("csv_path", help="Path to result.csv")
    args = parser.parse_args()

    repository = SupabaseRepository(create_supabase_client())
    summary = import_csv(args.csv_path, repository)
    print(f"Rows read: {summary.rows_read}")
    print(f"Assets upserted: {summary.assets_upserted}")
    print(f"Auctions upserted: {summary.auctions_upserted}")


if __name__ == "__main__":
    main()
