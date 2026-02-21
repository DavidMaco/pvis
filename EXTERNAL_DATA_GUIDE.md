# PVIS External Data Import Guide

## Overview
PVIS can now operate in two modes:
- **Seed Mode** (default): Uses realistic generated data for demos/testing
- **External Mode**: Imports your company's actual procurement data

This guide explains how to prepare and import your company data.

---

## Quick Start

### Step 1: Prepare CSV Files
Create a directory with four CSV files following the specifications below.

### Step 2: Validate & Import
```powershell
cd procurement-intelligence-engine
python data_ingestion\external_data_loader.py --input-dir .\company_data
```

### Step 3: Populate Warehouse
```powershell
python data_ingestion\populate_warehouse.py
```

### Step 4: (Optional) Import FX Rates
If you have historical FX rates, place `fx_rates.csv` in the same directory.
Otherwise, the system generates realistic rates for analysis.

### Step 5: Launch Dashboard
```powershell
# Option A: Quick launcher (recommended)
.\RUN_STREAMLIT.ps1

# Option B: Manual launch
streamlit run streamlit_app.py
```

---

## CSV File Specifications

### 1. **suppliers.csv**

Required when importing company data.

#### Columns

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| **supplier_name** | Text | ✓ | Unique supplier identifier (e.g., "ABC Chemical Ltd") |
| **country** | Text | ✓ | Country name (e.g., "Germany", "China", "Nigeria") |
| **default_currency** | Text | ✓ | 3-letter currency code: USD, EUR, GBP, CNY, NGN |
| **lead_time_days** | Number | ✓ | Average delivery time in days (must be > 0) |
| **lead_time_stddev** | Number | ✗ | Lead time standard deviation (defaults to 20% of lead_time_days) |
| **defect_rate_pct** | Number | ✗ | Historical defect rate as % (0–100, defaults to 2.0) |

#### Example

```csv
supplier_name,country,default_currency,lead_time_days,lead_time_stddev,defect_rate_pct
"ABC Chemical Ltd",Germany,EUR,21,4,1.5
"Shanghai Rubber Co",China,CNY,30,6,3.2
"Lagos Petrochem",Nigeria,NGN,14,3,5.0
"Mumbai Steel Works",India,USD,25,5,2.1
```

**Country Mapping:**
Supported countries must already exist in the database. PVIS pre-loads:
- Nigeria, Germany, China, India, United States, United Kingdom, Brazil, South Africa

To add new countries, insert into the `countries` table directly.

---

### 2. **materials.csv**

Required when importing company data.

#### Columns

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| **material_name** | Text | ✓ | Unique material identifier (e.g., "HDPE Granules Grade A") |
| **category** | Text | ✓ | Material category (e.g., "Polymers", "Chemicals", "Metals") |
| **standard_cost** | Number | ✓ | Standard unit cost in USD (must be ≥ 0) |

#### Example

```csv
material_name,category,standard_cost
"PET Resin Grade A",Polymers,1.25
"HDPE Film 80 micron",Polymers,0.95
"Chromium Oxide",Chemicals,2.15
"Mild Steel Sheet",Metals,0.75
"Copper Wire 2mm",Metals,5.50
```

---

### 3. **purchase_orders.csv**

Required when importing company data.

#### Columns

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| **po_number** | Text | ✗ | Unique PO identifier (auto-generated if missing: PO-000001, PO-000002, ...) |
| **po_date** | Date | ✓ | Order date (format: YYYY-MM-DD, e.g., 2024-01-15) |
| **supplier_name** | Text | ✓ | Must match a supplier from suppliers.csv |
| **currency** | Text | ✓ | 3-letter code: USD, EUR, GBP, CNY, NGN |
| **total_value** | Number | ✓ | Total PO value (must be ≥ 0) |
| **delivery_status** | Text | ✗ | One of: DELIVERED, PENDING, CANCELLED (defaults to DELIVERED) |

#### Example

```csv
po_number,po_date,supplier_name,currency,total_value,delivery_status
PO-2024-0001,2024-01-10,"ABC Chemical Ltd",EUR,15000.00,DELIVERED
PO-2024-0002,2024-01-12,"Shanghai Rubber Co",CNY,22500.50,DELIVERED
PO-2024-0003,2024-02-01,"Lagos Petrochem",NGN,5000000.00,PENDING
PO-2024-0004,2024-02-05,"Mumbai Steel Works",USD,18750.25,DELIVERED
```

**Date Format:** ISO 8601 (YYYY-MM-DD)
**Status Options:** DELIVERED, PENDING, CANCELLED

---

### 4. **purchase_order_items.csv**

Required when importing company data. Links POs to materials.

#### Columns

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| **po_number** | Text | ✓ | Must match a po_number from purchase_orders.csv |
| **material_name** | Text | ✓ | Must match a material_name from materials.csv |
| **quantity** | Number | ✓ | Line item quantity (must be > 0) |
| **unit_price** | Number | ✓ | Price per unit in the PO currency (must be ≥ 0) |

#### Example

```csv
po_number,material_name,quantity,unit_price
PO-2024-0001,"PET Resin Grade A",100,1.30
PO-2024-0001,"HDPE Film 80 micron",50,1.00
PO-2024-0002,"Chromium Oxide",200,2.20
PO-2024-0003,"Mild Steel Sheet",1000,0.78
PO-2024-0004,"Copper Wire 2mm",500,5.75
```

---

### 5. **fx_rates.csv** (Optional)

Historical FX rates. If omitted, the system generates realistic rates.

#### Columns

| Column | Type | Required | Notes |
|--------|------|----------|-------|
| **rate_date** | Date | ✓ | Date of FX rate (format: YYYY-MM-DD) |
| **currency_code** | Text | ✓ | 3-letter code: EUR, GBP, CNY, NGN (not USD) |
| **rate_to_usd** | Number | ✓ | Units of currency per 1 USD (must be > 0) |

#### Example

```csv
rate_date,currency_code,rate_to_usd
2024-01-01,EUR,0.92
2024-01-01,GBP,0.79
2024-01-01,CNY,6.84
2024-01-01,NGN,1300.00
2024-01-02,EUR,0.9205
2024-01-02,GBP,0.7895
2024-01-02,CNY,6.85
2024-01-02,NGN,1305.00
```

---

## Common Issues & Solutions

### "Missing required columns"
Check that your CSV has the exact column names (case-sensitive).

```csv
✓ CORRECT:  supplier_name
✗ WRONG:    Supplier Name, supplier_name_en, SupplierName
```

### "Country not found"
The country name must exist in the database. Use one of:
- Nigeria, Germany, China, India, United States, United Kingdom, Brazil, South Africa

To add custom countries, insert directly:
```sql
INSERT INTO countries (country_name) VALUES ('Australia');
```

### "supplier_name not found"
Ensure the supplier_name in purchase_orders.csv exactly matches suppliers.csv (case-sensitive, no extra spaces).

### "material_name not found"
Ensure the material_name in purchase_order_items.csv exactly matches materials.csv.

### "total_value mismatch"
If you provide both `total_value` in purchase_orders.csv and line items in purchase_order_items.csv, they may not match. The system uses your explicit `total_value` for reporting, so ensure accuracy.

---

## Data Validation Rules

PVIS enforces these rules during import:

1. **Suppliers**
   - lead_time_days must be > 0
   - default_currency must be a supported code
   - country must exist in the database

2. **Materials**
   - standard_cost must be ≥ 0
   - category is required (no empty categories)

3. **Purchase Orders**
   - po_date must be valid ISO date
   - total_value must be ≥ 0
   - supplier_name must exist in suppliers
   - currency must be a valid 3-letter code

4. **PO Items**
   - quantity must be > 0
   - unit_price must be ≥ 0
   - po_number must exist in purchase_orders
   - material_name must exist in materials

**Validation Mode:** LENIENT
- Type mismatches are warnings (not errors)
- Missing optional columns are handled with defaults
- Errors halt the import process

---

## Pipeline Behavior

After importing external data:

1. **Transaction Layer** (populated by external_data_loader.py):
   - suppliers
   - materials
   - purchase_orders
   - purchase_order_items

2. **Warehouse Layer** (populated by populate_warehouse.py):
   - dim_date (auto-generated)
   - dim_supplier (from suppliers)
   - dim_material (from materials)
   - fact_procurement (from POs + items)
   - supplier_spend_summary
   - supplier_performance_metrics
   - financial_kpis

3. **Analytics Layer** (run via Streamlit Pipeline Runner):
   - fx_simulation_results (Monte Carlo)
   - supplier_risk_scores

---

## Performance Notes

- **Scale:** PVIS is optimized for 8–200 suppliers, 50–1,000 materials, 500–20,000 POs
- **Date Range:** Recommended 1–5 years of historical data
- **FX Rates:** Should have records for all dates in your PO data

For large datasets (>100K POs), consider:
- Staging data in bulk-load format
- Running ETL in batches
- Enabling query caching

---

## Example: Complete Company Data Workflow

### Scenario: Import Q4 2024 procurement data for Acme Corp

**1. Prepare Files**
```
company_data\
  ├─ suppliers.csv        (20 suppliers)
  ├─ materials.csv        (150 materials)
  ├─ purchase_orders.csv  (5,000 POs from Q4 2024)
  ├─ purchase_order_items.csv  (12,000 line items)
  └─ fx_rates.csv         (daily rates Oct–Dec 2024)
```

**2. Import**
```powershell
python data_ingestion\external_data_loader.py --input-dir .\company_data
```
Output:
```
Loading external data from: ./company_data
Validating suppliers.csv... ✓
Validating materials.csv... ✓
Validating purchase_orders.csv... ✓
Validating purchase_order_items.csv... ✓

Importing data into database...
  ✓ Imported 20 suppliers
  ✓ Imported 150 materials
  ✓ Imported 5000 purchase orders
  ✓ Imported 12000 purchase order items

✓ External data imported successfully!
```

**3. Populate Warehouse**
```powershell
python data_ingestion\populate_warehouse.py
```

**4. Launch & Analyze**
```powershell
streamlit run streamlit_app.py
```

Navigate to:
- **Executive Summary** → See spend trends
- **FX Volatility & Monte Carlo** → Analyze exposure to EUR/GBP/CNY/NGN
- **Supplier Risk Analysis** → Review performance of all 20 suppliers
- **Spend & Cost Analysis** → Cost leakage by category
- **Working Capital** → Cash conversion cycle optimization

---

## Support

For issues or questions:
1. Check the **Common Issues & Solutions** section above
2. Review the validation error messages during import
3. Consult the database schema in `schema.sql`
4. Check the import logs in `data_ingestion/external_data_loader.py`
