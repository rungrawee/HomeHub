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

For the first real database test, limit the import to one row:

```bash
PYTHONPATH=backend .venv/bin/python backend/import_csv.py scraper/result.csv --limit 1
```

Verify that one asset and its auction history are correct in Supabase before
running an unrestricted import.

After reviewing the summary, create `backend/.env` from `.env.example` and add
the Supabase server credentials. Never commit that file. The real import is:

```bash
PYTHONPATH=backend .venv/bin/python backend/import_csv.py scraper/result.csv
```

Run the unit tests before an import:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s backend/tests -v
```

Check the imported Supabase data without changing it:

```bash
PYTHONPATH=backend .venv/bin/python backend/check_data_quality.py
```

Start the API and open `http://127.0.0.1:8000/docs`:

```bash
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --reload
```

`GET /assets` supports `province`, `amphur`, `tambon`, `asset_type`,
`deed_number`, `min_price`, `max_price`, `auction_date_from`,
`auction_date_to`, `page`, and `page_size` query parameters.

The real import uses `source_key` and auction composite keys for idempotent
upserts. Running the same CSV again should update existing records rather than
creating duplicates.
