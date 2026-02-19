"""
PVIS ETL Pipeline for dimensional model population.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)


def clear_warehouse_tables():
    ordered_tables = [
        'fact_procurement', 'supplier_spend_summary', 'supplier_performance_metrics',
        'financial_kpis', 'dim_supplier', 'dim_material', 'dim_date'
    ]
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ordered_tables:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()


def populate_dim_date(start_date='2023-01-01', end_date='2026-12-31'):
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    rows = []
    for date in dates:
        rows.append({'date_key': int(date.strftime('%Y%m%d')), 'full_date': date.date(), 'year': date.year, 'quarter': (date.month - 1) // 3 + 1, 'month': date.month, 'day': date.day})
    pd.DataFrame(rows).to_sql('dim_date', engine, if_exists='append', index=False)


def populate_dim_material():
    df = pd.read_sql("SELECT material_id, material_name, category FROM materials", engine)
    if df.empty:
        return
    df.insert(0, 'material_key', range(1, len(df) + 1))
    df.to_sql('dim_material', engine, if_exists='append', index=False)


def populate_dim_supplier():
    df = pd.read_sql("SELECT s.supplier_id, s.supplier_name, c.country_name, s.risk_index FROM suppliers s JOIN countries c ON s.country_id = c.country_id", engine)
    if df.empty:
        return
    df.insert(0, 'supplier_key', range(1, len(df) + 1))
    df.to_sql('dim_supplier', engine, if_exists='append', index=False)


def populate_fact_procurement():
    query = """
    SELECT poi.po_item_id, po.supplier_id, poi.material_id, po.order_date,
           poi.quantity, poi.unit_price, (poi.quantity * poi.unit_price) as total_local_value,
           po.currency_id, fx.rate_to_usd
    FROM purchase_order_items poi
    JOIN purchase_orders po ON poi.po_id = po.po_id
    LEFT JOIN fx_rates fx ON po.currency_id = fx.currency_id
      AND fx.rate_date = (
        SELECT MAX(rate_date) FROM fx_rates WHERE currency_id = po.currency_id AND rate_date <= po.order_date
      )
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return
    dim_supplier = pd.read_sql("SELECT supplier_key, supplier_id FROM dim_supplier", engine)
    dim_material = pd.read_sql("SELECT material_key, material_id FROM dim_material", engine)
    df = df.merge(dim_supplier, on='supplier_id', how='left').merge(dim_material, on='material_id', how='left')
    df['date_key'] = pd.to_datetime(df['order_date']).dt.strftime('%Y%m%d').astype(int)
    df['rate_to_usd'] = df['rate_to_usd'].fillna(1.0)
    df['total_usd_value'] = df['total_local_value'] / df['rate_to_usd']
    fact = df[['supplier_key', 'material_key', 'date_key', 'quantity', 'total_local_value', 'total_usd_value']].copy()
    fact.insert(0, 'fact_id', range(1, len(fact) + 1))
    fact.to_sql('fact_procurement', engine, if_exists='append', index=False)


def populate_supplier_spend_summary():
    df = pd.read_sql("SELECT s.supplier_id, YEAR(po.order_date) as year, SUM(poi.quantity * poi.unit_price) as total_local_spend FROM purchase_orders po JOIN purchase_order_items poi ON po.po_id = poi.po_id JOIN suppliers s ON po.supplier_id = s.supplier_id GROUP BY s.supplier_id, YEAR(po.order_date)", engine)
    if df.empty:
        return
    fx_df = pd.read_sql("SELECT s.supplier_id, YEAR(fx.rate_date) as year, AVG(fx.rate_to_usd) as avg_rate_to_usd FROM suppliers s JOIN fx_rates fx ON s.default_currency_id = fx.currency_id GROUP BY s.supplier_id, YEAR(fx.rate_date)", engine)
    df = df.merge(fx_df, on=['supplier_id', 'year'], how='left')
    df['avg_rate_to_usd'] = df['avg_rate_to_usd'].fillna(1.0)
    df['total_spend_usd'] = df['total_local_spend'] / df['avg_rate_to_usd']
    df[['supplier_id', 'year', 'total_spend_usd']].to_sql('supplier_spend_summary', engine, if_exists='append', index=False)


def populate_financial_kpis():
    inv = pd.read_sql("SELECT snapshot_date, AVG(inventory_value_usd) as avg_inventory_value FROM inventory_snapshots GROUP BY snapshot_date ORDER BY snapshot_date DESC LIMIT 1", engine)
    if inv.empty:
        return
    payables = pd.read_sql("SELECT accounts_payable_usd FROM payables_summary ORDER BY summary_date DESC LIMIT 1", engine)
    p = float(payables.iloc[0, 0]) if not payables.empty else 0
    avg_inventory = float(inv.iloc[0, 1])
    dio = avg_inventory
    dpo = p
    ccc = dio - dpo
    pd.DataFrame({'kpi_date': [datetime.now().date()], 'dio': [round(dio, 2)], 'dpo': [round(dpo, 2)], 'ccc': [round(ccc, 2)]}).to_sql('financial_kpis', engine, if_exists='append', index=False)


if __name__ == "__main__":
    clear_warehouse_tables()
    populate_dim_date()
    populate_dim_material()
    populate_dim_supplier()
    populate_fact_procurement()
    populate_supplier_spend_summary()
    populate_financial_kpis()
    print("✓ ETL pipeline completed")
