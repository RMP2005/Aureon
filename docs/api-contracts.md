# Aureon API Contracts

Base URL: `/api/v1`

---

## 1. Health

### `GET /health`
Returns system health status.

**Response**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "simulation": "ready",
    "ml": "ready"
  }
}
```

---

## 2. Simulations

### `POST /simulations`
Start a new simulation run.

**Request**
```json
{
  "name": "Morning Rush Hour",
  "config": {
    "duration": 3600,
    "traffic_density": "high",
    "weather": "rain"
  }
}
```

**Response**
```json
{
  "id": "sim-12345",
  "name": "Morning Rush Hour",
  "status": "starting",
  "created_at": "2026-08-21T02:00:00Z"
}
```

### `GET /simulations`
List all active and past simulations.

**Response**
```json
{
  "data": [
    {
      "id": "sim-12345",
      "name": "Morning Rush Hour",
      "status": "running"
    }
  ],
  "total": 1
}
```

### `GET /simulations/{id}`
Get details of a specific simulation.

**Response**
```json
{
  "id": "sim-12345",
  "name": "Morning Rush Hour",
  "status": "running",
  "current_time": 1500,
  "config": {
    "duration": 3600,
    "traffic_density": "high",
    "weather": "rain"
  }
}
```

### `DELETE /simulations/{id}`
Stop and remove a simulation.

**Response**
```json
{
  "message": "Simulation sim-12345 stopped and deleted"
}
```

---

## 3. Machine Learning

### `GET /models`
List available ML models in the registry.

**Response**
```json
{
  "data": [
    {
      "id": "clf-01",
      "name": "Incident Classifier",
      "version": "v1.2",
      "status": "active"
    }
  ],
  "total": 1
}
```

### `GET /models/{id}`
Get details for a specific model.

**Response**
```json
{
  "id": "clf-01",
  "name": "Incident Classifier",
  "version": "v1.2",
  "description": "Classifies emergency incidents",
  "status": "active"
}
```

### `POST /models/predict`
Run an inference using a specific model.

**Request**
```json
{
  "model_id": "clf-01",
  "inputs": {
    "feature_1": 0.5,
    "feature_2": 1.2
  }
}
```

**Response**
```json
{
  "prediction": "high_severity",
  "confidence": 0.94,
  "model_id": "clf-01",
  "timestamp": "2026-08-21T02:05:00Z"
}
```
