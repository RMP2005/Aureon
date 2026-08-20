# Aureon — Backend

FastAPI + Python API server.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Development

```bash
uvicorn src.main:app --reload     # Start dev server on http://localhost:8000
ruff check src/ tests/            # Lint
mypy src/                         # Type check
pytest                            # Run tests
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Structure

```
src/
├── main.py          → FastAPI app entry point
├── api/
│   ├── __init__.py  → Root API router
│   └── routes/      → Route modules by domain
├── core/
│   └── config.py    → Settings from env vars
├── models/          → Pydantic schemas & ORM models
└── services/        → Business logic layer
tests/               → Test suite
```
