"""Tests for data_ingestion modules — verifies seed data and ETL logic."""

import pandas as pd
import pytest


def test_seed_module_importable():
    """seed_realistic_data module should import without errors."""
    from data_ingestion import seed_realistic_data
    assert hasattr(seed_realistic_data, "_generate_fx_rates")
    assert hasattr(seed_realistic_data, "_generate_purchase_orders")
    assert hasattr(seed_realistic_data, "main")


def test_populate_module_importable():
    """populate_warehouse module should import without errors."""
    from data_ingestion import populate_warehouse
    assert hasattr(populate_warehouse, "populate_dim_date")
    assert hasattr(populate_warehouse, "populate_fact_procurement")
    assert hasattr(populate_warehouse, "populate_financial_kpis")


def test_populate_warehouse_functions_exist():
    """All expected ETL functions must be present."""
    from data_ingestion import populate_warehouse as pw

    expected = [
        "populate_dim_date",
        "populate_dim_material",
        "populate_dim_supplier",
        "populate_fact_procurement",
        "populate_supplier_spend_summary",
        "populate_supplier_performance_metrics",
        "populate_financial_kpis",
    ]
    for fn_name in expected:
        assert hasattr(pw, fn_name), f"Missing function: {fn_name}"
