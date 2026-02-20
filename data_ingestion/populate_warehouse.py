"""
Comprehensive ETL Pipeline for pro_intel_2 Data Warehouse
Populates dimension and fact tables from transactional data
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import sys

DATABASE_URL = 'mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2'
engine = create_engine(DATABASE_URL)


def populate_dim_date(start_date='2023-01-01', end_date='2026-12-31'):
    """
    Populate dim_date dimension table with date hierarchy.
    """
    print("Populating dim_date...")
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    dim_date_data = []
    for date in dates:
        date_key = int(date.strftime('%Y%m%d'))
        dim_date_data.append({
            'date_key': date_key,
            'full_date': date.date(),
            'year': date.year,
            'quarter': (date.month - 1) // 3 + 1,
            'month': date.month,
            'day': date.day
        })
    
    df = pd.DataFrame(dim_date_data)
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM dim_date"))
        conn.commit()
    
    # Insert new data
    df.to_sql('dim_date', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(df)} date records")


def populate_dim_material():
    """
    Populate dim_material from materials table.
    """
    print("Populating dim_material...")
    
    query = """
    SELECT 
        material_id,
        material_name,
        category
    FROM materials
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("  ⚠ No materials found in source table")
        return
    
    # Add surrogate key
    df.insert(0, 'material_key', range(1, len(df) + 1))
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM dim_material"))
        conn.commit()
    
    # Insert dimension data
    df.to_sql('dim_material', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(df)} material records")


def populate_dim_supplier():
    """
    Populate dim_supplier from suppliers and countries tables.
    """
    print("Populating dim_supplier...")
    
    query = """
    SELECT 
        s.supplier_id,
        s.supplier_name,
        c.country_name,
        s.risk_index
    FROM suppliers s
    JOIN countries c ON s.country_id = c.country_id
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("  ⚠ No suppliers found in source table")
        return
    
    # Add surrogate key
    df.insert(0, 'supplier_key', range(1, len(df) + 1))
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM dim_supplier"))
        conn.commit()
    
    # Insert dimension data
    df.to_sql('dim_supplier', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(df)} supplier records")


def populate_fact_procurement():
    """
    Populate fact_procurement from purchase_orders and purchase_order_items.
    """
    print("Populating fact_procurement...")
    
    query = """
    SELECT 
        poi.po_item_id,
        po.supplier_id,
        poi.material_id,
        po.order_date,
        poi.quantity,
        poi.unit_price,
        (poi.quantity * poi.unit_price) as total_local_value,
        po.currency_id,
        fx.rate_to_usd
    FROM purchase_order_items poi
    JOIN purchase_orders po ON poi.po_id = po.po_id
    LEFT JOIN fx_rates fx ON po.currency_id = fx.currency_id 
        AND fx.rate_date = (
            SELECT MAX(rate_date) 
            FROM fx_rates 
            WHERE currency_id = po.currency_id 
            AND rate_date <= po.order_date
        )
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("  ⚠ No purchase order items found")
        return
    
    # Get dimension mappings
    dim_supplier = pd.read_sql("SELECT supplier_key, supplier_id FROM dim_supplier", engine)
    dim_material = pd.read_sql("SELECT material_key, material_id FROM dim_material", engine)
    
    # Merge to get surrogate keys
    df = df.merge(dim_supplier, on='supplier_id', how='left')
    df = df.merge(dim_material, on='material_id', how='left')
    
    # Create date_key
    df['date_key'] = pd.to_datetime(df['order_date']).dt.strftime('%Y%m%d').astype(int)
    
    # Calculate USD value
    df['rate_to_usd'] = df['rate_to_usd'].fillna(1.0)  # Default to 1 if no FX rate
    df['total_usd_value'] = df['total_local_value'] / df['rate_to_usd']
    
    # Prepare fact table data
    fact_data = df[[
        'supplier_key', 'material_key', 'date_key',
        'quantity', 'total_local_value', 'total_usd_value'
    ]].copy()
    
    # Add fact_id
    fact_data.insert(0, 'fact_id', range(1, len(fact_data) + 1))
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM fact_procurement"))
        conn.commit()
    
    # Insert fact data
    fact_data.to_sql('fact_procurement', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(fact_data)} procurement fact records")


def populate_supplier_spend_summary():
    """
    Calculate and populate supplier spend summary by year.
    """
    print("Populating supplier_spend_summary...")
    
    query = """
    SELECT 
        s.supplier_id,
        YEAR(po.order_date) as year,
        SUM(poi.quantity * poi.unit_price) as total_local_spend
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    JOIN suppliers s ON po.supplier_id = s.supplier_id
    GROUP BY s.supplier_id, YEAR(po.order_date)
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("  ⚠ No spend data available")
        return
    
    # Get average FX rate per year per supplier's default currency
    fx_query = """
    SELECT 
        s.supplier_id,
        YEAR(fx.rate_date) as year,
        AVG(fx.rate_to_usd) as avg_rate_to_usd
    FROM suppliers s
    JOIN fx_rates fx ON s.default_currency_id = fx.currency_id
    GROUP BY s.supplier_id, YEAR(fx.rate_date)
    """
    
    fx_df = pd.read_sql(fx_query, engine)
    
    # Merge and calculate USD spend
    df = df.merge(fx_df, on=['supplier_id', 'year'], how='left')
    df['avg_rate_to_usd'] = df['avg_rate_to_usd'].fillna(1.0)
    df['total_spend_usd'] = df['total_local_spend'] / df['avg_rate_to_usd']
    
    # Prepare summary data
    summary_data = df[['supplier_id', 'year', 'total_spend_usd']].copy()
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM supplier_spend_summary"))
        conn.commit()
    
    # Insert summary data
    summary_data.to_sql('supplier_spend_summary', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(summary_data)} spend summary records")


def populate_supplier_performance_metrics():
    """
    Calculate comprehensive supplier performance metrics.
    """
    print("Populating supplier_performance_metrics...")
    
    # Get lead time statistics
    lead_time_query = """
    SELECT 
        supplier_id,
        AVG(DATEDIFF(delivery_date, order_date)) as avg_lead_time,
        STDDEV(DATEDIFF(delivery_date, order_date)) as lead_time_stddev
    FROM purchase_orders
    WHERE delivery_date IS NOT NULL
    GROUP BY supplier_id
    """
    
    lead_time_df = pd.read_sql(lead_time_query, engine)
    
    # Get quality metrics
    quality_query = """
    SELECT 
        supplier_id,
        AVG(defect_rate) as avg_defect_rate
    FROM quality_incidents
    GROUP BY supplier_id
    """
    
    quality_df = pd.read_sql(quality_query, engine)
    
    # Get on-time delivery percentage
    otd_query = """
    SELECT 
        supplier_id,
        (SUM(CASE WHEN delivery_date <= payment_due_date THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as on_time_delivery_pct
    FROM purchase_orders
    WHERE delivery_date IS NOT NULL
    GROUP BY supplier_id
    """
    
    otd_df = pd.read_sql(otd_query, engine)
    
    # Get FX exposure (percentage of spend in non-USD currencies)
    fx_query = """
    SELECT 
        po.supplier_id,
        (SUM(CASE WHEN cur.currency_code != 'USD' THEN poi.quantity * poi.unit_price ELSE 0 END) * 100.0 / 
         SUM(poi.quantity * poi.unit_price)) as fx_exposure_pct
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    JOIN currencies cur ON po.currency_id = cur.currency_id
    GROUP BY po.supplier_id
    """
    
    fx_df = pd.read_sql(fx_query, engine)
    
    # Merge all metrics
    metrics_df = lead_time_df.merge(quality_df, on='supplier_id', how='left')
    metrics_df = metrics_df.merge(otd_df, on='supplier_id', how='left')
    metrics_df = metrics_df.merge(fx_df, on='supplier_id', how='left')
    
    # Fill missing values
    metrics_df['avg_defect_rate'] = metrics_df['avg_defect_rate'].fillna(0)
    metrics_df['on_time_delivery_pct'] = metrics_df['on_time_delivery_pct'].fillna(100)
    metrics_df['fx_exposure_pct'] = metrics_df['fx_exposure_pct'].fillna(0)
    metrics_df['lead_time_stddev'] = metrics_df['lead_time_stddev'].fillna(0)
    
    # Normalize metrics for composite risk score
    metrics_df['norm_lead_time'] = (metrics_df['avg_lead_time'] - metrics_df['avg_lead_time'].min()) / \
                                    (metrics_df['avg_lead_time'].max() - metrics_df['avg_lead_time'].min() + 0.001)
    
    metrics_df['norm_defect'] = metrics_df['avg_defect_rate']
    metrics_df['norm_otd'] = 1 - (metrics_df['on_time_delivery_pct'] / 100)
    metrics_df['norm_fx'] = metrics_df['fx_exposure_pct'] / 100
    
    # Calculate composite risk score (weighted average)
    metrics_df['composite_risk_score'] = (
        0.30 * metrics_df['norm_lead_time'] +
        0.35 * metrics_df['norm_defect'] +
        0.25 * metrics_df['norm_otd'] +
        0.10 * metrics_df['norm_fx']
    ) * 100
    
    # Calculate cost variance (simplified - stddev of unit prices)
    cost_query = """
    SELECT 
        po.supplier_id,
        (STDDEV(poi.unit_price) / AVG(poi.unit_price) * 100) as cost_variance_pct
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    GROUP BY po.supplier_id
    """
    
    cost_df = pd.read_sql(cost_query, engine)
    metrics_df = metrics_df.merge(cost_df, on='supplier_id', how='left')
    metrics_df['cost_variance_pct'] = metrics_df['cost_variance_pct'].fillna(0)
    
    # Prepare final data
    final_data = metrics_df[[
        'supplier_id', 'avg_lead_time', 'lead_time_stddev',
        'avg_defect_rate', 'cost_variance_pct', 'on_time_delivery_pct',
        'fx_exposure_pct', 'composite_risk_score'
    ]].copy()
    
    # Convert percentages to proper decimal format
    final_data['avg_defect_rate'] = (final_data['avg_defect_rate'] * 100).round(2)
    
    # Add timestamp
    final_data['last_updated'] = datetime.now()
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM supplier_performance_metrics"))
        conn.commit()
    
    # Insert metrics data
    final_data.to_sql('supplier_performance_metrics', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted {len(final_data)} performance metric records")


def populate_financial_kpis():
    """
    Calculate and populate financial KPIs (DIO, DPO, CCC).
    """
    print("Populating financial_kpis...")
    
    # Get inventory data
    inv_query = """
    SELECT 
        snapshot_date,
        AVG(inventory_value_usd) as avg_inventory_value
    FROM inventory_snapshots
    GROUP BY snapshot_date
    ORDER BY snapshot_date DESC
    LIMIT 1
    """
    
    inv_df = pd.read_sql(inv_query, engine)
    
    if inv_df.empty:
        print("  ⚠ No inventory data available, skipping financial KPIs")
        return
    
    # Get payables and receivables
    payables_query = "SELECT accounts_payable_usd FROM payables_summary ORDER BY summary_date DESC LIMIT 1"
    receivables_query = "SELECT accounts_receivable_usd FROM receivables_summary ORDER BY summary_date DESC LIMIT 1"
    
    try:
        payables = pd.read_sql(payables_query, engine).iloc[0, 0] if not pd.read_sql(payables_query, engine).empty else 0
        receivables = pd.read_sql(receivables_query, engine).iloc[0, 0] if not pd.read_sql(receivables_query, engine).empty else 0
    except:
        payables, receivables = 0, 0
    
    # Simplified KPI calculation
    avg_inventory = inv_df.iloc[0, 1] if not inv_df.empty else 0
    
    # Calculate KPIs (using approximations)
    dio = (avg_inventory / 365) * 365 if avg_inventory > 0 else 0  # Days Inventory Outstanding
    dpo = (payables / 365) * 365 if payables > 0 else 0  # Days Payable Outstanding
    ccc = dio - dpo  # Cash Conversion Cycle
    
    kpi_data = pd.DataFrame({
        'kpi_date': [datetime.now().date()],
        'dio': [round(dio, 2)],
        'dpo': [round(dpo, 2)],
        'ccc': [round(ccc, 2)]
    })
    
    # Clear existing data
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM financial_kpis"))
        conn.commit()
    
    # Insert KPI data
    kpi_data.to_sql('financial_kpis', engine, if_exists='append', index=False)
    print(f"  ✓ Inserted financial KPI record")


def main():
    """
    Execute full ETL pipeline.
    """
    print("="*60)
    print("Starting ETL Pipeline for pro_intel_2 Data Warehouse")
    print("="*60)
    
    try:
        # Disable FK checks for clean truncate-and-reload
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            conn.commit()

        # Populate dimensions first
        populate_dim_date()
        populate_dim_material()
        populate_dim_supplier()
        
        # Then populate facts
        populate_fact_procurement()
        
        # Populate aggregates
        populate_supplier_spend_summary()
        populate_supplier_performance_metrics()
        
        # Financial KPIs (if data available)
        populate_financial_kpis()

        # Re-enable FK checks
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        
        print("="*60)
        print("✓ ETL Pipeline completed successfully!")
        print("="*60)
        
    except Exception as e:
        # Re-enable FK checks even on failure
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            conn.commit()
        print(f"\n✗ ETL Pipeline failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
