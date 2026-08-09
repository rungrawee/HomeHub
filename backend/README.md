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
