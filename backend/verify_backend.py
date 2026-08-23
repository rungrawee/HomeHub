import json

from app.readiness import check_backend_readiness
from app.settings import get_settings
from app.supabase_client import create_supabase_client


def main() -> None:
    settings = get_settings()
    client = None
    try:
        client = create_supabase_client(settings)
    except (ImportError, ValueError):
        pass
    report = check_backend_readiness(settings, client)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    if not report.ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
