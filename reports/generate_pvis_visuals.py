"""
Generate full PVIS visual pack for executive dashboard blueprint.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

OUTPUT_DIR = Path(__file__).resolve().parent / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL)


def _save(fig, name):
    path = OUTPUT_DIR / name
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


def generate_risk_heatmap():
    df = pd.read_sql(
        """
        SELECT s.supplier_name, spm.avg_lead_time, spm.lead_time_stddev,
               spm.avg_defect_rate, spm.cost_variance_pct,
               spm.on_time_delivery_pct, spm.fx_exposure_pct,
               spm.composite_risk_score
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.composite_risk_score DESC
        """,
        engine,
    )
    metrics = [
        "avg_lead_time", "lead_time_stddev", "avg_defect_rate",
        "cost_variance_pct", "on_time_delivery_pct", "fx_exposure_pct",
        "composite_risk_score",
    ]
    heat = df.set_index("supplier_name")[metrics]
    heat_norm = (heat - heat.min()) / (heat.max() - heat.min() + 1e-9)

    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.6 * len(heat_norm))))
    im = ax.imshow(heat_norm.values, cmap="YlOrRd", aspect="auto")
    ax.set_yticks(range(len(heat_norm.index)))
    ax.set_yticklabels(heat_norm.index)
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels([
        "Lead Time", "LT Volatility", "Defect %", "Cost Var %",
        "OTD %", "FX Exp %", "Composite"
    ], rotation=30, ha="right")
    ax.set_title("Risk Heatmap")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    return _save(fig, "risk_heatmap.png")


def generate_lead_time_volatility_chart():
    df = pd.read_sql(
        """
        SELECT s.supplier_name, spm.avg_lead_time, spm.lead_time_stddev
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.lead_time_stddev DESC
        """,
        engine,
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(df["supplier_name"], df["lead_time_stddev"], color="#3b82f6", label="Volatility")
    ax.plot(df["supplier_name"], df["avg_lead_time"], color="#ef4444", marker="o", label="Avg Lead Time")
    ax.set_title("Lead Time Volatility Chart")
    ax.set_ylabel("Days")
    ax.legend()
    return _save(fig, "lead_time_volatility.png")


def generate_cost_variance_table():
    df = pd.read_sql(
        """
        SELECT s.supplier_name, ROUND(spm.cost_variance_pct,2) AS cost_variance_pct,
               ROUND(spm.composite_risk_score,2) AS risk_score
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.cost_variance_pct DESC
        """,
        engine,
    )
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    ax.axis("off")
    table = ax.table(
        cellText=df.values,
        colLabels=["Supplier", "Cost Variance %", "Risk Score"],
        loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    ax.set_title("Cost Variance Table", pad=12)
    return _save(fig, "cost_variance_table.png")


def generate_top10_risk_suppliers():
    df = pd.read_sql(
        """
        SELECT s.supplier_name, spm.composite_risk_score
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.composite_risk_score DESC
        LIMIT 10
        """,
        engine,
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.barh(df["supplier_name"], df["composite_risk_score"], color="#f97316")
    ax.invert_yaxis()
    ax.set_title("Top 10 Risk Suppliers")
    ax.set_xlabel("Composite Supplier Risk Index")
    return _save(fig, "top10_risk_suppliers.png")


def generate_fx_scenario_graphs(currency_code="NGN", days=90, simulations=5000):
    currency = pd.read_sql(
        "SELECT currency_id FROM currencies WHERE UPPER(currency_code)=%s LIMIT 1",
        engine,
        params=(currency_code.upper(),),
    )
    if currency.empty:
        raise ValueError(f"Currency {currency_code} not found")
    currency_id = int(currency.iloc[0]["currency_id"])

    fx_df = pd.read_sql(
        "SELECT rate_date, rate_to_usd FROM fx_rates WHERE currency_id=%s ORDER BY rate_date",
        engine,
        params=(currency_id,),
    )

    fx_df["log_return"] = np.log(fx_df["rate_to_usd"] / fx_df["rate_to_usd"].shift(1))
    fx_df = fx_df.dropna()

    mu = fx_df["log_return"].mean()
    sigma = fx_df["log_return"].std()
    current_rate = fx_df["rate_to_usd"].iloc[-1]

    dt = 1 / 252
    np.random.seed(42)
    paths = np.zeros((simulations, days))

    for i in range(simulations):
        rate = current_rate
        for d in range(days):
            shock = np.random.normal(mu * dt, sigma * np.sqrt(dt))
            rate *= np.exp(shock)
            paths[i, d] = rate

    p5 = np.percentile(paths, 5, axis=0)
    p50 = np.percentile(paths, 50, axis=0)
    p95 = np.percentile(paths, 95, axis=0)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.fill_between(range(days), p5, p95, color="#a3d5ff", alpha=0.6, label="5th-95th percentile")
    ax.plot(p50, color="#1d4f91", linewidth=2.0, label="Median")
    ax.set_title(f"FX Scenario Graph ({currency_code} per 1 USD)")
    ax.set_xlabel("Days Ahead")
    ax.set_ylabel("FX Rate")
    ax.legend(loc="upper left")
    _save(fig, "fx_scenario_band.png")

    final_rates = paths[:, -1]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(final_rates, bins=40, color="#2f7ed8", alpha=0.85)
    ax.axvline(np.percentile(final_rates, 5), color="#b30000", linestyle="--", label="P5")
    ax.axvline(np.percentile(final_rates, 50), color="#1d4f91", linestyle="--", label="P50")
    ax.axvline(np.percentile(final_rates, 95), color="#2ca02c", linestyle="--", label="P95")
    ax.set_title("Monte Carlo Distribution Curve")
    ax.set_xlabel("FX Rate")
    ax.set_ylabel("Frequency")
    ax.legend()
    _save(fig, "fx_distribution.png")


def generate_landed_cost_stress_impact():
    df = pd.read_sql("SELECT scenario_name, landed_cost_impact_usd FROM scenario_planning_output", engine)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    colors = ["#ef4444" if x > 0 else "#10b981" for x in df["landed_cost_impact_usd"]]
    ax.bar(df["scenario_name"], df["landed_cost_impact_usd"], color=colors)
    ax.axhline(0, color="black", linewidth=1)
    ax.set_title("Landed Cost Stress Impact")
    ax.set_ylabel("Impact (USD)")
    return _save(fig, "landed_cost_stress_impact.png")


def generate_cost_leakage_breakdown():
    df = pd.read_sql(
        """
        SELECT m.category, (poi.unit_price - m.standard_cost) * poi.quantity AS leakage_local
        FROM purchase_order_items poi
        JOIN materials m ON poi.material_id = m.material_id
        WHERE poi.unit_price > m.standard_cost
        """,
        engine,
    )
    if df.empty:
        return None

    grouped = df.groupby("category")["leakage_local"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    grouped.plot(kind="bar", color="#d95f02", ax=ax)
    ax.set_title("Cost Leakage Breakdown")
    ax.set_xlabel("Category")
    ax.set_ylabel("Leakage (Local Currency)")
    return _save(fig, "cost_leakage_breakdown.png")


def generate_inventory_trend():
    df = pd.read_sql(
        """
        SELECT snapshot_date, SUM(inventory_value_usd) AS inventory_value_usd
        FROM inventory_snapshots
        GROUP BY snapshot_date
        ORDER BY snapshot_date
        """,
        engine,
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(pd.to_datetime(df["snapshot_date"]), df["inventory_value_usd"], color="#0ea5e9")
    ax.set_title("Inventory Trend")
    ax.set_ylabel("Inventory Value (USD)")
    return _save(fig, "inventory_trend.png")


def generate_dpo_vs_dio():
    df = pd.read_sql(
        """
        SELECT summary_date AS report_date,
               accounts_payable_usd AS dpo_proxy,
               (SELECT AVG(inventory_value_usd)
                FROM inventory_snapshots i
                WHERE i.snapshot_date <= p.summary_date) AS dio_proxy
        FROM payables_summary p
        ORDER BY summary_date
        """,
        engine,
    )
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(pd.to_datetime(df["report_date"]), df["dpo_proxy"], label="DPO Proxy", color="#7c3aed")
    ax.plot(pd.to_datetime(df["report_date"]), df["dio_proxy"], label="DIO Proxy", color="#f59e0b")
    ax.set_title("DPO vs DIO")
    ax.legend()
    return _save(fig, "dpo_vs_dio.png")


def generate_ccc_trend():
    wc = pd.read_sql("SELECT current_ccc, target_ccc, ccc_improvement_days, analysis_date FROM working_capital_opportunities", engine)
    if wc.empty:
        return None
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    values = [float(wc.iloc[0]["current_ccc"]), float(wc.iloc[0]["target_ccc"])]
    ax.bar(["Current CCC", "Target CCC"], values, color=["#ef4444", "#10b981"])
    ax.set_title("CCC Trend Over Time")
    ax.set_ylabel("CCC (days/proxy)")
    return _save(fig, "ccc_trend.png")


def generate_optimization_estimator():
    wc = pd.read_sql("SELECT ccc_improvement_days FROM working_capital_opportunities", engine)
    if wc.empty:
        return None
    improvement = float(wc.iloc[0]["ccc_improvement_days"])
    annual_spend = pd.read_sql("SELECT SUM(total_usd_value) AS spend FROM fact_procurement", engine).iloc[0]["spend"]
    annual_spend = float(annual_spend or 0)
    opportunity_usd = annual_spend * (improvement / 365.0)

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(["Estimated Working Capital Release"], [opportunity_usd], color="#22c55e")
    ax.set_title("Optimization Opportunity Estimator")
    ax.set_ylabel("USD")
    return _save(fig, "optimization_estimator.png")


def generate_dashboard_blueprint():
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.set_axis_off()

    def box(x, y, w, h, label):
        rect = plt.Rectangle((x, y), w, h, fill=False, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)

    ax.text(0.5, 0.96, "POWER BI EXECUTIVE DASHBOARD BLUEPRINT", ha="center", fontsize=13, weight="bold")

    box(0.04, 0.80, 0.92, 0.13, "Executive KPIs: Spend USD | FX Exposure % | Composite Risk | CCC | 90-Day FX Band")
    box(0.04, 0.54, 0.44, 0.22, "Supplier Risk: Heatmap | Lead Time Volatility | Cost Variance Table | Top 10 Risk")
    box(0.52, 0.54, 0.44, 0.22, "FX Forecast: Monte Carlo Distribution | 5th-95th Band | Landed Cost Stress")
    box(0.04, 0.26, 0.44, 0.22, "Working Capital: Inventory Trend | DPO vs DIO | CCC Trend")
    box(0.52, 0.26, 0.44, 0.22, "Optimization Estimator | Scenario Planning | Negotiation Insights")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    return _save(fig, "dashboard_blueprint.png")


def main():
    generate_risk_heatmap()
    generate_lead_time_volatility_chart()
    generate_cost_variance_table()
    generate_top10_risk_suppliers()
    generate_fx_scenario_graphs(currency_code="NGN")
    generate_landed_cost_stress_impact()
    generate_cost_leakage_breakdown()
    generate_inventory_trend()
    generate_dpo_vs_dio()
    generate_ccc_trend()
    generate_optimization_estimator()
    generate_dashboard_blueprint()
    print(f"✓ PVIS visual pack generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
