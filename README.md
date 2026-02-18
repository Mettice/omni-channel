# Casino Support Chat & Voice Assistant

This project is a small demo that combines:

- A **web chat UI** (`index.html`) styled as a dark casino support widget
- A **Python backend** (`retell/server.py`) that:
  - Serves a Retell-compatible **LLM WebSocket** endpoint for live voice calls
  - Exposes `POST /create-call` to create Retell web calls from the frontend
  - Logs and stores conversation history in Supabase

## Project structure

- `index.html` – frontend chat UI + Retell Web SDK call button
- `retell/server.py` – aiohttp app with HTTP + WebSocket for Retell
- `requirements.txt` – Python dependencies
- `.env` – local environment variables (ignored by git)

## Getting started (local)

1. **Create & activate a virtualenv** (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Create `.env` in the project root**:

```text
OPENAI_API_KEY=sk-...
RETELL_API_KEY=rt-...
SUPABASE_URL=...
SUPABASE_KEY=...
```

4. **Run the backend**:

```bash
python retell/server.py
```

This will start an aiohttp server on `http://localhost:8080` with:

- `POST /create-call` – creates a Retell web call and returns an `access_token`
- `GET /llm-websocket/{call_id}` – WebSocket endpoint Retell connects to

5. **Open the frontend**:

You can open `index.html` directly in the browser for quick testing, or serve it with a simple static server, e.g.:

```bash
python -m http.server 3000
```

Then open `http://localhost:3000/index.html`.

## Deploying

### Backend (Railway)

- Push this repo to GitHub.
- Create a new **Railway** project from the repo.
- Set environment variables in Railway:
  - `OPENAI_API_KEY`
  - `RETELL_API_KEY`
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
- Set the start command to:

```bash
python retell/server.py
```

### Frontend (Vercel)

- Deploy `index.html` (and any static assets) as a simple static site.
- Update the `fetch` URL in `index.html` from:

```js
fetch('http://localhost:8080/create-call', { ... })
```

to your Railway URL, e.g.:

```js
fetch('https://your-railway-app.up.railway.app/create-call', { ... })
```

so the call button works in production.

