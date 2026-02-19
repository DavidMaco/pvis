# Pro_Intel_2 Database Setup & Execution Guide

## Overview
Complete setup instructions for the procurement intelligence data warehouse with Python analytics and Power BI integration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MySQL Database                        │
│                    (pro_intel_2)                         │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Transactional │  │  Dimensions  │  │    Facts    │ │
│  │     Tables     │  │   & Staging  │  │ & Aggregates│ │
│  └────────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌───────────────────────────┴─────────────────────────────┐
│              Python Analytics Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │     ETL      │  │  FX Simulation│  │   Supplier   │  │
│  │   Pipeline   │  │  Monte Carlo  │  │  Risk Scoring│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌───────────────────────────┴─────────────────────────────┐
│                    Power BI                              │
│              Dashboards & Reports                        │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Database Setup
- MySQL Server 8.0+ running on `localhost:3306`
- Database: `pro_intel_2` must exist
- User: `root` with password `Maconoelle86`
- All 18 tables created (see original schema)

### 2. Python Environment
```bash
cd "c:\Users\HP EliteBook\OneDrive\Documents\VSCode Projects"
python -m venv .venv
.venv\Scripts\activate
pip install pymysql sqlalchemy pandas numpy scikit-learn matplotlib plotly flask
```

### 3. Verify Database Connection
```bash
python -c "from sqlalchemy import create_engine; engine = create_engine('mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2'); print('✓ Connected to pro_intel_2')"
```

---

## Execution Sequence

### Step 1: Apply Database Constraints (One-time)
Adds foreign keys, check constraints, and performance indexes.

```bash
mysql -h 127.0.0.1 -P 3306 -u root -pMaconoelle86 pro_intel_2 < database/add_constraints_migration.sql
```

**What it does:**
- ✓ Enforces referential integrity between tables
- ✓ Adds data validation rules (e.g., defect_rate must be 0-1)
- ✓ Creates composite indexes for analytical queries
- ✓ Creates `fx_simulation_results` table

---

### Step 2: Generate Sample Data (Optional but Recommended)
Creates 24 months of realistic historical procurement data.

```bash
cd procurement-intelligence-engine
python data_ingestion/generate_sample_data.py
```

**What it generates:**
- **FX Rates**: 730+ days of NGN, EUR, GBP exchange rates (includes simulated devaluation)
- **Purchase Orders**: ~700+ POs across 3 suppliers over 24 months
- **PO Items**: ~2,500+ line items with realistic quantities and pricing
- **Quality Incidents**: 5-10% defect sampling from completed deliveries
- **Inventory Snapshots**: Monthly inventory levels for all materials
- **Financial Summaries**: Monthly payables/receivables

**Output:**
```
Generating FX rate data...
  ✓ Generated 2190 FX rate records
Generating purchase orders...
  ✓ Generated 720 purchase orders
  ✓ Generated 2534 purchase order items
...
```

---

### Step 3: Run ETL Pipeline
Populates dimension tables and fact tables from transactional data.

```bash
python data_ingestion/populate_warehouse.py
```

**What it does:**
- Populates `dim_date` (2023-2026, ~1,460 records)
- Populates `dim_material` from `materials` table
- Populates `dim_supplier` from `suppliers` + `countries`
- Populates `fact_procurement` by joining PO items with dimensions
- Calculates `supplier_spend_summary` by year
- Computes comprehensive `supplier_performance_metrics`
- Generates `financial_kpis` (DIO, DPO, CCC)

**Output:**
```
============================================================
Starting ETL Pipeline for pro_intel_2 Data Warehouse
============================================================
Populating dim_date...
  ✓ Inserted 1461 date records
Populating dim_material...
  ✓ Inserted 3 material records
Populating dim_supplier...
  ✓ Inserted 3 supplier records
Populating fact_procurement...
  ✓ Inserted 2534 procurement fact records
...
✓ ETL Pipeline completed successfully!
```

---

### Step 4: Run Advanced Analytics
Executes FX Monte Carlo simulation and supplier risk scoring.

```bash
python analytics/advanced_analytics.py
```

**What it does:**
- **FX Simulation**: 10,000 Monte Carlo paths for 90-day NGN/USD forecast
  - Outputs: P5, median, P95 exchange rates
  - Stores results in `fx_simulation_results` table
  
- **Supplier Risk**: Multi-factor composite risk score
  - Lead time variability (25%)
  - Quality/defect rate (30%)
  - On-time delivery (25%)
  - Cost variance (10%)
  - FX exposure (10%)

**Output:**
```
============================================================
Advanced Analytics: FX Simulation & Supplier Risk
============================================================
FX Simulation Parameters:
  Currency ID: 1
  Current Rate: 621.453182
  Historical Drift (μ): 0.001234
  Historical Volatility (σ): 0.015432

Forecast (90 days ahead):
  5th Percentile (worst case): 587.234561
  Median (50th percentile): 623.891234
  95th Percentile (best case): 662.123456
  Expected Change: 0.39%

✓ Simulation results stored in fx_simulation_results table

Calculating Supplier Risk Metrics...
✓ Updated 3 supplier risk profiles

Risk Score Summary:
 supplier_id  composite_risk_score  avg_defect_rate  on_time_delivery_pct
           1                 28.45             2.34                  94.50
           2                 45.67             4.12                  87.30
           3                 18.92             1.23                  97.80
============================================================
✓ Analytics pipeline completed successfully!
```

---

## Power BI Connection

### Connection String
```
Server: localhost:3306
Database: pro_intel_2
Authentication: MySQL (root/Maconoelle86)
```

### Key Tables for Visualizations

**Star Schema (Primary)**
- `fact_procurement` (grain: PO line item)
- `dim_date`, `dim_supplier`, `dim_material`

**Aggregates (Pre-computed)**
- `supplier_spend_summary` (supplier × year)
- `supplier_performance_metrics` (current snapshot)
- `fx_simulation_results` (forecast scenarios)

**Transactional (Detail Drill-down)**
- `purchase_orders`, `purchase_order_items`
- `quality_incidents`

### Sample DAX Measures

```dax
Total Spend USD = SUM(fact_procurement[total_usd_value])

Avg Supplier Risk = AVERAGE(supplier_performance_metrics[composite_risk_score])

FX Volatility = 
    VAR CurrentRate = MAX(fx_rates[rate_to_usd])
    VAR P95Rate = MAX(fx_simulation_results[p95_rate])
    RETURN (P95Rate - CurrentRate) / CurrentRate

Quality Score = 
    100 - AVERAGE(supplier_performance_metrics[avg_defect_rate])
```

---

## Regular Maintenance Schedule

### Daily
- None (transactional data loaded via external CSV/ERP)

### Weekly
```bash
python data_ingestion/populate_warehouse.py
python analytics/advanced_analytics.py
```

### Monthly
- Review FX simulation accuracy
- Audit supplier risk scores vs actual performance
- Regenerate financial KPIs

---

## File Structure

```
procurement-intelligence-engine/
├── database/
│   └── add_constraints_migration.sql     # FK & CHECK constraints
├── data_ingestion/
│   ├── generate_sample_data.py           # Sample data generator
│   ├── populate_warehouse.py             # Dimension/fact ETL
│   └── etl_pipeline.py                   # Original (now deprecated)
├── analytics/
│   ├── advanced_analytics.py             # FX sim + risk scoring
│   ├── supplier_scoring.py               # Legacy scoring
│   ├── spend_analysis.py                 # Legacy analysis
│   ├── risk_assessment.py                # Legacy risk models
│   └── price_forecast.py                 # Legacy forecasting
├── config.py                             # Database connection
└── SETUP_GUIDE.md                        # This file
```

---

## Troubleshooting

### Issue: "Access denied for user 'root'"
**Fix:** Update password in all Python scripts:
```python
DATABASE_URL = 'mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/pro_intel_2'
```

### Issue: "Table doesn't exist"
**Fix:** Ensure all 18 tables are created in MySQL first. Check with:
```sql
USE pro_intel_2;
SHOW TABLES;
```

### Issue: "Foreign key constraint fails"
**Fix:** Run migration AFTER data is loaded:
1. Generate sample data first
2. Run ETL pipeline
3. Then apply constraints

### Issue: "Division by zero in risk scoring"
**Fix:** Ensure at least 3 suppliers with multiple POs and quality incidents exist.

---

## Database Schema Quick Reference

### Transactional Tables (Seed Data Required)
- `suppliers` (3+), `materials` (3+), `countries` (4), `currencies` (3)
- `purchase_orders`, `purchase_order_items`, `quality_incidents`

### Dimension Tables (Auto-populated by ETL)
- `dim_date`, `dim_supplier`, `dim_material`

### Fact Tables (Auto-populated by ETL)
- `fact_procurement`

### Aggregate Tables (Auto-computed)
- `supplier_spend_summary`
- `supplier_performance_metrics`
- `fx_simulation_results`
- `financial_kpis`

### Supporting Tables
- `fx_rates`, `inventory_snapshots`
- `payables_summary`, `receivables_summary`

---

## Next Steps

1. **Verify Setup**: Run all 4 steps in sequence
2. **Configure Power BI**: Connect to `pro_intel_2` and build dashboards
3. **Customize Analytics**: Adjust risk weights in `advanced_analytics.py`
4. **Schedule Automation**: Set up cron/Task Scheduler for weekly ETL runs
5. **Add More Data**: Import real CSV data using modified `generate_sample_data.py`

---

## Support & Feedback

For schema changes or additional analytics modules, consult the main `README.md` or database documentation.
