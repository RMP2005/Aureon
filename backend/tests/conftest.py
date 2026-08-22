"""Shared test fixtures."""

import pytest

import src.core.rate_limit as _rl_mod


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Reset the rate limiter state before each test."""
    if _rl_mod.active_limiter is not None:
        _rl_mod.active_limiter.reset()
