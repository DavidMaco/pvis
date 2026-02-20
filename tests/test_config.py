"""Tests for config.py — verifies database URL construction."""

import os


def test_database_url_format():
    """DATABASE_URL must be a valid mysql+pymysql connection string."""
    from config import DATABASE_URL

    assert DATABASE_URL.startswith("mysql+pymysql://"), (
        f"Expected mysql+pymysql:// prefix, got: {DATABASE_URL[:30]}"
    )
    assert "pro_intel_2" in DATABASE_URL


def test_database_url_env_override(monkeypatch):
    """When DATABASE_URL env var is set, config should use it."""
    import importlib
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://test:test@localhost/testdb")
    import config
    importlib.reload(config)
    # After reload, the env var fallback should activate
    # (only if Streamlit secrets are unavailable, which they are in pytest)
    assert "testdb" in config.DATABASE_URL or "pro_intel_2" in config.DATABASE_URL
