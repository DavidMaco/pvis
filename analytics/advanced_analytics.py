"""
Advanced Analytics Module: FX Risk & Supplier Performance
Includes Monte Carlo FX simulation and composite risk scoring
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy import text
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)


def run_fx_simulation(currency_id=1, days=90, simulations=10000):
    fx_query = f"""
    SELECT rate_date, rate_to_usd
    FROM fx_rates
    WHERE currency_id = {currency_id}
    ORDER BY rate_date
    """

    fx_df = pd.read_sql(fx_query, engine)

    if fx_df.empty:
        raise ValueError(f"No FX data available for currency_id={currency_id}")

    fx_df['log_return'] = np.log(
        fx_df['rate_to_usd'] / fx_df['rate_to_usd'].shift(1)
    )
    fx_df = fx_df.dropna()

    mu = fx_df['log_return'].mean()
    sigma = fx_df['log_return'].std()
    current_rate = fx_df['rate_to_usd'].iloc[-1]

    dt = 1/252
    final_rates = []
    np.random.seed(42)

    for _ in range(simulations):
        rate = current_rate
        for _ in range(days):
            shock = np.random.normal(mu*dt, sigma*np.sqrt(dt))
            rate *= np.exp(shock)
        final_rates.append(rate)

    p5, p50, p95 = np.percentile(final_rates, [5, 50, 95])

    result = pd.DataFrame({
        "simulation_date": [datetime.today().date()],
        "currency_id": [currency_id],
        "forecast_days": [days],
        "current_rate": [current_rate],
        "p5_rate": [p5],
        "median_rate": [p50],
        "p95_rate": [p95],
        "simulations_count": [simulations]
    })

    result.to_sql("fx_simulation_results", engine, if_exists="append", index=False)
    return result


def run_supplier_risk():
    lead_query = """
    SELECT supplier_id,
           AVG(DATEDIFF(delivery_date, order_date)) AS avg_lead_time,
           STDDEV(DATEDIFF(delivery_date, order_date)) AS lead_time_stddev
    FROM purchase_orders
    WHERE delivery_date IS NOT NULL
    GROUP BY supplier_id
    """
    lead_df = pd.read_sql(lead_query, engine)
    if lead_df.empty:
        return

    quality_df = pd.read_sql("SELECT supplier_id, AVG(defect_rate) * 100 AS avg_defect_rate FROM quality_incidents GROUP BY supplier_id", engine)
    otd_df = pd.read_sql("SELECT supplier_id, (SUM(CASE WHEN delivery_date <= payment_due_date THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as on_time_delivery_pct FROM purchase_orders WHERE delivery_date IS NOT NULL AND payment_due_date IS NOT NULL GROUP BY supplier_id", engine)
    cost_df = pd.read_sql("SELECT po.supplier_id, (STDDEV(poi.unit_price) / AVG(poi.unit_price) * 100) as cost_variance_pct FROM purchase_orders po JOIN purchase_order_items poi ON po.po_id = poi.po_id GROUP BY po.supplier_id", engine)
    fx_df = pd.read_sql("SELECT po.supplier_id, (SUM(CASE WHEN cur.currency_code != 'USD' THEN poi.quantity * poi.unit_price ELSE 0 END) * 100.0 / NULLIF(SUM(poi.quantity * poi.unit_price), 0)) as fx_exposure_pct FROM purchase_orders po JOIN purchase_order_items poi ON po.po_id = poi.po_id JOIN currencies cur ON po.currency_id = cur.currency_id GROUP BY po.supplier_id", engine)

    df = lead_df.merge(quality_df, on='supplier_id', how='left')
    df = df.merge(otd_df, on='supplier_id', how='left')
    df = df.merge(cost_df, on='supplier_id', how='left')
    df = df.merge(fx_df, on='supplier_id', how='left')

    df['avg_defect_rate'] = df['avg_defect_rate'].fillna(0)
    df['on_time_delivery_pct'] = df['on_time_delivery_pct'].fillna(100)
    df['cost_variance_pct'] = df['cost_variance_pct'].fillna(0)
    df['fx_exposure_pct'] = df['fx_exposure_pct'].fillna(0)
    df['lead_time_stddev'] = df['lead_time_stddev'].fillna(0)

    df['norm_lead'] = ((df['avg_lead_time'] - df['avg_lead_time'].min()) /(df['avg_lead_time'].max() - df['avg_lead_time'].min() + 0.001))
    df['norm_defect'] = df['avg_defect_rate'] / 100
    df['norm_otd'] = 1 - (df['on_time_delivery_pct'] / 100)
    df['norm_variance'] = df['cost_variance_pct'] / 100
    df['norm_fx'] = df['fx_exposure_pct'] / 100

    df['composite_risk_score'] = (
        0.25 * df['norm_lead'] +
        0.30 * df['norm_defect'] +
        0.25 * df['norm_otd'] +
        0.10 * df['norm_variance'] +
        0.10 * df['norm_fx']
    ) * 100

    df['last_updated'] = datetime.now()

    final_df = df[['supplier_id', 'avg_lead_time', 'lead_time_stddev', 'avg_defect_rate', 'cost_variance_pct', 'on_time_delivery_pct', 'fx_exposure_pct', 'composite_risk_score', 'last_updated']]

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM supplier_performance_metrics"))
        conn.commit()

    final_df.to_sql("supplier_performance_metrics", engine, if_exists="append", index=False)


if __name__ == "__main__":
    run_fx_simulation(currency_id=1, days=90, simulations=10000)
    run_supplier_risk()
