# Aureon Backend

FastAPI backend for the Aureon urban intelligence platform.

## Features
- FastAPI application with robust lifespan management
- Pydantic v2 settings management
- ML Model inference placeholder routes
- Simulation orchestration placeholder routes
- Standardized API response schema wrapper

## Setup
1. Ensure you have Python 3.11+ installed.
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Configure environment:
   ```bash
   cp .env.example .env
   ```
5. Run the server:
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation
Once the server is running, you can access the OpenAPI documentation at:
- Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- ReDoc: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
