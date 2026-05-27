# Webpage Analyzer

A small full-stack project that analyzes web pages using a FastAPI backend and a Streamlit frontend.

The backend fetches a URL, parses the HTML with BeautifulSoup, stores snapshots in SQLite, and exposes endpoints for analysis, history, snapshot retrieval, and comparison.

## Features

- Fetch and analyze web pages by URL
- Extract page title, text, HTML DOM structure, and basic metrics
- Persist snapshot history in SQLite
- Compare two snapshots to detect DOM changes
- Streamlit frontend for submitting URLs and reviewing results

## Repository structure

- `webpage-analyzer-platform/`
  - `backend/app/main.py` - FastAPI application and analysis logic
  - `frontend_streamlit.py` - Streamlit user interface
  - `requirements.txt` - Python dependencies
  - `run_backend.sh` - Start the backend server
  - `run_frontend.sh` - Start the Streamlit frontend
  - `webpage_analyzer.db` - SQLite database used by the backend

## Quick start

1. Open a terminal in the repository root.
2. Change to the platform directory:

```bash
cd webpage-analyzer-platform
```

3. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start the backend API:

```bash
./run_backend.sh
```

6. In a second terminal, start the Streamlit frontend:

```bash
./run_frontend.sh
```

7. Open the Streamlit app in your browser at `http://localhost:8501`.

## Backend API

The backend runs on `http://localhost:8000` by default.

### Endpoints

- `GET /` — API root health message
- `GET /health` — health check
- `POST /analyze` — analyze a web page
- `GET /history` — list stored snapshot metadata
- `GET /snapshot/{snapshot_id}` — fetch a specific snapshot
- `GET /snapshots/by-url?url={url}` — snapshots for a URL
- `GET /compare?left_id={left}&right_id={right}` — compare two snapshot IDs
- `POST /compare` — compare two snapshots by JSON body

### Example request

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Data storage

The backend stores analysis snapshots in SQLite. The schema includes:

- `id`
- `url`
- `timestamp`
- `title`
- `html`
- `text`
- `total_links`
- `total_buttons`
- `total_forms`
- `total_tables`
- `total_inputs`

## Development notes

- The project uses `BeautifulSoup` for HTML parsing.
- The DOM is serialized into nested JSON for tree exploration and comparison.
- Snapshot comparison reports added, removed, and changed DOM nodes.
- The backend is designed for local experimentation and can be extended with more metrics.

## Notes

- Run the commands from `webpage-analyzer-platform/` so the backend writes to the correct SQLite file.
- If the database file does not exist, it is created automatically on startup.
- The frontend communicates with the backend at `/analyze`.
