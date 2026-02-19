import pymysql

conn = pymysql.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='Maconoelle86',
    database='pro_intel_2'
)

cur = conn.cursor()

print("\n" + "="*70)
print("DATABASE VERIFICATION STATUS")
print("="*70)

tables_to_check = [
    'dim_date',
    'dim_supplier', 
    'dim_material',
    'fact_procurement',
    'supplier_performance_metrics',
    'supplier_spend_summary',
    'fx_simulation_results',
    'purchase_orders',
    'purchase_order_items',
    'fx_rates',
    'quality_incidents'
]

for table in tables_to_check:
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cur.fetchone()[0]
        status = "✓" if count > 0 else "✗ EMPTY"
        print(f"{status:8} {table:40} {count:>8,} rows")
    except Exception as e:
        print(f"✗ ERROR {table:40} {str(e)[:30]}")

print("="*70)

# Check constraints
print("\nFOREIGN KEY CONSTRAINTS:")
cur.execute("""
    SELECT COUNT(*) as fk_count 
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
    WHERE TABLE_SCHEMA = 'pro_intel_2' 
    AND REFERENCED_TABLE_NAME IS NOT NULL
""")
fk_count = cur.fetchone()[0]
print(f"Foreign Keys: {fk_count}")

# Check indexes
cur.execute("""
    SELECT COUNT(DISTINCT INDEX_NAME) as idx_count
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = 'pro_intel_2'
    AND INDEX_NAME != 'PRIMARY'
""")
idx_count = cur.fetchone()[0]
print(f"Indexes: {idx_count}")

print("="*70)

conn.close()
print("\n✓ Verification complete!\n")
