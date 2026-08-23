import json

from app.data_quality import build_data_quality_report
from app.repository import SupabaseRepository
from app.supabase_client import create_supabase_client


def main() -> None:
    repository = SupabaseRepository(create_supabase_client())
    report = build_data_quality_report(repository)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
