# Saha API

Python 3.12 FastAPI service for search, extraction, transliteration, and meaning.

```bash
cp .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
pytest
```

Docker (from the **repository root**):

```bash
docker build -f services/api/Dockerfile -t saha-api .
docker run --rm -p 8000:8000 --env-file services/api/.env saha-api
```
