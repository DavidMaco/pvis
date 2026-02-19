"""
Generate PVIS visuals for executive reporting.
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


def generate_risk_heatmap():
    df = pd.read_sql("SELECT s.supplier_name, spm.avg_lead_time, spm.lead_time_stddev, spm.avg_defect_rate, spm.cost_variance_pct, spm.on_time_delivery_pct, spm.fx_exposure_pct, spm.composite_risk_score FROM supplier_performance_metrics spm JOIN suppliers s ON spm.supplier_id = s.supplier_id ORDER BY spm.composite_risk_score DESC", engine)
    metrics = ["avg_lead_time", "lead_time_stddev", "avg_defect_rate", "cost_variance_pct", "on_time_delivery_pct", "fx_exposure_pct", "composite_risk_score"]
    heat = df.set_index("supplier_name")[metrics]
    heat_norm = (heat - heat.min()) / (heat.max() - heat.min() + 1e-9)
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.6 * len(heat_norm))))
    im = ax.imshow(heat_norm.values, cmap="YlOrRd", aspect="auto")
    ax.set_yticks(range(len(heat_norm.index))); ax.set_yticklabels(heat_norm.index)
    ax.set_xticks(range(len(metrics))); ax.set_xticklabels(["Lead Time", "LT Volatility", "Defect %", "Cost Var %", "OTD %", "FX Exp %", "Composite"], rotation=30, ha="right")
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    ax.set_title("PVIS Risk Heatmap")
    _save(fig, "risk_heatmap.png")


def generate_fx_scenario_graphs(currency_id=1, days=90, simulations=5000):
    fx_df = pd.read_sql("SELECT rate_date, rate_to_usd FROM fx_rates WHERE currency_id = %s ORDER BY rate_date", engine, params=(currency_id,))
    fx_df["log_return"] = np.log(fx_df["rate_to_usd"] / fx_df["rate_to_usd"].shift(1))
    fx_df = fx_df.dropna()
    mu, sigma = fx_df["log_return"].mean(), fx_df["log_return"].std()
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
    p5, p50, p95 = np.percentile(paths, 5, axis=0), np.percentile(paths, 50, axis=0), np.percentile(paths, 95, axis=0)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.fill_between(range(days), p5, p95, color="#a3d5ff", alpha=0.6, label="5th-95th band")
    ax.plot(p50, color="#1d4f91", linewidth=2.0, label="Median")
    ax.legend(); ax.set_title("PVIS FX Scenario Band (90-Day Forecast)")
    _save(fig, "fx_scenario_band.png")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    final_rates = paths[:, -1]
    ax.hist(final_rates, bins=40, color="#2f7ed8", alpha=0.85)
    ax.set_title("Monte Carlo FX Distribution (Day 90)")
    _save(fig, "fx_distribution.png")


def generate_cost_leakage_breakdown():
    df = pd.read_sql("SELECT m.category, (poi.unit_price - m.standard_cost) * poi.quantity AS leakage_local FROM purchase_order_items poi JOIN materials m ON poi.material_id = m.material_id WHERE poi.unit_price > m.standard_cost", engine)
    grouped = df.groupby("category")["leakage_local"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    grouped.plot(kind="bar", color="#d95f02", ax=ax)
    ax.set_title("Cost Leakage Breakdown by Category")
    _save(fig, "cost_leakage_breakdown.png")


def generate_dashboard_blueprint():
    fig, ax = plt.subplots(figsize=(10.5, 6.5)); ax.set_axis_off()
    def box(x, y, w, h, label):
        rect = plt.Rectangle((x, y), w, h, fill=False, linewidth=1.2)
        ax.add_patch(rect); ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)
    ax.text(0.5, 0.95, "PVIS Executive Dashboard Blueprint", ha="center", fontsize=14, weight="bold")
    box(0.05, 0.78, 0.9, 0.12, "Executive KPIs: Spend | FX Exposure | Risk Index | CCC | 90-Day FX Band")
    box(0.05, 0.52, 0.42, 0.22, "Supplier Risk: Heatmap | Top 10 Risk")
    box(0.53, 0.52, 0.42, 0.22, "FX Volatility: Monte Carlo Curve | 5-95% Band")
    box(0.05, 0.24, 0.42, 0.22, "Working Capital: Inventory Trend | DPO vs DIO")
    box(0.53, 0.24, 0.42, 0.22, "Optimization Estimator | Cost Leakage")
    _save(fig, "dashboard_blueprint.png")


if __name__ == "__main__":
    generate_risk_heatmap()
    generate_fx_scenario_graphs()
    generate_cost_leakage_breakdown()
    generate_dashboard_blueprint()
    print(f"✓ PVIS visuals created in {OUTPUT_DIR}")
