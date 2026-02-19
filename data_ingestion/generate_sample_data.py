"""
Sample Data Generator for pro_intel_2
Generates realistic historical procurement data (24 months)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import random
from pathlib import Path
import sys
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATABASE_URL

np.random.seed(42)
random.seed(42)

engine = create_engine(DATABASE_URL)


def get_currency_map():
    currencies = pd.read_sql("SELECT currency_id, currency_code FROM currencies", engine)
    if currencies.empty:
        raise ValueError("No currencies found in currencies table")
    return {
        str(row["currency_code"]).upper(): int(row["currency_id"])
        for _, row in currencies.iterrows()
    }


def clear_transactional_tables():
    """Clear transactional tables in FK-safe order without dropping schemas."""
    print("Clearing transactional tables...")
    ordered_tables = [
        "quality_incidents",
        "purchase_order_items",
        "purchase_orders",
        "inventory_snapshots",
        "payables_summary",
        "receivables_summary",
        "fx_rates",
    ]
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ordered_tables:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()
    print("  ✓ Transactional tables cleared")


def generate_fx_rates():
    """
    Generate 24 months of FX rate data with realistic patterns.
    Simulates NGN devaluation and volatility.
    """
    print("Generating FX rate data...")
    
    dates = pd.date_range(start="2024-01-01", end="2025-12-31", freq='D')
    
    currency_map = get_currency_map()
    ngn_id = currency_map.get("NGN")
    eur_id = currency_map.get("EUR")
    gbp_id = currency_map.get("GBP")

    if not ngn_id:
        raise ValueError("NGN currency not found. Add NGN in currencies table.")

    fx_data = []
    fx_id = 1
    
    # NGN/USD with devaluation event
    base_rate_ngn = 460
    rates_ngn = [base_rate_ngn]
    
    for i in range(1, len(dates)):
        volatility = 0.015
        shock = np.random.normal(0, volatility)
        new_rate = rates_ngn[-1] * (1 + shock)
        
        # Simulate devaluation at day 180
        if i == 180:
            new_rate *= 1.35
        
        rates_ngn.append(new_rate)
    
    for i, date in enumerate(dates):
        # NGN rate_to_usd is recorded as NGN per 1 USD
        fx_data.append({
            'fx_id': fx_id,
            'currency_id': ngn_id,
            'rate_date': date.date(),
            'rate_to_usd': rates_ngn[i]
        })
        fx_id += 1
        
        if eur_id:
            eur_rate = 0.85 + np.random.normal(0, 0.01)
            fx_data.append({
                'fx_id': fx_id,
                'currency_id': eur_id,
                'rate_date': date.date(),
                'rate_to_usd': eur_rate
            })
            fx_id += 1
        
        if gbp_id:
            gbp_rate = 0.75 + np.random.normal(0, 0.01)
            fx_data.append({
                'fx_id': fx_id,
                'currency_id': gbp_id,
                'rate_date': date.date(),
                'rate_to_usd': gbp_rate
            })
            fx_id += 1
    
    fx_df = pd.DataFrame(fx_data)
    fx_df.to_sql('fx_rates', engine, if_exists='append', index=False)
    print(f"  ✓ Generated {len(fx_df)} FX rate records")
    print(f"  ✓ NGN rate convention: rate_to_usd = NGN per 1 USD")


def generate_purchase_orders():
    """
    Generate 24 months of purchase order data.
    """
    print("Generating purchase orders...")
    
    # Get existing suppliers, materials, currencies
    suppliers = pd.read_sql("SELECT supplier_id, default_currency_id, lead_time_days FROM suppliers", engine)
    materials = pd.read_sql("SELECT material_id, standard_cost FROM materials", engine)
    
    if suppliers.empty or materials.empty:
        print("  ⚠ Need suppliers and materials in database first")
        return
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    po_data = []
    po_items_data = []
    
    po_id = 1
    po_item_id = 1
    
    # Generate 10-15 POs per month for each supplier
    current_date = start_date
    
    while current_date <= end_date:
        for _, supplier in suppliers.iterrows():
            # Random number of POs this month per supplier
            num_pos = random.randint(8, 15)
            
            for _ in range(num_pos):
                order_date = current_date + timedelta(days=random.randint(0, 28))
                
                if order_date > end_date:
                    break
                
                lead_time = int(supplier['lead_time_days']) + random.randint(-5, 10)
                delivery_date = order_date + timedelta(days=max(lead_time, 1))
                payment_due_date = delivery_date + timedelta(days=random.choice([30, 45, 60]))
                
                status = random.choice(['Completed', 'Completed', 'Completed', 'In Progress', 'Cancelled'])
                
                po_data.append({
                    'po_id': po_id,
                    'supplier_id': int(supplier['supplier_id']),
                    'order_date': order_date.date(),
                    'delivery_date': delivery_date.date() if status != 'Cancelled' else None,
                    'payment_due_date': payment_due_date.date(),
                    'currency_id': int(supplier['default_currency_id']),
                    'status': status
                })
                
                # Generate 1-5 line items per PO
                num_items = random.randint(1, 5)
                selected_materials = materials.sample(n=min(num_items, len(materials)))
                
                for _, material in selected_materials.iterrows():
                    quantity = random.randint(1000, 15000)
                    # Price varies around standard cost
                    unit_price = float(material['standard_cost']) * random.uniform(0.8, 1.2)
                    
                    po_items_data.append({
                        'po_item_id': po_item_id,
                        'po_id': po_id,
                        'material_id': int(material['material_id']),
                        'quantity': quantity,
                        'unit_price': round(unit_price, 4)
                    })
                    po_item_id += 1
                
                po_id += 1
        
        # Move to next month
        current_date = (current_date + timedelta(days=32)).replace(day=1)
    
    po_df = pd.DataFrame(po_data)
    po_items_df = pd.DataFrame(po_items_data)
    
    po_df.to_sql('purchase_orders', engine, if_exists='append', index=False)
    po_items_df.to_sql('purchase_order_items', engine, if_exists='append', index=False)
    
    print(f"  ✓ Generated {len(po_df)} purchase orders")
    print(f"  ✓ Generated {len(po_items_df)} purchase order items")


def generate_quality_incidents():
    """
    Generate quality incident data correlated with suppliers.
    """
    print("Generating quality incidents...")
    
    # Get POs and items
    query = """
    SELECT po.po_id, po.supplier_id, po.delivery_date, poi.material_id
    FROM purchase_orders po
    JOIN purchase_order_items poi ON po.po_id = poi.po_id
    WHERE po.status = 'Completed' AND po.delivery_date IS NOT NULL
    """
    
    po_data = pd.read_sql(query, engine)
    
    if po_data.empty:
        print("  ⚠ No completed POs available")
        return
    
    # Sample 5-10% of deliveries have quality incidents
    sample_size = int(len(po_data) * random.uniform(0.05, 0.10))
    incidents = po_data.sample(n=sample_size)
    
    incident_data = []
    incident_id = 1
    
    for _, row in incidents.iterrows():
        # Defect rate varies by supplier (simulate some suppliers being worse)
        base_defect_rate = random.uniform(0.001, 0.05)
        
        incident_data.append({
            'incident_id': incident_id,
            'supplier_id': int(row['supplier_id']),
            'material_id': int(row['material_id']),
            'defect_rate': round(base_defect_rate, 4),
            'incident_date': row['delivery_date']
        })
        incident_id += 1
    
    incidents_df = pd.DataFrame(incident_data)
    incidents_df.to_sql('quality_incidents', engine, if_exists='append', index=False)
    
    print(f"  ✓ Generated {len(incidents_df)} quality incident records")


def generate_inventory_snapshots():
    """
    Generate monthly inventory snapshots.
    """
    print("Generating inventory snapshots...")
    
    materials = pd.read_sql("SELECT material_id, standard_cost FROM materials", engine)
    
    if materials.empty:
        print("  ⚠ No materials available")
        return
    
    snapshot_data = []
    snapshot_id = 1
    
    # Monthly snapshots for 24 months
    dates = pd.date_range(start="2024-01-01", end="2025-12-31", freq='MS')
    
    for date in dates:
        for _, material in materials.iterrows():
            # Random inventory level
            quantity = random.randint(5000, 50000)
            inventory_value = quantity * float(material['standard_cost'])
            
            snapshot_data.append({
                'snapshot_id': snapshot_id,
                'material_id': int(material['material_id']),
                'snapshot_date': date.date(),
                'quantity_on_hand': quantity,
                'inventory_value_usd': round(inventory_value, 4)
            })
            snapshot_id += 1
    
    snapshots_df = pd.DataFrame(snapshot_data)
    snapshots_df.to_sql('inventory_snapshots', engine, if_exists='append', index=False)
    
    print(f"  ✓ Generated {len(snapshots_df)} inventory snapshot records")


def generate_financial_summaries():
    """
    Generate payables and receivables summaries.
    """
    print("Generating financial summaries...")
    
    dates = pd.date_range(start="2024-01-01", end="2025-12-31", freq='MS')
    
    payables_data = []
    receivables_data = []
    
    for date in dates:
        # Simulate growing payables/receivables
        base_payable = random.uniform(500000, 2000000)
        base_receivable = random.uniform(300000, 1500000)
        
        payables_data.append({
            'summary_date': date.date(),
            'accounts_payable_usd': round(base_payable, 4)
        })
        
        receivables_data.append({
            'summary_date': date.date(),
            'accounts_receivable_usd': round(base_receivable, 4)
        })
    
    payables_df = pd.DataFrame(payables_data)
    receivables_df = pd.DataFrame(receivables_data)
    
    payables_df.to_sql('payables_summary', engine, if_exists='append', index=False)
    receivables_df.to_sql('receivables_summary', engine, if_exists='append', index=False)
    
    print(f"  ✓ Generated {len(payables_df)} payables summary records")
    print(f"  ✓ Generated {len(receivables_df)} receivables summary records")


def main():
    """
    Generate all sample data.
    """
    print("="*60)
    print("Sample Data Generation for pro_intel_2")
    print("="*60)
    
    try:
        clear_transactional_tables()
        generate_fx_rates()
        generate_purchase_orders()
        generate_quality_incidents()
        generate_inventory_snapshots()
        generate_financial_summaries()
        
        print("\n" + "="*60)
        print("✓ Sample data generation completed!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run populate_warehouse.py to build dimensions and facts")
        print("2. Run advanced_analytics.py for FX simulation and risk metrics")
        
    except Exception as e:
        print(f"\n✗ Data generation failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
