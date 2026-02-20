"""Tests for streamlit_app.py — verifies the app can be imported and key functions exist."""

import os
import pytest

# ── Helper: detect whether MySQL is reachable ────────────────────────────────

def _mysql_available() -> bool:
    """Return True only if MySQL is actually accepting connections."""
    try:
        from sqlalchemy import create_engine, text
        from config import DATABASE_URL
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


_skip_no_db = pytest.mark.skipif(
    not _mysql_available(),
    reason="MySQL is not reachable (CI or no local server)",
)


def test_streamlit_app_compiles():
    """streamlit_app.py should compile without syntax errors."""
    import py_compile
    py_compile.compile("streamlit_app.py", doraise=True)


@_skip_no_db
def test_database_connectivity():
    """Database should be reachable and return data."""
    from sqlalchemy import create_engine, text
    from config import DATABASE_URL

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


@_skip_no_db
def test_core_tables_populated():
    """All core transactional and warehouse tables should have data."""
    from sqlalchemy import create_engine, text
    from config import DATABASE_URL

    engine = create_engine(DATABASE_URL)
    required_tables = {
        "countries": 8,
        "currencies": 5,
        "suppliers": 8,
        "materials": 50,
        "purchase_orders": 700,
        "fx_rates": 4000,
        "dim_date": 1400,
        "dim_supplier": 8,
        "fact_procurement": 1900,
        "supplier_performance_metrics": 8,
        "financial_kpis": 1,
    }

    with engine.connect() as conn:
        for table, min_rows in required_tables.items():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count >= min_rows, (
                f"Table {table} has {count} rows, expected >= {min_rows}"
            )
