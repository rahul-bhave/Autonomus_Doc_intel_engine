"""
Uvicorn entrypoint for the Document Intel Engine REST API.

Run:
    .venv/Scripts/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from src.api.server import app  # noqa: F401 — re-exported for uvicorn

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
