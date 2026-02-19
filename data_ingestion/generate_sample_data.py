"""
Sample Data Generator for pro_intel_2
Generates realistic historical procurement data (24 months)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

np.random.seed(42)
random.seed(42)
engine = create_engine(DATABASE_URL)


def clear_transactional_tables():
    ordered_tables = [
        "quality_incidents", "purchase_order_items", "purchase_orders",
        "inventory_snapshots", "payables_summary", "receivables_summary", "fx_rates",
    ]
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ordered_tables:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()


def generate_fx_rates():
    dates = pd.date_range(start="2024-01-01", end="2025-12-31", freq='D')
    fx_data, fx_id = [], 1
    base_rate_ngn = 460
    rates_ngn = [base_rate_ngn]
    for i in range(1, len(dates)):
        shock = np.random.normal(0, 0.015)
        new_rate = rates_ngn[-1] * (1 + shock)
        if i == 180:
            new_rate *= 1.35
        rates_ngn.append(new_rate)
    for i, date in enumerate(dates):
        fx_data.append({'fx_id': fx_id, 'currency_id': 1, 'rate_date': date.date(), 'rate_to_usd': rates_ngn[i]}); fx_id += 1
        fx_data.append({'fx_id': fx_id, 'currency_id': 2, 'rate_date': date.date(), 'rate_to_usd': 0.85 + np.random.normal(0, 0.01)}); fx_id += 1
        fx_data.append({'fx_id': fx_id, 'currency_id': 3, 'rate_date': date.date(), 'rate_to_usd': 0.75 + np.random.normal(0, 0.01)}); fx_id += 1
    pd.DataFrame(fx_data).to_sql('fx_rates', engine, if_exists='append', index=False)


def generate_purchase_orders():
    suppliers = pd.read_sql("SELECT supplier_id, default_currency_id, lead_time_days FROM suppliers", engine)
    materials = pd.read_sql("SELECT material_id, standard_cost FROM materials", engine)
    if suppliers.empty or materials.empty:
        return
    start_date, end_date = datetime(2024, 1, 1), datetime(2025, 12, 31)
    po_data, po_items_data, po_id, po_item_id = [], [], 1, 1
    current_date = start_date
    while current_date <= end_date:
        for _, supplier in suppliers.iterrows():
            for _ in range(random.randint(8, 15)):
                order_date = current_date + timedelta(days=random.randint(0, 28))
                if order_date > end_date:
                    break
                lead_time = int(supplier['lead_time_days']) + random.randint(-5, 10)
                delivery_date = order_date + timedelta(days=max(lead_time, 1))
                payment_due_date = delivery_date + timedelta(days=random.choice([30, 45, 60]))
                status = random.choice(['Completed', 'Completed', 'Completed', 'In Progress', 'Cancelled'])
                po_data.append({'po_id': po_id, 'supplier_id': int(supplier['supplier_id']), 'order_date': order_date.date(), 'delivery_date': delivery_date.date() if status != 'Cancelled' else None, 'payment_due_date': payment_due_date.date(), 'currency_id': int(supplier['default_currency_id']), 'status': status})
                for _, material in materials.sample(n=min(random.randint(1, 5), len(materials))).iterrows():
                    po_items_data.append({'po_item_id': po_item_id, 'po_id': po_id, 'material_id': int(material['material_id']), 'quantity': random.randint(1000, 15000), 'unit_price': round(float(material['standard_cost']) * random.uniform(0.8, 1.2), 4)})
                    po_item_id += 1
                po_id += 1
        current_date = (current_date + timedelta(days=32)).replace(day=1)
    pd.DataFrame(po_data).to_sql('purchase_orders', engine, if_exists='append', index=False)
    pd.DataFrame(po_items_data).to_sql('purchase_order_items', engine, if_exists='append', index=False)


def generate_quality_incidents():
    query = """SELECT po.po_id, po.supplier_id, po.delivery_date, poi.material_id FROM purchase_orders po JOIN purchase_order_items poi ON po.po_id = poi.po_id WHERE po.status = 'Completed' AND po.delivery_date IS NOT NULL"""
    po_data = pd.read_sql(query, engine)
    if po_data.empty:
        return
    incidents = po_data.sample(n=int(len(po_data) * random.uniform(0.05, 0.10)))
    rows = []
    incident_id = 1
    for _, row in incidents.iterrows():
        rows.append({'incident_id': incident_id, 'supplier_id': int(row['supplier_id']), 'material_id': int(row['material_id']), 'defect_rate': round(random.uniform(0.001, 0.05), 4), 'incident_date': row['delivery_date']})
        incident_id += 1
    pd.DataFrame(rows).to_sql('quality_incidents', engine, if_exists='append', index=False)


def generate_inventory_snapshots():
    materials = pd.read_sql("SELECT material_id, standard_cost FROM materials", engine)
    if materials.empty:
        return
    rows, snapshot_id = [], 1
    for date in pd.date_range(start="2024-01-01", end="2025-12-31", freq='MS'):
        for _, material in materials.iterrows():
            qty = random.randint(5000, 50000)
            rows.append({'snapshot_id': snapshot_id, 'material_id': int(material['material_id']), 'snapshot_date': date.date(), 'quantity_on_hand': qty, 'inventory_value_usd': round(qty * float(material['standard_cost']), 4)})
            snapshot_id += 1
    pd.DataFrame(rows).to_sql('inventory_snapshots', engine, if_exists='append', index=False)


def generate_financial_summaries():
    payables, receivables = [], []
    for date in pd.date_range(start="2024-01-01", end="2025-12-31", freq='MS'):
        payables.append({'summary_date': date.date(), 'accounts_payable_usd': round(random.uniform(500000, 2000000), 4)})
        receivables.append({'summary_date': date.date(), 'accounts_receivable_usd': round(random.uniform(300000, 1500000), 4)})
    pd.DataFrame(payables).to_sql('payables_summary', engine, if_exists='append', index=False)
    pd.DataFrame(receivables).to_sql('receivables_summary', engine, if_exists='append', index=False)


if __name__ == "__main__":
    clear_transactional_tables()
    generate_fx_rates()
    generate_purchase_orders()
    generate_quality_incidents()
    generate_inventory_snapshots()
    generate_financial_summaries()
    print("✓ Sample data generation completed")
