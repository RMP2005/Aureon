# Phase 8 — Security Audit Report

**Date:** 2026-08-23
**Commits:** 24c9564 (8B), e6e7fd7 (8C), cd7535b (8D), 8E (no code changes)
**Tests:** 22/22 passed

---

## Executive Summary

Phase 8 performed a systematic security audit and hardening of the Aureon backend API. Three concrete vulnerabilities were identified and fixed (8B), two resource abuse protections were added (8C), and CORS/security headers were hardened (8D). The final audit (8E) confirmed no additional vulnerabilities in subprocess handling, file I/O, secrets, dependencies, or production configuration.

**Severity distribution:** 2 MEDIUM, 5 LOW, 2 INFORMATIONAL — all addressed or documented.

---

## Attack Surface Reviewed

| Area | Scope | Status |
|------|-------|--------|
| Subprocess (osmium) | `simulation/src/maps/osm_provider.py:145` | SAFE — `shell=False`, hardcoded bbox, no user input in args |
| File handling (PBF/GraphML) | `simulation/src/maps/osm_provider.py`, `backend/src/services/simulation_service.py` | SAFE — `run_id` is dict key (not file path); PBF/GraphML loaded from fixed cache dir |
| File handling (GraphML) | `osmnx.load_graphml()` | SAFE — loads from fixed path `simulation/data/osm_cache/`, no user-controlled filename |
| File handling (write) | `osmnx.save_graphml()` | SAFE — writes only to `cache_path`, no user input |
| Secrets/configuration | All `.env.example` files, `config.py`, source code | CLEAN — no hardcoded secrets, credentials, or API keys |
| Dependencies (backend) | `pyproject.toml` | LOW RISK — all pinned to minimum versions, no known vulnerabilities at audit time |
| Dependencies (frontend) | `package.json` | LOW RISK — standard Next.js stack |
| API endpoints | `/api/v1/simulation/*`, `/api/v1/health`, `/api/v1/models/*` | HARDENED — see fixes below |
| CORS | `main.py:50-56` | HARDENED — methods/headers restricted |
| Docker | `docker-compose.yml`, Dockerfiles | SAFE — `docker-compose.yml` is dev-only; production Dockerfile uses clean CMD without `--reload` |
| Logging | `backend/src/core/logging.py` | SAFE — no secrets logged; exception details logged server-side only |
| Health endpoint | `backend/src/api/routes/health.py` | SAFE — returns project name and version only |

---

## Verified Findings by Severity

### MEDIUM (Fixed in 8B)

**M1: Synchronous blocking in async event handler**
- File: `backend/src/api/routes/simulation.py`
- Issue: `run_simulation()` and `run_comparison()` were sync calls in `async def`, blocking the uvicorn event loop
- Impact: Single long simulation could freeze all concurrent requests
- Fix: Wrapped in `asyncio.to_thread()`

**M2: Excessive simulation resource limits**
- File: `backend/src/models/schemas.py`
- Issue: `duration_minutes` allowed up to 1440, `incident_rate_per_hour` up to 60
- Impact: Combined allowed 14,400 incidents per request — effective DoS vector
- Fix: Capped to `le=120` and `le=30` respectively

### LOW (Fixed in 8B, 8C, 8D)

**L1: Exception detail leakage**
- File: `backend/src/api/routes/simulation.py`
- Issue: `str(e)` in HTTP error responses exposed internal exception messages
- Fix: Generic error strings returned; full details logged server-side via `logger.exception()`

**L2: Unbounded in-memory run storage**
- File: `backend/src/services/simulation_service.py`
- Issue: `_runs` dict grew without limit
- Fix: `OrderedDict` with configurable `max_stored_runs` (default 100), oldest-first eviction

**L3: No rate limiting**
- Issue: No request throttling on expensive simulation endpoints
- Fix: `SlidingWindowRateLimiter` middleware, configurable via `RATE_LIMIT_MAX_REQUESTS` (default 30/60s)

**L4: Overly permissive CORS methods/headers**
- File: `backend/src/main.py`
- Issue: `allow_methods=["*"]`, `allow_headers=["*"]`
- Fix: Restricted to `["GET", "POST", "OPTIONS"]` and `["Content-Type"]`

**L5: Missing security headers**
- Issue: No `X-Content-Type-Options` or `X-Frame-Options`
- Fix: `SecurityHeadersMiddleware` adds `nosniff` and `DENY`

### INFORMATIONAL (Not Fixed — Not Vulnerabilities)

**I1: No authentication**
- All endpoints are public. This is a research/development API — authentication is not implemented or claimed. Not a vulnerability.

**I2: `ResponseEnvelope.data: Any`**
- No type validation on response payloads. Acceptable for current architecture; would matter if internal objects were accidentally exposed.

**I3: OpenAPI docs always enabled**
- `/api/docs`, `/api/redoc`, `/api/openapi.json` are always accessible. For a dev/research API this is acceptable. Production deployment could conditionally disable via environment check.

---

## Fixes Implemented Across Phase 8

| Commit | Phase | Changes |
|--------|-------|---------|
| `24c9564` | 8B | `asyncio.to_thread()` for async handlers; parameter bounds; generic errors with server-side logging |
| `e6e7fd7` | 8C | Sliding-window rate limiter; `OrderedDict` LRU eviction for run storage; config settings |
| `cd7535b` | 8D | CORS methods/headers restriction; `SecurityHeadersMiddleware` |
| 8E | — | No code changes — all areas audited clean |

**Files modified:** `simulation.py`, `schemas.py`, `simulation_service.py`, `config.py`, `main.py`, `rate_limit.py` (new), `conftest.py` (new), `test_resource_protection.py` (new), `test_simulation_routes.py`

---

## Tests Performed

| Category | Count | Status |
|----------|-------|--------|
| Health check | 1 | PASSED |
| Simulation routes (existing) | 3 | PASSED |
| Parameter bounds (Phase 8B) | 5 | PASSED |
| Rate limiting (Phase 8C) | 3 | PASSED |
| LRU eviction (Phase 8C) | 3 | PASSED |
| CORS/security headers (Phase 8D) | 4 | PASSED |
| Simulation service | 3 | PASSED |
| **Total** | **22** | **ALL PASSED** |

---

## Safe / Verified Areas

- **Subprocess calls:** Only `osmium extract` in `osm_provider.py:145`. Uses list form (`shell=False`), hardcoded bbox floats, no user input in arguments. Not exploitable.
- **File I/O:** PBF/GraphML loaded from fixed cache directory. `run_id` is a dict key, not a filesystem path. `osmnx.save_graphml` writes only to `cache_path`.
- **Secrets:** No hardcoded credentials, API keys, or tokens in any source file. All configuration via pydantic-settings with env vars.
- **Docker:** Production Dockerfile CMD does not use `--reload`. `docker-compose.yml` is explicitly dev configuration.
- **Logging:** No sensitive data logged. Exception details logged server-side only, generic strings returned to clients.
- **Database:** SQLite URL is a local file default (`aureon.db`). No remote DB credentials.
- **sys.path manipulation:** `simulation_service.py` manipulates `sys.path` to import simulation modules. This is a code quality concern, not a security vulnerability — paths are computed from `__file__`, not from user input.

---

## Remaining Production Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| No authentication on any endpoint | MEDIUM | Acceptable for dev/research. Add auth before public deployment. |
| SQLite in production | LOW | Fine for moderate load. Consider PostgreSQL for high-concurrency deployments. |
| OpenAPI docs publicly accessible | LOW | Disable in production via environment check if needed. |
| No HTTPS enforcement | LOW | TLS should be terminated at reverse proxy/load balancer. |
| `sys.path` manipulation | INFO | Code quality issue. Consider proper package structure in future. |

---

## Explicitly Unverified / Out of Scope

- Frontend security (XSS, client-side vulnerabilities) — Phase 8 focused on backend API
- Network-level attacks (DDoS beyond rate limiting)
- Physical security of deployment infrastructure
- Third-party library CVEs (dependencies pinned to minimum versions, no known active CVEs at audit time)
- WebSocket security (endpoint registered but not implemented beyond stub)
- ML model security (models not loaded in current architecture)

---

## Conclusion

The Aureon backend API is in a solid security posture for a research/development system. All identified vulnerabilities have been fixed. The remaining risks are architectural decisions appropriate for the project's current stage.
