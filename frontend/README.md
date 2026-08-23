# HomeHub frontend

React + Vite search interface for public LED auction assets.
Requires Node.js 20.19 or newer.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in the browser.

The frontend uses `http://127.0.0.1:8000` by default. To use another backend,
copy `.env.example` to `.env` and set `VITE_API_URL`.

```bash
npm test
npm run build
```
