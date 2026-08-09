# Backend

FastAPI service for importing and serving LED asset data.

Planned responsibilities:

- Import validated scraper data into Supabase.
- Expose read-only asset search endpoints.
- Manage authentication and favorites.
- Keep Supabase service credentials private on the server.

## Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## CSV import

Run the safe validation first. This does not need Supabase credentials and does
not write to the database:

```bash
PYTHONPATH=backend .venv/bin/python backend/import_csv.py scraper/result.csv --dry-run
```

After reviewing the summary, create `backend/.env` from `.env.example` and add
the Supabase server credentials. Never commit that file. The real import is:

```bash
PYTHONPATH=backend .venv/bin/python backend/import_csv.py scraper/result.csv
```

Run the unit tests before an import:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
```

The real import uses `source_key` and auction composite keys for idempotent
upserts. Running the same CSV again should update existing records rather than
creating duplicates.
