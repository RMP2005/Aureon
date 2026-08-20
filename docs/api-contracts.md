# Aureon — API Contracts

> This document will define the API contracts between frontend and backend.
> It will be populated as endpoints are implemented.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

> TBD — JWT-based authentication planned for Phase 1.

## Endpoints

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/api/v1/status` | API status |

### Simulation (Phase 2)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/simulations` | Create and start a simulation |
| GET | `/api/v1/simulations/{id}` | Get simulation status |
| DELETE | `/api/v1/simulations/{id}` | Stop a simulation |
| WS | `/ws/simulations/{id}` | Stream simulation state |

### ML (Phase 3)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/predictions` | Request model inference |
| GET | `/api/v1/models` | List available models |
| GET | `/api/v1/models/{id}` | Get model metadata |

## Response Format

All responses follow a consistent envelope:

```json
{
  "status": "ok",
  "data": { ... },
  "error": null
}
```
