# Detailed Walkthrough: Building the Procurement Intelligence Project

This project evolved through **two distinct phases** — an initial Procurement Intelligence Engine and a specialized PVIS (Procurement Volatility Intelligence System) that grew out of it.

---

## Phase 1: Foundation — The Procurement Intelligence Engine

**Goal:** Build a basic procurement analytics platform with ETL, supplier intelligence, risk modeling, and a web dashboard.

### Step 1: Database & Configuration

A MySQL database `pro_intel_2` was created with core transactional tables (`suppliers`, `materials`, `currencies`, `countries`, `purchase_orders`, `purchase_order_items`, `fx_rates`, `quality_incidents`, `inventory_snapshots`, `payables_summary`, `receivables_summary`) plus warehouse tables (`dim_date`, `dim_supplier`, `dim_material`, `fact_procurement`, `supplier_spend_summary`, `supplier_performance_metrics`, `financial_kpis`).

`config.py` holds the connection string:

```python
DATABASE_URL = 'mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2'
```

### Step 2: ETL Pipeline (`data_ingestion/etl_pipeline.py`)

The first ETL module used SQLAlchemy ORM models (`Supplier`, `Invoice`) to:

1. **Extract** data from `sample_data.csv` (or generate synthetic rows if the file is missing)
2. **Transform** — parse dates, fill missing ratings with a default of 3.0
3. **Load** — upsert suppliers and append invoices to MySQL

This was the "v1" ingestion approach — simple CSV-driven, suitable for prototyping.

### Step 3: Analytics Modules

Five analytics modules were built:

| Module | File | Purpose |
|--------|------|---------|
| Market Intelligence | `analytics/market_intelligence.py` | Simulates commodity price fetching (e.g. copper), calculates average price/volatility/trend, and provides geopolitical risk scores by country |
| Price Forecasting | `analytics/price_forecast.py` | Trains a `LinearRegression` model on simulated 100-month price/demand data, saves the model as a `.pkl`, and forecasts future commodity prices |
| Risk Assessment | `analytics/risk_assessment.py` | Uses `LogisticRegression` to predict supplier failure probability based on rating, average spend, and location risk. Also includes a compliance check for EU regulations |
| Spend Analysis | `analytics/spend_analysis.py` | Queries invoices joined with suppliers, aggregates spend by supplier and category, generates bar and pie charts |
| Supplier Scoring | `analytics/supplier_scoring.py` | Calculates a composite supplier score from rating, average spend, invoice count, and location risk, then ranks suppliers |

### Step 4: Contract Automation (`automation/contract_analysis.py`)

Uses **spaCy NLP** (`en_core_web_sm`) to extract named entities (organizations, money amounts, dates) from contract text. Also detects penalty and termination clauses, and generates templated RFP responses.

### Step 5: Flask Web Dashboard (`ui/app.py`)

A Flask app serves an HTML dashboard with:

- **Plotly** bar chart of invoice amounts over time
- **Plotly** bar chart of top-ranked suppliers
- Market intelligence summary (copper price trends)

Accessed at `http://127.0.0.1:5000`.

### Step 6: Testing (`tests/`)

Three test files cover:

- `tests/test_etl.py` — Tests CSV extraction and data transformation (date parsing, null filling)
- `tests/test_analytics.py` — Tests supplier scoring on synthetic data
- `tests/test_risk_assessment.py` — Tests risk data loading, model training, and compliance logic

### Step 7: Containerization

- `Dockerfile` — Python 3.11-slim image, installs pinned requirements, runs Gunicorn with 2 workers on port 5000
- `docker-compose.yml` — Exposes port 5000, mounts project as volume

---

## Phase 2: PVIS — Procurement Volatility Intelligence System

**Goal:** Transform the foundation into a board-grade intelligence system focused on **FX volatility, supplier risk quantification, working capital optimization, and executive reporting**.

The PVIS codebase lives in the `pvis-publish` directory (pushed to [github.com/DavidMaco/pvis](https://github.com/DavidMaco/pvis)) and represents the production-ready evolution.

### Step 8: Production Configuration (`config.py`)

The config was completely rewritten to be **environment-variable driven**:

- `get_database_url()` — reads `PVIS_DATABASE_URL` or falls back to local dev default
- `get_mysql_params()` — returns PyMySQL connection dict from individual env vars
- `get_runtime_mode()` — supports `development` / `staging` / `production`
- `validate_runtime_settings()` — **blocks production startup** if secrets aren't set or synthetic FX fallback is enabled
- `allow_synthetic_fx_fallback()` — controls whether fake FX data is acceptable
- `get_usd_ngn_override_rate()` — manual override for the USD/NGN rate
- Structured logging via `logging.basicConfig()` with configurable log level

### Step 9: Realistic Data Generation (`data_ingestion/generate_sample_data.py`)

The biggest evolution — replaced hardcoded synthetic rates with **live market data**:

#### 9a. HTTP Client — `_fetch_json()`

An HTTP client with `User-Agent: PVIS/1.1` header and SSL context (fixes 403 errors from APIs that block bare `urlopen` calls).

#### 9b. Live FX Rates — `fetch_usd_latest_rates()`

Tries three FX API providers in order:

1. `open.er-api.com` (primary — has NGN)
2. `exchangerate-api.com` (backup — has NGN)
3. `frankfurter.app` (ECB source — EUR/GBP only, no NGN)

#### 9c. Historical Rates — `fetch_usd_historical_rates()`

Pulls real historical EUR/GBP data from Frankfurter's time-series API.

#### 9d. NGN Backcast — `_build_deterministic_backcast_from_latest()`

Since no free API provides NGN historical data, this function:

- Starts at 65% of the live rate (e.g. ~875 if current = 1,345)
- Applies an **accelerating depreciation curve** (power 1.3) modeling NGN devaluation
- Adds mild seasonality (sinusoidal) and daily noise (±0.3%)
- Pins the final date exactly to the live market rate

#### 9e. FX Rate Orchestrator — `generate_fx_rates()`

1. Fetches live spot rate (confirmed: **1,345.77 NGN per 1 USD**)
2. EUR/GBP → real Frankfurter historical data
3. NGN → deterministic backcast from live rate
4. Maps currency codes to IDs from the `currencies` table
5. Writes to `fx_rates` table (~837 records for 24 months × 3 currencies)

#### 9f. Other Generators

Remain similar to Phase 1 but use FK-safe `DELETE` instead of `REPLACE`:

- `generate_purchase_orders()` — 8-15 POs/month per supplier, 1-5 line items each
- `generate_quality_incidents()` — 5-10% of completed deliveries get quality events
- `generate_inventory_snapshots()` — Monthly inventory levels per material
- `generate_financial_summaries()` — Monthly payables and receivables

### Step 10: Star Schema ETL (`data_ingestion/populate_warehouse.py`)

Populates the **data warehouse** from transactional tables:

| Function | Target Table | Logic |
|----------|-------------|-------|
| `populate_dim_date()` | `dim_date` | 4-year calendar (2023-2026), date keys in YYYYMMDD format |
| `populate_dim_material()` | `dim_material` | Maps `material_id` → surrogate `material_key` |
| `populate_dim_supplier()` | `dim_supplier` | Joins `suppliers` ↔ `countries`, assigns surrogate keys |
| `populate_fact_procurement()` | `fact_procurement` | Joins PO items with FX rates (closest date ≤ order date), calculates `total_usd_value = local_value / rate_to_usd` |
| `populate_supplier_spend_summary()` | `supplier_spend_summary` | Annual USD spend per supplier using avg FX rate |
| `populate_supplier_performance_metrics()` | `supplier_performance_metrics` | Composite risk score from lead time, defects, OTD, cost variance, FX exposure |
| `populate_financial_kpis()` | `financial_kpis` | Calculates DIO, DPO, and CCC (Cash Conversion Cycle) |

The **composite risk score** formula:

```
Risk = (0.30 × LeadTimeNorm + 0.35 × DefectNorm + 0.25 × OTDNorm + 0.10 × FXExposureNorm) × 100
```

### Step 11: Advanced Analytics (`analytics/advanced_analytics.py`)

Two main capabilities:

#### A) Monte Carlo FX Simulation (`run_fx_simulation`)

1. Loads historical FX rates for NGN from `fx_rates`
2. Calculates daily **log returns**: `r_t = ln(S_t / S_{t-1})`
3. Estimates drift (μ) and volatility (σ)
4. Runs **10,000 simulations** over 90 trading days using Geometric Brownian Motion:

```
S_{t+1} = S_t × exp(μ·dt + σ·√dt·Z)
```

where Z ~ N(0,1) and dt = 1/252

5. Reports P5, P50, P95 percentiles (e.g. P5=1,338.91, P50=1,346.01, P95=1,353.23)
6. Stores results in `fx_simulation_results` table

#### B) Supplier Risk Scoring (`run_supplier_risk`)

- Queries lead time stats, quality defect rates, on-time delivery %, cost variance %, and FX exposure %
- Merges all metrics per supplier
- Normalizes each to [0,1] and computes the 5-factor weighted composite risk score
- Writes to `supplier_performance_metrics`

### Step 12: Optimization Engine (`analytics/optimization_engine.py`)

Four strategic outputs:

| Function | Output Table | Purpose |
|----------|-------------|---------|
| `build_fx_exposure_mapping()` | `fx_exposure_mapping` | Maps each supplier's total local and USD spend with FX exposure % |
| `build_scenario_planning()` | `scenario_planning_output` | Calculates landed cost impact under 4 FX scenarios: Base (0%), NGN Mild Deval (+10%), Severe Deval (+20%), Appreciation (-10%) |
| `build_working_capital_restructuring()` | `working_capital_opportunities` | Reads current DIO/DPO/CCC, targets 10% DIO reduction and 10% DPO extension, calculates CCC improvement |
| `build_negotiation_insights()` | `negotiation_insights` | Top-10 riskiest suppliers with auto-generated negotiation strategies (SLA penalties, quality rebates, indexed pricing, FX hedging) |

### Step 13: Executive Visualizations (`reports/generate_pvis_visuals.py`)

Generates **13 PNG charts** using matplotlib:

| # | Visual | Description |
|---|--------|-------------|
| 1 | `risk_heatmap.png` | Normalized heatmap of all risk factors by supplier |
| 2 | `lead_time_volatility.png` | Bar chart of lead time volatility + line for avg lead time |
| 3 | `cost_variance_table.png` | Tabular display of cost variance % and risk scores |
| 4 | `top10_risk_suppliers.png` | Horizontal bar chart of top 10 composite risk scores |
| 5 | `fx_scenario_band.png` | 5th-95th percentile FX band from Monte Carlo simulation |
| 6 | `fx_distribution.png` | Histogram of terminal FX rates with P5/P50/P95 lines |
| 7 | `landed_cost_stress_impact.png` | Bar chart of USD impact under each FX scenario |
| 8 | `cost_leakage_breakdown.png` | Cost leakage by material category (above-standard-cost spend) |
| 9 | `inventory_trend.png` | Time series of total inventory value |
| 10 | `dpo_vs_dio.png` | Dual-line chart of DPO and DIO proxies over time |
| 11 | `ccc_trend.png` | Current vs target CCC bar chart |
| 12 | `optimization_estimator.png` | Working capital release opportunity in USD |
| 13 | `dashboard_blueprint.png` | Power BI executive dashboard wireframe layout |

### Step 14: Executive PDF Report (`reports/generate_executive_report.py`)

Assembles all visuals into a **multi-page PDF** (`Executive_Report.pdf`) using `matplotlib.backends.backend_pdf.PdfPages`:

| Page | Content |
|------|---------|
| 1 | **Cover** — Business problem statement, PVIS mandate, 3 strategic recommendations |
| 2 | Dashboard Blueprint |
| 3 | Risk Heatmap |
| 4 | Lead Time Volatility + Top 10 Risk Suppliers |
| 5 | Cost Variance Table + Cost Leakage Breakdown |
| 6 | FX Scenario Band + Monte Carlo Distribution |
| 7 | Landed Cost Stress Impact |
| 8 | Working Capital: Inventory Trend + DPO vs DIO + CCC Trend |
| 9 | Optimization Opportunity Estimator |

### Step 15: Database Integrity (`database/add_constraints_migration.sql` + `apply_constraints.py`)

A comprehensive SQL migration adds:

- **15 foreign key constraints** (e.g. `fk_po_supplier`, `fk_poi_material`, `fk_fx_currency`, `fk_fact_supplier`)
- **13 CHECK constraints** (e.g. `risk_index` 0-100, `quantity > 0`, `defect_rate` 0-1, `delivery_date >= order_date`)
- **7 composite indexes** for analytical query performance
- **`fx_simulation_results`** table creation

The Python runner (`apply_constraints.py`) reads the SQL file, splits by `;`, filters out comments, executes each statement, and gracefully skips "already exists" errors.

### Step 16: End-to-End Pipeline Orchestrator (`run_pvis_pipeline.py`)

A single entry point that runs the entire pipeline in order:

```
validate_runtime_settings()
  → generate_sample_data()       ← Live FX + realistic PO/quality/inventory data
    → run_etl()                   ← Star schema dimensions + facts
      → run_fx_simulation()       ← 10K Monte Carlo paths, 90 days
        → run_supplier_risk()     ← Composite risk scoring
          → run_optimization()    ← Scenarios, working capital, negotiation
            → generate_visuals()  ← 13 PNG charts
              → generate_report() ← Executive PDF
```

### Step 17: Verification (`verify_setup.py`)

Connects to MySQL and reports row counts for all 11 key tables, plus counts of foreign keys and indexes — a quick health check.

### Step 18: Production Hardening & GitHub Release

- Environment variable support for all secrets
- `PVIS_ENV=production` mode blocks synthetic FX fallback
- Structured logging with configurable level
- `PRODUCTION_READINESS.md` documents remaining gaps (secrets management, CI/CD, observability, data quality gates, access control, backup/DR)
- Tagged as **v1.0.0** and published as a [GitHub Release](https://github.com/DavidMaco/pvis/releases/tag/v1.0.0)

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     LIVE FX APIS                            │
│   open.er-api.com → exchangerate-api.com → frankfurter.app │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA GENERATION (generate_sample_data.py)      │
│   FX Rates (live NGN + historical EUR/GBP)                  │
│   Purchase Orders → Line Items → Quality Incidents          │
│   Inventory Snapshots → Payables/Receivables                │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              ETL WAREHOUSE (populate_warehouse.py)           │
│   dim_date | dim_supplier | dim_material                    │
│   fact_procurement | supplier_spend_summary                  │
│   supplier_performance_metrics | financial_kpis              │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              ANALYTICS ENGINE                                │
│   Monte Carlo FX Simulation (10K paths × 90 days)           │
│   Composite Supplier Risk Scoring (5 factors)                │
│   FX Exposure Mapping | Scenario Planning                    │
│   Working Capital Restructuring | Negotiation Insights       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              REPORTING                                       │
│   13 Executive Visuals (matplotlib → PNG)                    │
│   Multi-page Executive PDF (PdfPages)                        │
│   Power BI Dashboard Blueprint                               │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | MySQL 8 (`pro_intel_2`) |
| ORM/Connection | SQLAlchemy + PyMySQL |
| Data Processing | pandas, NumPy |
| Simulation | NumPy (Geometric Brownian Motion) |
| ML (Phase 1) | scikit-learn (LogisticRegression, LinearRegression) |
| NLP (Phase 1) | spaCy |
| Visualization | matplotlib |
| Web (Phase 1) | Flask + Plotly |
| FX Data | open.er-api.com, exchangerate-api.com, Frankfurter (ECB) |
| Deployment | Docker, GitHub Actions |
| Version Control | Git → GitHub (`DavidMaco/pvis`) |

---

*Document generated: February 20, 2026*
