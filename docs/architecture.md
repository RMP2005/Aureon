# Aureon Architecture

Aureon is an AI-powered urban digital twin platform consisting of four main subsystems: Frontend, Backend, ML, and Simulation.

## System Architecture

```mermaid
graph TD
    subgraph Frontend
        UI[Next.js UI]
        WS_Client[WebSocket Client]
    end

    subgraph Backend
        API[FastAPI Server]
        Router_Health[Health Router]
        Router_Sim[Simulation Router]
        Router_ML[ML Router]
        API --> Router_Health
        API --> Router_Sim
        API --> Router_ML
    end

    subgraph Simulation
        Engine[Simulation Engine]
        City[City Model]
        Environment[Environment Model]
        Emergency[Emergency Model]
        Engine --> City
        Engine --> Environment
        Engine --> Emergency
    end

    subgraph ML
        Predictor[Traffic/Weather Predictor]
        Classifier[Incident Classifier]
        Optimizer[Resource Optimizer]
    end

    UI -->|REST| API
    WS_Client <-->|WebSocket| API
    Router_Sim -->|Control| Engine
    Engine -->|State Updates| API
    Router_ML -->|Inference| Predictor
    Router_ML -->|Inference| Classifier
    Router_ML -->|Inference| Optimizer
```

## Docker Deployment Architecture

Aureon uses Docker Compose for local development and deployment.

```mermaid
graph TD
    Client[Browser] -->|HTTP:3000| Frontend_Container
    Frontend_Container -->|HTTP:8000| Backend_Container
    Client -->|HTTP:8000| Backend_Container
    
    subgraph Docker Compose
        Frontend_Container[Frontend: Node 20]
        Backend_Container[Backend: Python 3.11]
    end
```

## Data Flow (Simulation → ML → Backend → Frontend)

1. **Simulation Engine** generates urban states (e.g., traffic conditions, weather events, emergencies) continuously.
2. **Backend API** receives these states or reads them from the simulation process.
3. **ML Models** process the simulation data (e.g., predicting traffic flow, classifying incidents, optimizing emergency response routing).
4. **Backend API** aggregates the simulated state and ML insights.
5. **Frontend UI** requests the aggregated data via REST or receives real-time streams via WebSocket.

## Models

### Simulation Models
- **Environment**: Simulates weather, temperature, and environmental conditions.
- **City**: Simulates traffic flow, crowd movement, and urban infrastructure.
- **Emergency**: Simulates random or triggered events like accidents, fires, and medical emergencies.

### ML Models
- **Classifier**: Categorizes incidents based on severity, type, and required response.
- **Predictor**: Forecasts future states (e.g., traffic bottlenecks in the next 30 minutes).
- **Optimizer**: Suggests optimal resource allocation (e.g., routing ambulances, adjusting traffic lights).

## API Layer

The backend uses FastAPI to expose three main route groups:
1. **Health (`/api/v1/health`)**: System status and dependency checks.
2. **Simulation (`/api/v1/simulations`)**: Endpoints to start, stop, configure, and monitor digital twin runs.
3. **ML (`/api/v1/models`)**: Endpoints to list models, retrieve metadata, and run inferences against simulation states.
