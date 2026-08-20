# Aureon Documentation

Welcome to the documentation for Aureon, the AI-powered urban digital twin platform.

## Contents

- [Architecture & Design](architecture.md) — System design, deployment architecture, data flows, and subsystem responsibilities.
- [API Contracts](api-contracts.md) — REST API schemas, endpoints, and WebSocket payloads.

## Deployment & Development

Aureon uses Docker and Docker Compose to orchestrate its services. A comprehensive `Makefile` is provided in the project root to simplify common tasks.

### Quick Commands (via Makefile)
- `make dev`: Start all services using Docker Compose.
- `make build`: Rebuild all Docker images.
- `make test`: Run all tests across backend, ML, and simulation.
- `make lint`: Run linters across all codebases.
- `make clean`: Remove caches, builds, and node_modules.

See the [Root README](../README.md) for more setup details.
