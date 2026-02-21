"""
demo_data.py — Synthetic demo DataFrames for PVIS dashboard.

When no MySQL database is reachable (e.g. Streamlit Cloud), the dashboard
calls `demo_query(sql)` instead of hitting the DB.  This module pattern-
matches the SQL text and returns a realistic DataFrame so every chart and
KPI renders correctly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ── Constants ────────────────────────────────────────────────────────────────

_RNG = np.random.RandomState(42)

_SUPPLIERS = [
    "Lagos Industrial Supply Co.",
    "Dangote Materials Ltd.",
    "Zenith Procurement Group",
    "Ogun Steel Works",
    "Abuja Tech Supplies",
    "Niger Delta Chemicals",
    "Kano Textiles Intl.",
    "Port Harcourt Logistics",
    "Ibadan Agri-Trade",
    "Abia Plastics Corp.",
]

_CATEGORIES = [
    "Raw Materials",
    "Packaging",
    "Chemicals",
    "Electronics",
    "Steel & Metals",
    "Textiles",
    "Office Supplies",
    "Logistics",
]

_CURRENCIES = [
    {"currency_id": 1, "currency_code": "USD"},
    {"currency_id": 2, "currency_code": "EUR"},
    {"currency_id": 3, "currency_code": "NGN"},
    {"currency_id": 4, "currency_code": "GBP"},
    {"currency_id": 5, "currency_code": "CNY"},
]

# ── Helper: date ranges ─────────────────────────────────────────────────────

def _monthly_dates(months: int = 18):
    """Return a list of month-start strings like '2024-07'."""
    today = datetime.today()
    return [(today - timedelta(days=30 * i)).strftime("%Y-%m") for i in range(months)][::-1]


def _daily_dates(days: int = 365):
    """Return a list of daily datetime objects."""
    today = datetime.today()
    return [today - timedelta(days=i) for i in range(days)][::-1]


# ── Individual demo generators ───────────────────────────────────────────────

def _total_spend() -> pd.DataFrame:
    return pd.DataFrame([{"spend": 12_450_890.50}])


def _fx_exposure_pct() -> pd.DataFrame:
    return pd.DataFrame([{"fx_pct": 37.4}])


def _avg_risk() -> pd.DataFrame:
    return pd.DataFrame([{"avg_risk": 4.2}])


def _ccc_latest() -> pd.DataFrame:
    return pd.DataFrame([{"ccc": 48}])


def _ngn_rate_db() -> pd.DataFrame:
    return pd.DataFrame([{"rate_to_usd": 1580.0}])


def _supplier_risk_ranking() -> pd.DataFrame:
    scores = sorted(_RNG.uniform(2.0, 8.5, size=len(_SUPPLIERS)), reverse=True)
    return pd.DataFrame({
        "supplier_name": _SUPPLIERS,
        "composite_risk_score": scores,
    })


def _monthly_trend() -> pd.DataFrame:
    months = _monthly_dates(18)
    base = 600_000
    spend = [base + _RNG.normal(0, 60_000) + i * 12_000 for i in range(len(months))]
    return pd.DataFrame({"month": months, "spend_usd": spend})


def _currency_list() -> pd.DataFrame:
    return pd.DataFrame(_CURRENCIES)


def _fx_history(currency_id: int = 3) -> pd.DataFrame:
    """Generate realistic FX history for the given currency."""
    days = _daily_dates(365)
    start_rates = {1: 1.0, 2: 0.92, 3: 1450.0, 4: 0.79, 5: 7.25}
    base = start_rates.get(currency_id, 100.0)
    rates = [base]
    for _ in range(len(days) - 1):
        shock = _RNG.normal(0, base * 0.003)
        rates.append(max(rates[-1] + shock, base * 0.85))
    return pd.DataFrame({"rate_date": days, "rate_to_usd": rates})


def _supplier_performance() -> pd.DataFrame:
    n = len(_SUPPLIERS)
    return pd.DataFrame({
        "supplier_name": _SUPPLIERS,
        "avg_lead_time": _RNG.uniform(5, 30, n).round(1),
        "lead_time_stddev": _RNG.uniform(1, 8, n).round(2),
        "avg_defect_rate": _RNG.uniform(0.5, 6.0, n).round(2),
        "cost_variance_pct": _RNG.uniform(-5, 15, n).round(2),
        "on_time_delivery_pct": _RNG.uniform(70, 99, n).round(1),
        "fx_exposure_pct": _RNG.uniform(0, 60, n).round(1),
        "composite_risk_score": sorted(_RNG.uniform(2.0, 8.5, n), reverse=True),
    })


def _spend_by_supplier() -> pd.DataFrame:
    spends = _RNG.uniform(300_000, 2_500_000, len(_SUPPLIERS))
    return pd.DataFrame({
        "supplier_name": _SUPPLIERS,
        "spend_usd": spends.round(2),
    }).sort_values("spend_usd", ascending=False)


def _spend_by_category() -> pd.DataFrame:
    spends = _RNG.uniform(200_000, 3_000_000, len(_CATEGORIES))
    return pd.DataFrame({
        "category": _CATEGORIES,
        "spend_usd": spends.round(2),
    }).sort_values("spend_usd", ascending=False)


def _cost_leakage() -> pd.DataFrame:
    leakage = _RNG.uniform(10_000, 350_000, len(_CATEGORIES))
    return pd.DataFrame({
        "category": _CATEGORIES,
        "leakage_usd": leakage.round(2),
    }).sort_values("leakage_usd", ascending=False)


def _annual_spend() -> pd.DataFrame:
    rows = []
    for year in [2023, 2024, 2025]:
        for s in _SUPPLIERS:
            rows.append({
                "supplier_name": s,
                "year": year,
                "total_spend_usd": round(_RNG.uniform(200_000, 2_000_000), 2),
            })
    return pd.DataFrame(rows)


def _inventory_trend() -> pd.DataFrame:
    dates = _daily_dates(180)
    base = 3_200_000
    values = [base + _RNG.normal(0, 80_000) + i * 2_000 for i in range(len(dates))]
    return pd.DataFrame({"snapshot_date": dates, "total_inv": values})


def _payables_trend() -> pd.DataFrame:
    dates = _daily_dates(180)
    base = 1_800_000
    values = [base + _RNG.normal(0, 50_000) for _ in dates]
    return pd.DataFrame({"summary_date": dates, "accounts_payable_usd": values})


def _receivables_trend() -> pd.DataFrame:
    dates = _daily_dates(180)
    base = 1_200_000
    values = [base + _RNG.normal(0, 40_000) for _ in dates]
    return pd.DataFrame({"summary_date": dates, "accounts_receivable_usd": values})


def _financial_kpis() -> pd.DataFrame:
    return pd.DataFrame([{
        "kpi_date": datetime.today().date(),
        "dio": 42,
        "dpo": 35,
        "ccc": 48,
    }])


def _scenario_base_spend() -> pd.DataFrame:
    return pd.DataFrame([{
        "spend_usd": 12_450_890.50,
        "non_usd_spend": 4_656_633.37,
    }])


def _negotiation_insights() -> pd.DataFrame:
    """Same shape as supplier performance but limited to top 10."""
    return _supplier_performance().head(10)


def _table_health(table_name: str) -> pd.DataFrame:
    """Return a plausible row count for a given table."""
    counts = {
        "dim_date": 731,
        "dim_supplier": 10,
        "dim_material": 45,
        "fact_procurement": 2840,
        "supplier_performance_metrics": 10,
        "supplier_spend_summary": 30,
        "purchase_orders": 520,
        "purchase_order_items": 1560,
        "fx_rates": 1095,
        "quality_incidents": 85,
        "financial_kpis": 12,
    }
    cnt = counts.get(table_name, _RNG.randint(10, 500))
    return pd.DataFrame([{"cnt": cnt}])


# ── Public dispatcher ────────────────────────────────────────────────────────

def demo_query(sql: str) -> pd.DataFrame:
    """
    Pattern-match a SQL string and return an appropriate demo DataFrame.
    The matching is intentionally broad so minor query wording changes
    don't break it.
    """
    q = sql.lower().strip()

    # Health check: SELECT COUNT(*) FROM <table>
    if "count(*)" in q:
        for tbl in [
            "dim_date", "dim_supplier", "dim_material", "fact_procurement",
            "supplier_performance_metrics", "supplier_spend_summary",
            "purchase_orders", "purchase_order_items", "fx_rates",
            "quality_incidents", "financial_kpis",
        ]:
            if tbl in q:
                return _table_health(tbl)
        return pd.DataFrame([{"cnt": 100}])

    # Page 1 KPIs
    if "sum(total_usd_value)" in q and "fact_procurement" in q:
        return _total_spend()
    if "fx_pct" in q and "purchase_orders" in q:
        return _fx_exposure_pct()
    if "avg(composite_risk_score)" in q:
        return _avg_risk()
    if "financial_kpis" in q and "ccc" in q and "limit 1" in q and "dio" not in q:
        return _ccc_latest()

    # NGN rate fallback
    if "fx_rates" in q and "ngn" in q:
        return _ngn_rate_db()

    # Supplier risk ranking (top 10 by composite)
    if "composite_risk_score" in q and "limit 10" in q and "avg_lead_time" not in q:
        return _supplier_risk_ranking()

    # Monthly procurement trend
    if "date_format" in q and "fact_procurement" in q:
        return _monthly_trend()

    # Currency list
    if "currency_id" in q and "currency_code" in q and "fx_rates" in q and "distinct" in q:
        return _currency_list()

    # FX historical rates for a specific currency
    if "rate_to_usd" in q and "fx_rates" in q and "currency_id" in q:
        # Try to extract currency_id from query
        import re
        m = re.search(r"currency_id\s*=\s*(\d+)", q)
        cid = int(m.group(1)) if m else 3
        return _fx_history(cid)

    # Full supplier performance (risk analysis page)
    if "supplier_performance_metrics" in q and "avg_lead_time" in q:
        return _supplier_performance()

    # Spend by supplier
    if "fact_procurement" in q and "dim_supplier" in q:
        return _spend_by_supplier()

    # Spend by category
    if "fact_procurement" in q and "dim_material" in q:
        return _spend_by_category()

    # Cost leakage
    if "standard_cost" in q and "leakage" in q:
        return _cost_leakage()

    # Annual spend summary
    if "supplier_spend_summary" in q:
        return _annual_spend()

    # Inventory snapshots
    if "inventory_snapshots" in q:
        return _inventory_trend()

    # Payables
    if "payables_summary" in q:
        return _payables_trend()

    # Receivables
    if "receivables_summary" in q:
        return _receivables_trend()

    # Financial KPIs full row (DIO, DPO, CCC)
    if "financial_kpis" in q and ("dio" in q or "dpo" in q):
        return _financial_kpis()

    # Scenario planning base spend
    if "non_usd_spend" in q or ("purchase_orders" in q and "spend_usd" in q and "fx_rates" in q):
        return _scenario_base_spend()

    # Negotiation insights (top 10 risk suppliers with all metrics)
    if "composite_risk_score" in q and "limit 10" in q:
        return _negotiation_insights()

    # Default fallback
    return pd.DataFrame()
