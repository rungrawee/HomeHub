# HomeHub: LED Asset Search

Project structure:

- `scraper/`: Playwright scraper and CSV output pipeline.
- `backend/`: API service area for importing data and serving the web app.
- `frontend/`: Web UI area for searching assets and managing favorites.
- `supabase/`: Database schema files.

The scraper currently runs manually from `scraper/`:

```bash
cd scraper
../.venv/bin/python led_monitor.py
```

Backend and frontend are placeholders until the API design is approved.

Backend import instructions are documented in `backend/README.md`. Always run
the CSV importer with `--dry-run` before using Supabase credentials.
