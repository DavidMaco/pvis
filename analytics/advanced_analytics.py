"""
Advanced Analytics Module: FX Risk & Supplier Performance
Includes Monte Carlo FX simulation and composite risk scoring
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime

# =========================
# 1. DATABASE CONNECTION
# =========================

engine = create_engine(
    "mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2"
)

# =========================
# 2. FX MONTE CARLO MODULE
# =========================

def run_fx_simulation(currency_id=1, days=90, simulations=10000):
    """
    Run Monte Carlo simulation for FX rate forecasting.
    
    Parameters:
    -----------
    currency_id : int
        Currency to simulate (default 1 for NGN)
    days : int
        Forecast horizon in days
    simulations : int
        Number of Monte Carlo paths
    """
    
    fx_query = f"""
    SELECT rate_date, rate_to_usd
    FROM fx_rates
    WHERE currency_id = {currency_id}
    ORDER BY rate_date
    """

    fx_df = pd.read_sql(fx_query, engine)

    if fx_df.empty:
        raise ValueError(f"No FX data available for currency_id={currency_id}")

    # Calculate log returns
    fx_df['log_return'] = np.log(
        fx_df['rate_to_usd'] / fx_df['rate_to_usd'].shift(1)
    )

    fx_df = fx_df.dropna()

    # Historical volatility and drift
    mu = fx_df['log_return'].mean()
    sigma = fx_df['log_return'].std()
    current_rate = fx_df['rate_to_usd'].iloc[-1]

    print(f"FX Simulation Parameters:")
    print(f"  Currency ID: {currency_id}")
    print(f"  Current Rate: {current_rate:.6f}")
    print(f"  Historical Drift (μ): {mu:.6f}")
    print(f"  Historical Volatility (σ): {sigma:.6f}")

    # Monte Carlo simulation
    dt = 1/252  # Daily time step (252 trading days)
    final_rates = []

    np.random.seed(42)  # For reproducibility
    
    for _ in range(simulations):
        rate = current_rate
        for _ in range(days):
            shock = np.random.normal(mu*dt, sigma*np.sqrt(dt))
            rate *= np.exp(shock)
        final_rates.append(rate)

    # Calculate percentiles
    p5, p50, p95 = np.percentile(final_rates, [5, 50, 95])

    print(f"\nForecast ({days} days ahead):")
    print(f"  5th Percentile (worst case): {p5:.6f}")
    print(f"  Median (50th percentile): {p50:.6f}")
    print(f"  95th Percentile (best case): {p95:.6f}")
    print(f"  Expected Change: {((p50 - current_rate) / current_rate * 100):.2f}%")

    # Prepare results
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

    # Store results (append to keep history)
    result.to_sql(
        "fx_simulation_results",
        engine,
        if_exists="append",
        index=False
    )
    
    print(f"✓ Simulation results stored in fx_simulation_results table")

    return result


# =========================
# 3. COMPOSITE RISK SCORE
# =========================

def run_supplier_risk():
    """
    Calculate comprehensive supplier risk metrics.
    Writes all required columns to supplier_performance_metrics table.
    """
    
    print("\nCalculating Supplier Risk Metrics...")

    # Lead time metrics
    lead_query = """
    SELECT 
        supplier_id,
        AVG(DATEDIFF(delivery_date, order_date)) AS avg_lead_time,
        STDDEV(DATEDIFF(delivery_date, order_date)) AS lead_time_stddev
    FROM purchase_orders
    WHERE delivery_date IS NOT NULL
    GROUP BY supplier_id
    """

    lead_df = pd.read_sql(lead_query, engine)

    if lead_df.empty:
        print("⚠ No lead time data available")
        return

    # Quality metrics (defect rates)
    quality_query = """
    SELECT 
        supplier_id,
        AVG(defect_rate) * 100 AS avg_defect_rate
    FROM quality_incidents
    GROUP BY supplier_id
    """

    quality_df = pd.read_sql(quality_query, engine)

    # On-time delivery
    otd_query = """
    SELECT 
        supplier_id,
        (SUM(CASE WHEN delivery_date <= payment_due_date THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as on_time_delivery_pct
    FROM purchase_orders
    WHERE delivery_date IS NOT NULL AND payment_due_date IS NOT NULL
    GROUP BY supplier_id
    """

    otd_df = pd.read_sql(otd_query, engine)

    # Cost variance
    cost_query = """
    SELECT 
        po.supplier_id,
        (STDDEV(poi.unit_price) / AVG(poi.unit_price) * 100) as cost_variance_pct
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    GROUP BY po.supplier_id
    """

    cost_df = pd.read_sql(cost_query, engine)

    # FX exposure
    fx_query = """
    SELECT 
        po.supplier_id,
        (SUM(CASE WHEN cur.currency_code != 'USD' THEN poi.quantity * poi.unit_price ELSE 0 END) * 100.0 / 
         NULLIF(SUM(poi.quantity * poi.unit_price), 0)) as fx_exposure_pct
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    JOIN currencies cur ON po.currency_id = cur.currency_id
    GROUP BY po.supplier_id
    """

    fx_df = pd.read_sql(fx_query, engine)

    # Merge all metrics
    df = lead_df.merge(quality_df, on='supplier_id', how='left')
    df = df.merge(otd_df, on='supplier_id', how='left')
    df = df.merge(cost_df, on='supplier_id', how='left')
    df = df.merge(fx_df, on='supplier_id', how='left')

    # Fill nulls with defaults
    df['avg_defect_rate'] = df['avg_defect_rate'].fillna(0)
    df['on_time_delivery_pct'] = df['on_time_delivery_pct'].fillna(100)
    df['cost_variance_pct'] = df['cost_variance_pct'].fillna(0)
    df['fx_exposure_pct'] = df['fx_exposure_pct'].fillna(0)
    df['lead_time_stddev'] = df['lead_time_stddev'].fillna(0)

    # Normalize metrics for risk scoring
    df['norm_lead'] = (
        (df['avg_lead_time'] - df['avg_lead_time'].min()) /
        (df['avg_lead_time'].max() - df['avg_lead_time'].min() + 0.001)
    )

    df['norm_defect'] = df['avg_defect_rate'] / 100
    df['norm_otd'] = 1 - (df['on_time_delivery_pct'] / 100)
    df['norm_variance'] = df['cost_variance_pct'] / 100
    df['norm_fx'] = df['fx_exposure_pct'] / 100

    # Composite risk score (weighted)
    df['composite_risk_score'] = (
        0.25 * df['norm_lead'] +      # Lead time consistency
        0.30 * df['norm_defect'] +    # Quality issues
        0.25 * df['norm_otd'] +       # Delivery reliability
        0.10 * df['norm_variance'] +  # Price stability
        0.10 * df['norm_fx']          # FX exposure
    ) * 100

    # Add timestamp
    df['last_updated'] = datetime.now()

    # Select columns matching schema
    final_df = df[[
        'supplier_id', 
        'avg_lead_time', 
        'lead_time_stddev',
        'avg_defect_rate', 
        'cost_variance_pct', 
        'on_time_delivery_pct',
        'fx_exposure_pct', 
        'composite_risk_score',
        'last_updated'
    ]]

    # Write to database (replace existing)
    final_df.to_sql(
        "supplier_performance_metrics",
        engine,
        if_exists="replace",
        index=False
    )

    print(f"✓ Updated {len(final_df)} supplier risk profiles")
    print(f"\nRisk Score Summary:")
    print(final_df[['supplier_id', 'composite_risk_score', 'avg_defect_rate', 'on_time_delivery_pct']].to_string(index=False))


# =========================
# MAIN PIPELINE
# =========================

if __name__ == "__main__":
    print("="*60)
    print("Advanced Analytics: FX Simulation & Supplier Risk")
    print("="*60)
    
    try:
        # Run FX Monte Carlo simulation (NGN = currency_id 3)
        run_fx_simulation(currency_id=3, days=90, simulations=10000)
        
        # Calculate supplier risk metrics
        run_supplier_risk()
        
        print("\n" + "="*60)
        print("✓ Analytics pipeline completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Analytics pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
