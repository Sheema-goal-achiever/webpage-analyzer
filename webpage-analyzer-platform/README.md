# webpage-analyzer-platform

Simple scaffold for a FastAPI backend and Streamlit frontend.

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the backend:

```bash
./run_backend.sh
```

3. In a separate terminal, run the frontend:

```bash
./run_frontend.sh
```

The Streamlit app will POST to the FastAPI `/analyze` endpoint. `backend/app/main.py` currently contains a placeholder implementation.
