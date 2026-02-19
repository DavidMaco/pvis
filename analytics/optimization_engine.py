"""
PVIS Optimization Engine
Builds scenario planning, working capital restructuring, and negotiation insight outputs.
"""

from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)


def _get_ngn_currency_id():
    result = pd.read_sql(
        "SELECT currency_id FROM currencies WHERE UPPER(currency_code)='NGN' LIMIT 1",
        engine,
    )
    if result.empty:
        raise ValueError("NGN currency code missing in currencies table")
    return int(result.iloc[0]["currency_id"])


def build_fx_exposure_mapping():
    query = """
    SELECT
        s.supplier_id,
        s.supplier_name,
        cur.currency_code,
        SUM(poi.quantity * poi.unit_price) AS total_local_spend,
        SUM((poi.quantity * poi.unit_price) /
            COALESCE(fx.rate_to_usd, 1)) AS total_spend_usd
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    JOIN suppliers s ON po.supplier_id = s.supplier_id
    JOIN currencies cur ON po.currency_id = cur.currency_id
    LEFT JOIN fx_rates fx
      ON po.currency_id = fx.currency_id
     AND fx.rate_date = (
       SELECT MAX(rate_date)
       FROM fx_rates f2
       WHERE f2.currency_id = po.currency_id
         AND f2.rate_date <= po.order_date
     )
    GROUP BY s.supplier_id, s.supplier_name, cur.currency_code
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    total_usd = df["total_spend_usd"].sum()
    df["fx_exposure_pct"] = (df["total_spend_usd"] / total_usd * 100).round(2)
    df["last_updated"] = datetime.now()

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS fx_exposure_mapping"))
        conn.commit()
    df.to_sql("fx_exposure_mapping", engine, if_exists="replace", index=False)
    return df


def build_scenario_planning():
    base_query = """
    SELECT
        SUM((poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)) AS spend_usd,
        SUM(CASE WHEN cur.currency_code != 'USD' THEN (poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1) ELSE 0 END) AS non_usd_spend_usd
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    JOIN currencies cur ON po.currency_id = cur.currency_id
    LEFT JOIN fx_rates fx
      ON po.currency_id = fx.currency_id
     AND fx.rate_date = (
       SELECT MAX(rate_date)
       FROM fx_rates f2
       WHERE f2.currency_id = po.currency_id
         AND f2.rate_date <= po.order_date
     )
    """
    base_df = pd.read_sql(base_query, engine)
    base_total = float(base_df.iloc[0]["spend_usd"] or 0)
    base_non_usd = float(base_df.iloc[0]["non_usd_spend_usd"] or 0)

    scenarios = [
        {"scenario": "Base", "fx_shock_pct": 0},
        {"scenario": "NGN Mild Devaluation", "fx_shock_pct": 10},
        {"scenario": "NGN Severe Devaluation", "fx_shock_pct": 20},
        {"scenario": "NGN Appreciation", "fx_shock_pct": -10},
    ]

    rows = []
    for s in scenarios:
        shock = s["fx_shock_pct"] / 100.0
        stressed_non_usd = base_non_usd * (1 + shock)
        stressed_total = (base_total - base_non_usd) + stressed_non_usd
        rows.append(
            {
                "scenario_name": s["scenario"],
                "fx_shock_pct": s["fx_shock_pct"],
                "baseline_spend_usd": round(base_total, 2),
                "stressed_spend_usd": round(stressed_total, 2),
                "landed_cost_impact_usd": round(stressed_total - base_total, 2),
                "created_at": datetime.now(),
            }
        )

    df = pd.DataFrame(rows)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS scenario_planning_output"))
        conn.commit()
    df.to_sql("scenario_planning_output", engine, if_exists="replace", index=False)
    return df


def build_working_capital_restructuring():
    kpi = pd.read_sql(
        "SELECT kpi_date, dio, dpo, ccc FROM financial_kpis ORDER BY kpi_date DESC LIMIT 1",
        engine,
    )
    if kpi.empty:
        return kpi

    row = kpi.iloc[0]
    dio = float(row["dio"])
    dpo = float(row["dpo"])
    ccc = float(row["ccc"])

    target_dio = max(dio * 0.9, 0)
    target_dpo = dpo * 1.1
    target_ccc = target_dio - target_dpo

    opportunity = pd.DataFrame(
        [
            {
                "analysis_date": datetime.now().date(),
                "current_dio": round(dio, 2),
                "current_dpo": round(dpo, 2),
                "current_ccc": round(ccc, 2),
                "target_dio": round(target_dio, 2),
                "target_dpo": round(target_dpo, 2),
                "target_ccc": round(target_ccc, 2),
                "ccc_improvement_days": round(ccc - target_ccc, 2),
            }
        ]
    )

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS working_capital_opportunities"))
        conn.commit()
    opportunity.to_sql("working_capital_opportunities", engine, if_exists="replace", index=False)
    return opportunity


def build_negotiation_insights():
    query = """
    SELECT
        s.supplier_name,
        spm.composite_risk_score,
        spm.avg_lead_time,
        spm.avg_defect_rate,
        spm.cost_variance_pct,
        spm.fx_exposure_pct
    FROM supplier_performance_metrics spm
    JOIN suppliers s ON spm.supplier_id = s.supplier_id
    ORDER BY spm.composite_risk_score DESC
    LIMIT 10
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df

    recommendations = []
    for _, r in df.iterrows():
        actions = []
        if r["avg_lead_time"] > df["avg_lead_time"].median():
            actions.append("Add lead-time SLA penalties")
        if r["avg_defect_rate"] > df["avg_defect_rate"].median():
            actions.append("Introduce quality rebate clause")
        if r["cost_variance_pct"] > df["cost_variance_pct"].median():
            actions.append("Lock indexed pricing corridor")
        if r["fx_exposure_pct"] > df["fx_exposure_pct"].median():
            actions.append("Shift contract currency / hedge exposure")
        if not actions:
            actions.append("Maintain terms and monitor quarterly")
        recommendations.append("; ".join(actions))

    df["negotiation_strategy"] = recommendations
    df["created_at"] = datetime.now()

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS negotiation_insights"))
        conn.commit()
    df.to_sql("negotiation_insights", engine, if_exists="replace", index=False)
    return df


def main():
    print("Running PVIS optimization engine...")
    build_fx_exposure_mapping()
    build_scenario_planning()
    build_working_capital_restructuring()
    build_negotiation_insights()
    print("✓ PVIS optimization outputs generated")


if __name__ == "__main__":
    main()
