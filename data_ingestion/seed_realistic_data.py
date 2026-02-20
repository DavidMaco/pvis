"""
Realistic Data Seed for pro_intel_2
====================================
Generates 3 years (Jan 2023 – Dec 2025) of procurement data across:
  • 8 suppliers  (diverse geographies & risk profiles)
  • 50 materials (5 categories)
  • ~800 POs with realistic line-items
  • Daily FX rates for 4 currencies (NGN, EUR, GBP, CNY)
  • Quality incidents (~7 % of deliveries)
  • Monthly inventory snapshots
  • Monthly payables / receivables summaries
  • GBP is added as a 4th operating currency

Run:  python data_ingestion/seed_realistic_data.py
Then: python data_ingestion/populate_warehouse.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from sqlalchemy import create_engine, text
import random, math, sys, os

# ── Reproducibility ──────────────────────────────────────────────────────────
np.random.seed(2024)
random.seed(2024)

# ── DB connection ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import DATABASE_URL
except Exception:
    DATABASE_URL = "mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2"

engine = create_engine(DATABASE_URL)

START = date(2023, 1, 1)
END   = date(2025, 12, 31)


def _safe_replace(df: pd.DataFrame, table: str):
    """to_sql with if_exists='replace' but disable FK checks first."""
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.commit()
    df.to_sql(table, engine, if_exists="replace", index=False)
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

# ═══════════════════════════════════════════════════════════════════════════════
#  REFERENCE DATA
# ═══════════════════════════════════════════════════════════════════════════════

COUNTRIES = [
    (1, "Nigeria"),
    (2, "Germany"),
    (3, "China"),
    (4, "India"),
    (5, "United States"),
    (6, "United Kingdom"),
    (7, "Brazil"),
    (8, "South Africa"),
]

CURRENCIES = [
    (1, "USD", "US Dollar"),
    (2, "EUR", "Euro"),
    (3, "NGN", "Nigerian Naira"),
    (4, "GBP", "British Pound"),
    (5, "CNY", "Chinese Yuan"),
]

SUPPLIERS = [
    # (id, name, country_id, default_currency_id, risk_index, lead_time_days)
    (1, "Lagos Polymers Ltd",        1, 3, 0.62, 14),
    (2, "Bavaria Chem GmbH",         2, 2, 0.30, 21),
    (3, "Shenzhen Industrial Co",    3, 5, 0.55, 30),
    (4, "Mumbai Steel & Alloys",     4, 1, 0.48, 25),
    (5, "Houston Petrochem Inc",     5, 1, 0.20, 10),
    (6, "Yorkshire Compounds Ltd",   6, 4, 0.35, 18),
    (7, "São Paulo Resinas SA",      7, 1, 0.58, 28),
    (8, "Johannesburg Mining Corp",  8, 1, 0.45, 22),
]

MATERIAL_CATEGORIES = {
    "Polymers": [
        "PET Resin", "HDPE Granules", "LDPE Film Grade", "Polypropylene Homo",
        "Polycarbonate Sheet", "Nylon-6 Chips", "PVC Compound", "ABS Pellets",
        "EVA Copolymer", "PMMA Beads",
    ],
    "Chemicals": [
        "Caustic Soda Flakes", "Sulfuric Acid (98%)", "Hydrogen Peroxide (35%)",
        "Sodium Carbonate", "Acetic Acid Glacial", "Ethylene Glycol",
        "Methanol Industrial", "Toluene Tech Grade", "Isopropanol 99%",
        "Citric Acid Anhydrous",
    ],
    "Metals & Alloys": [
        "Mild Steel Plate (6 mm)", "Stainless Steel 304 Coil",
        "Aluminium Ingot 99.7%", "Copper Cathode Grade A",
        "Galvanized Sheet (0.5 mm)", "Tin Plate T-1", "Zinc Ingot SHG",
        "Brass Rod CW614N", "Nickel 201 Strip", "Titanium Sponge",
    ],
    "Packaging": [
        "Corrugated Box (3-ply)", "Stretch Wrap 20μm", "PP Woven Sack 50 kg",
        "BOPP Laminate Film", "Glass Bottle 330 mL", "PET Bottle 500 mL",
        "Aluminium Can 330 mL", "Blister Pack PVC/Alu",
        "Kraft Paper 80 gsm", "Shrink Sleeve Label",
    ],
    "Electronics & Components": [
        "Ceramic Capacitor 0402", "SMD Resistor 0805", "DC Motor 24V 50W",
        "PCB FR-4 Double-Side", "Li-Ion Cell 18650",
        "OLED Display 1.3″", "Connector USB-C 24P",
        "Power MOSFET N-Ch", "Crystal Oscillator 16 MHz",
        "Thermal Paste 5 g",
    ],
}


def _build_materials():
    """Build 50 materials with realistic standard costs."""
    cost_ranges = {
        "Polymers":                (0.80,   3.50),
        "Chemicals":               (0.30,   2.20),
        "Metals & Alloys":         (1.50,  12.00),
        "Packaging":               (0.10,   1.80),
        "Electronics & Components":(0.05,  25.00),
    }
    rows = []
    mid = 1
    for cat, names in MATERIAL_CATEGORIES.items():
        lo, hi = cost_ranges[cat]
        for name in names:
            rows.append((mid, name, cat, round(random.uniform(lo, hi), 4)))
            mid += 1
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
#  FX RATE GENERATION (GBM with regime shifts)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_fx_rates():
    """
    Daily rates for NGN, EUR, GBP, CNY (all expressed as units per 1 USD).
    NGN undergoes two step-devaluations; EUR/GBP/CNY follow mean-reverting GBM.
    """
    print("  Generating FX rates …")
    dates = pd.date_range(START, END, freq="D")

    def gbm_series(start, mu, sigma, n, mean_revert=0.0, target=None):
        """Geometric Brownian Motion with optional mean reversion."""
        vals = [start]
        for _ in range(1, n):
            drift = mu
            if mean_revert and target:
                drift += mean_revert * (math.log(target) - math.log(vals[-1]))
            shock = np.random.normal(drift, sigma)
            vals.append(vals[-1] * math.exp(shock))
        return vals

    n = len(dates)

    # NGN: starts ~460, devalues to ~750 mid-2023, again to ~1 550 early-2024
    ngn = gbm_series(460, 0.0003, 0.012, n)
    for i, d in enumerate(dates):
        if d.date() == date(2023, 6, 14):
            ngn[i] *= 1.55           # Unification shock
        if d.date() == date(2024, 1, 29):
            ngn[i] *= 1.30           # Second devaluation
        if i > 0 and ngn[i] < ngn[i-1] * 0.5:
            ngn[i] = ngn[i-1]        # Guard against unrealistic dips
        if i > 0:
            # Carry forward shocks
            ngn[i] = max(ngn[i], ngn[i-1] * 0.97)

    # EUR per USD (~0.85–0.95, mild mean reversion)
    eur = gbm_series(0.92, 0, 0.004, n, mean_revert=0.03, target=0.91)

    # GBP per USD (~0.78–0.84)
    gbp = gbm_series(0.81, 0, 0.004, n, mean_revert=0.03, target=0.80)

    # CNY per USD (~7.0–7.35)
    cny = gbm_series(6.95, 0.0001, 0.003, n, mean_revert=0.02, target=7.15)

    rows = []
    fxid = 1
    for i, d in enumerate(dates):
        for cid, rate in [(3, ngn[i]), (2, eur[i]), (4, gbp[i]), (5, cny[i])]:
            rows.append({
                "fx_id":       fxid,
                "currency_id": cid,
                "rate_date":   d.date(),
                "rate_to_usd": round(rate, 6),
            })
            fxid += 1

    df = pd.DataFrame(rows)
    _safe_replace(df, "fx_rates")
    print(f"    ✓ {len(df):,} FX rate rows  ({len(dates)} days × 4 currencies)")
    return df


# ═══════════════════════════════════════════════════════════════════════════════
#  PURCHASE ORDERS  (~800 POs)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_purchase_orders(materials):
    """
    ~800 POs spread across 36 months and 8 suppliers.
    Each PO gets 1-4 line items from realistic material pools.
    """
    print("  Generating purchase orders …")
    supplier_map = {s[0]: s for s in SUPPLIERS}
    months = pd.date_range(START, END, freq="MS")
    target_total = 800
    per_month = max(1, target_total // len(months))  # ~22 per month

    po_rows, item_rows = [], []
    po_id = 1
    item_id = 1

    # Pre-assign material pools per supplier (each supplier focuses on 2-3 categories)
    cat_names = list(MATERIAL_CATEGORIES.keys())
    sup_cats = {}
    for s in SUPPLIERS:
        chosen = random.sample(cat_names, k=random.randint(2, 3))
        pool = [m for m in materials if m[2] in chosen]
        sup_cats[s[0]] = pool

    for month_start in months:
        month_end = (month_start + pd.offsets.MonthEnd(0)).date()
        n_pos = random.randint(per_month - 4, per_month + 4)

        for _ in range(n_pos):
            sid = random.choice([s[0] for s in SUPPLIERS])
            sup = supplier_map[sid]
            order_date = month_start.date() + timedelta(days=random.randint(0, 27))
            if order_date > END:
                continue

            lead = max(5, int(sup[5]) + random.randint(-5, 10))
            delivery_date = order_date + timedelta(days=lead)
            pay_terms = random.choice([30, 45, 60, 90])
            payment_due = delivery_date + timedelta(days=pay_terms)

            # Status distribution: 80% completed, 12% in-progress, 8% cancelled
            r = random.random()
            status = "Completed" if r < 0.80 else ("In Progress" if r < 0.92 else "Cancelled")

            po_rows.append({
                "po_id":           po_id,
                "supplier_id":     sid,
                "order_date":      order_date,
                "delivery_date":   delivery_date if status != "Cancelled" else None,
                "payment_due_date":payment_due,
                "currency_id":     sup[3],
                "status":          status,
            })

            # 1-4 line items
            pool = sup_cats.get(sid, materials)
            n_items = random.randint(1, 4)
            chosen_mats = random.sample(pool, k=min(n_items, len(pool)))
            for mat in chosen_mats:
                qty = random.randint(500, 20_000)
                std_cost = mat[3]
                # Unit price fluctuates ±25 % around standard cost
                unit_price = round(std_cost * random.uniform(0.75, 1.25), 4)
                item_rows.append({
                    "po_item_id":  item_id,
                    "po_id":       po_id,
                    "material_id": mat[0],
                    "quantity":    qty,
                    "unit_price":  unit_price,
                })
                item_id += 1

            po_id += 1

    po_df = pd.DataFrame(po_rows)
    items_df = pd.DataFrame(item_rows)

    _safe_replace(items_df, "purchase_order_items")
    _safe_replace(po_df, "purchase_orders")

    print(f"    ✓ {len(po_df):,} purchase orders")
    print(f"    ✓ {len(items_df):,} line items")
    return po_df, items_df


# ═══════════════════════════════════════════════════════════════════════════════
#  QUALITY INCIDENTS  (~7 % of completed deliveries)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_quality_incidents(po_df, items_df):
    """~7% of completed PO-items produce a quality incident."""
    print("  Generating quality incidents …")
    completed = po_df[po_df["status"] == "Completed"]
    completed_items = items_df[items_df["po_id"].isin(completed["po_id"])]
    merged = completed_items.merge(completed[["po_id", "supplier_id", "delivery_date"]], on="po_id")

    n_incidents = max(1, int(len(merged) * 0.07))
    sample = merged.sample(n=n_incidents)

    # Riskier suppliers get higher defect rates
    risk_map = {s[0]: s[4] for s in SUPPLIERS}  # supplier_id -> risk_index

    rows = []
    for idx, (_, r) in enumerate(sample.iterrows(), start=1):
        base = risk_map.get(r["supplier_id"], 0.5)
        defect_rate = round(np.clip(np.random.beta(2, 20) + base * 0.02, 0.001, 0.15), 4)
        rows.append({
            "incident_id":  idx,
            "supplier_id":  int(r["supplier_id"]),
            "material_id":  int(r["material_id"]),
            "defect_rate":  defect_rate,
            "incident_date": r["delivery_date"],
        })

    df = pd.DataFrame(rows)
    _safe_replace(df, "quality_incidents")
    print(f"    ✓ {len(df):,} quality incidents")


# ═══════════════════════════════════════════════════════════════════════════════
#  INVENTORY SNAPSHOTS  (monthly, per material)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_inventory_snapshots(materials):
    """Monthly inventory value snapshot for each of the 50 materials."""
    print("  Generating inventory snapshots …")
    months = pd.date_range(START, END, freq="MS")
    rows = []
    sid = 1
    for mat in materials:
        # Each material starts with a random stock level, then drifts
        qty = random.randint(5_000, 40_000)
        for m in months:
            # Seasonal adjustment (Q4 stock-build)
            season = 1.15 if m.month in (10, 11, 12) else 1.0
            qty = max(1_000, int(qty * random.uniform(0.85, 1.15) * season))
            val = round(qty * mat[3] * random.uniform(0.95, 1.05), 4)
            rows.append({
                "snapshot_id":       sid,
                "material_id":       mat[0],
                "snapshot_date":     m.date(),
                "quantity_on_hand":  qty,
                "inventory_value_usd": val,
            })
            sid += 1

    df = pd.DataFrame(rows)
    _safe_replace(df, "inventory_snapshots")
    print(f"    ✓ {len(df):,} inventory snapshots  ({len(materials)} materials × {len(months)} months)")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYABLES & RECEIVABLES SUMMARIES  (monthly)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_financial_summaries():
    """Monthly AP & AR with seasonal trends + growth."""
    print("  Generating payables / receivables …")
    months = pd.date_range(START, END, freq="MS")
    pay, rec = [], []
    ap_base = 1_200_000
    ar_base = 800_000

    for i, m in enumerate(months):
        # Slight uptrend + seasonal bump in Q4
        grow = 1 + i * 0.005
        season = 1.20 if m.month in (10, 11, 12) else (0.90 if m.month in (1, 2) else 1.0)
        ap = round(ap_base * grow * season * random.uniform(0.90, 1.10), 4)
        ar = round(ar_base * grow * season * random.uniform(0.85, 1.15), 4)
        pay.append({"summary_date": m.date(), "accounts_payable_usd": ap})
        rec.append({"summary_date": m.date(), "accounts_receivable_usd": ar})

    _safe_replace(pd.DataFrame(pay), "payables_summary")
    _safe_replace(pd.DataFrame(rec), "receivables_summary")
    print(f"    ✓ {len(pay)} payables + {len(rec)} receivables monthly records")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    banner = "Realistic Data Seed — pro_intel_2"
    print("=" * 60)
    print(banner)
    print("=" * 60)

    # 1. Reference data ────────────────────────────────────────────────────────
    print("\n[1/7] Seeding reference tables …")
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        conn.execute(text("DELETE FROM countries"))
        for cid, name in COUNTRIES:
            conn.execute(text("INSERT INTO countries (country_id, country_name) VALUES (:i, :n)"), {"i": cid, "n": name})

        conn.execute(text("DELETE FROM currencies"))
        for cid, code, name in CURRENCIES:
            conn.execute(text(
                "INSERT INTO currencies (currency_id, currency_code, currency_name) VALUES (:i, :c, :n)"
            ), {"i": cid, "c": code, "n": name})

        conn.execute(text("DELETE FROM suppliers"))
        for sid, name, ctry, cur, risk, lt in SUPPLIERS:
            conn.execute(text(
                "INSERT INTO suppliers (supplier_id, supplier_name, country_id, "
                "default_currency_id, risk_index, lead_time_days) "
                "VALUES (:sid,:name,:ctry,:cur,:risk,:lt)"
            ), {"sid": sid, "name": name, "ctry": ctry, "cur": cur, "risk": risk, "lt": lt})

        materials = _build_materials()
        conn.execute(text("DELETE FROM materials"))
        for mid, name, cat, cost in materials:
            conn.execute(text(
                "INSERT INTO materials (material_id, material_name, category, standard_cost) "
                "VALUES (:mid,:name,:cat,:cost)"
            ), {"mid": mid, "name": name, "cat": cat, "cost": cost})

        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()

    print(f"    ✓ {len(COUNTRIES)} countries, {len(CURRENCIES)} currencies, "
          f"{len(SUPPLIERS)} suppliers, {len(materials)} materials")

    # 2. FX rates ──────────────────────────────────────────────────────────────
    print("\n[2/7] FX rates …")
    _generate_fx_rates()

    # 3. Purchase orders ───────────────────────────────────────────────────────
    print("\n[3/7] Purchase orders …")
    po_df, items_df = _generate_purchase_orders(materials)

    # 4. Quality incidents ─────────────────────────────────────────────────────
    print("\n[4/7] Quality incidents …")
    _generate_quality_incidents(po_df, items_df)

    # 5. Inventory snapshots ───────────────────────────────────────────────────
    print("\n[5/7] Inventory snapshots …")
    _generate_inventory_snapshots(materials)

    # 6. Financial summaries ───────────────────────────────────────────────────
    print("\n[6/7] Financial summaries …")
    _generate_financial_summaries()

    # 7. Summary ───────────────────────────────────────────────────────────────
    print("\n[7/7] Verifying row counts …")
    with engine.connect() as conn:
        for tbl in [
            "countries", "currencies", "suppliers", "materials",
            "fx_rates", "purchase_orders", "purchase_order_items",
            "quality_incidents", "inventory_snapshots",
            "payables_summary", "receivables_summary",
        ]:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"    {tbl:40s} {cnt:>8,}")

    print("\n" + "=" * 60)
    print("✓ Seed complete!  Next steps:")
    print("  1. python data_ingestion/populate_warehouse.py")
    print("  2. python analytics/advanced_analytics.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
