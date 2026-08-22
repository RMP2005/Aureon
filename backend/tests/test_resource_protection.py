"""Tests for API resource abuse protection (Phase 8C) and run persistence."""

import pytest
from httpx import ASGITransport, AsyncClient

import src.core.rate_limit as _rl_mod
from src.main import app
from src.services.run_store import RunStore


# --- Rate limiting tests ---


@pytest.mark.asyncio
async def test_rate_limit_allows_requests_under_limit() -> None:
    """Requests below the rate limit succeed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_rejects_excessive_simulation_requests() -> None:
    """Excessive requests to protected endpoints are rejected with 429."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send more requests than the limit allows in a burst
        responses = []
        for _ in range(35):
            r = await client.get("/api/v1/simulation/state")
            responses.append(r.status_code)
        # Some should be 200, some should be 429
        assert 429 in responses
        assert 200 in responses


@pytest.mark.asyncio
async def test_rate_limit_does_not_affect_health_endpoint() -> None:
    """Health endpoint is not rate-limited."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = []
        for _ in range(35):
            r = await client.get("/api/v1/health")
            responses.append(r.status_code)
        # All should be 200 - health is not protected
        assert all(code == 200 for code in responses)


# --- Run persistence tests ---


def test_run_store_save_and_retrieve() -> None:
    """RunStore saves and retrieves a run."""
    store = RunStore()
    store.save_run("persist_1", {"data": "hello", "strategy": "aureon"}, run_type="single_run")
    result = store.get_run("persist_1")
    assert result is not None
    assert result["data"] == "hello"
    assert result["strategy"] == "aureon"


def test_run_store_persists_failed_run() -> None:
    """Failed runs are stored with error info."""
    store = RunStore()
    store.save_run("fail_1", None, status="failed", error_message="boom")
    result = store.get_run("fail_1")
    assert result is not None


def test_run_store_list_runs() -> None:
    """list_runs returns all stored runs."""
    store = RunStore()
    store.save_run("list_a", {"executed_at": "t1"})
    store.save_run("list_b", {"executed_at": "t2"})
    runs = store.list_runs()
    run_ids = [r["run_id"] for r in runs]
    assert "list_a" in run_ids
    assert "list_b" in run_ids


def test_run_store_count() -> None:
    """count_runs returns the number of stored runs."""
    store = RunStore()
    initial = store.count_runs()
    store.save_run("cnt_1", {"v": 1})
    assert store.count_runs() == initial + 1


def test_run_store_delete() -> None:
    """delete_run removes the run."""
    store = RunStore()
    store.save_run("del_1", {"v": 1})
    assert store.get_run("del_1") is not None
    store.delete_run("del_1")
    assert store.get_run("del_1") is None


# --- CORS / Security header tests ---


@pytest.mark.asyncio
async def test_security_headers_present() -> None:
    """Responses include standard security headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_cors_does_not_allow_disallowed_methods() -> None:
    """CORS preflight rejects methods not in the allow list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            },
        )
    # DELETE is not in the allowed methods, so Access-Control-Allow-Methods
    # should NOT include DELETE
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "DELETE" not in allow_methods


@pytest.mark.asyncio
async def test_cors_allows_get_and_post() -> None:
    """CORS preflight succeeds for allowed methods."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for method in ("GET", "POST"):
            response = await client.options(
                "/api/v1/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": method,
                },
            )
            allow_methods = response.headers.get("access-control-allow-methods", "")
            assert method in allow_methods


@pytest.mark.asyncio
async def test_cors_origins_default_to_localhost() -> None:
    """Default CORS origins are configured for local development."""
    from src.core.config import settings

    assert "http://localhost:3000" in settings.CORS_ORIGINS
