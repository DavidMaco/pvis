# PROJECT WALKTHROUGH
## Building the Procurement Intelligence Engine — A Complete Build History

**Document Date:** February 20, 2026
**Repository:** [DavidMaco/Procurement_Intelligence_Proj1](https://github.com/DavidMaco/Procurement_Intelligence_Proj1)
**Tech Stack:** Python 3.13 · MySQL 8.0 · Streamlit 1.54 · SQLAlchemy · NumPy · Plotly

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Phase 1 — Foundation (Scaffold & Prototyping)](#2-phase-1--foundation)
3. [Phase 2 — Database Schema & Constraints](#3-phase-2--database-schema--constraints)
4. [Phase 3 — Realistic Data Generation](#4-phase-3--realistic-data-generation)
5. [Phase 4 — Star-Schema ETL Pipeline](#5-phase-4--star-schema-etl-pipeline)
6. [Phase 5 — Advanced Analytics Engine](#6-phase-5--advanced-analytics-engine)
7. [Phase 6 — Streamlit Executive Dashboard](#7-phase-6--streamlit-executive-dashboard)
8. [Phase 7 — Production Hardening](#8-phase-7--production-hardening)
9. [Phase 8 — Comprehensive Accuracy Audit](#9-phase-8--comprehensive-accuracy-audit)
10. [Phase 9 — Final Integrity Review & Cleanup](#10-phase-9--final-integrity-review--cleanup)
11. [Final Architecture](#11-final-architecture)
12. [Database Schema Reference](#12-database-schema-reference)
13. [File Manifest](#13-file-manifest)

---

## 1. Project Overview

The Procurement Intelligence Engine is a production-grade data analytics system designed for manufacturing organizations to:

- **Monitor FX volatility** using Monte Carlo simulation (10,000 Geometric Brownian Motion paths)
- **Score supplier risk** using a 5-factor composite model (lead time, defects, OTD, cost variance, FX exposure)
- **Analyze procurement spend** across 8 international suppliers, 50 materials, and 5 currencies
- **Optimize working capital** through DIO, DPO, and Cash Conversion Cycle metrics
- **Support executive decisions** via a 7-page interactive Streamlit dashboard

The project evolved through 9 distinct phases, progressing from a basic Flask prototype to a fully audited, production-ready Streamlit application.

---

## 2. Phase 1 — Foundation

### Goal
Scaffold a basic procurement analytics platform with ETL, supplier intelligence, risk modeling, and a web dashboard.

### What Was Built

**Project structure:**
```
procurement-intelligence-engine/
├── data_ingestion/
│   ├── etl_pipeline.py        # CSV-based ETL with SQLAlchemy ORM
│   └── sample_data.csv        # Test data
├── analytics/
│   ├── supplier_scoring.py    # Composite supplier ranking
│   ├── spend_analysis.py      # Spend aggregation + matplotlib charts
│   ├── price_forecast.py      # LinearRegression price forecasting
│   ├── risk_assessment.py     # LogisticRegression failure prediction
│   └── market_intelligence.py # Simulated commodity price feeds
├── automation/
│   └── contract_analysis.py   # spaCy NLP entity extraction
├── ui/
│   └── app.py                 # Flask dashboard with Plotly
├── tests/                     # unittest suite
├── config.py                  # SQLite → MySQL connection string
├── requirements.txt           # All deps including tensorflow, spacy, flask
├── Dockerfile                 # Gunicorn + Flask container
└── docker-compose.yml         # Port 5000
```

**Key decisions:**
- MySQL database `pro_intel_2` chosen over SQLite for production viability
- SQLAlchemy used for ORM (Supplier and Invoice models)
- Initial analytics used scikit-learn for ML prototyping (LogisticRegression, LinearRegression)
- spaCy NLP used for contract entity extraction
- Flask served as the initial web framework
- GitHub Actions CI configured for automated testing

**Artifacts produced:**
- Initial commit pushed to GitHub (`DavidMaco/Procurement_Intelligence_Proj1`)
- README.md, .gitignore, GitHub CI workflow

---

## 3. Phase 2 — Database Schema & Constraints

### Goal
Design a comprehensive 18-table relational schema supporting both transactional operations and analytical warehousing.

### Schema Design

**Transactional tables (11):**

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `countries` | Reference dimension | country_id, country_name, region |
| `currencies` | 5 currencies (USD, EUR, NGN, GBP, CNY) | currency_id, currency_code |
| `suppliers` | 8 international suppliers | supplier_id, supplier_name, country_id, default_currency_id, lead_time_days |
| `materials` | 50 materials across 5 categories | material_id, material_name, category, standard_cost |
| `purchase_orders` | ~778 POs over 3 years | po_id, supplier_id, order_date, delivery_date, currency_id, status |
| `purchase_order_items` | ~1,952 line items | poi_id, po_id, material_id, quantity, unit_price |
| `fx_rates` | ~4,384 daily FX rates | fx_id, currency_id, rate_date, rate_to_usd |
| `quality_incidents` | ~106 defect events | qi_id, supplier_id, po_id, defect_rate, incident_date |
| `inventory_snapshots` | 1,800 monthly snapshots | snapshot_date, material_id, quantity_on_hand, value |
| `payables_summary` | 36 monthly AP summaries | period_date, total_payable, avg_days_outstanding |
| `receivables_summary` | 36 monthly AR summaries | period_date, total_receivable, avg_days_outstanding |

**Warehouse tables (8):**

| Table | Purpose |
|-------|---------|
| `dim_date` | 1,461-row date dimension (2023–2026) |
| `dim_supplier` | Surrogate-keyed supplier dimension |
| `dim_material` | Surrogate-keyed material dimension |
| `fact_procurement` | 1,952 fact rows joining PO items with FX rates |
| `supplier_spend_summary` | Annual USD spend per supplier |
| `supplier_performance_metrics` | Composite risk scores per supplier |
| `financial_kpis` | DIO, DPO, CCC metrics |
| `fx_simulation_results` | Monte Carlo simulation outputs |

### Constraints Migration (`database/add_constraints_migration.sql`)

A 288-line SQL migration was written adding:
- **15 foreign key constraints** (e.g., `fk_po_supplier`, `fk_poi_material`, `fk_fx_currency`)
- **13 CHECK constraints** (e.g., `risk_index` 0–100, `quantity > 0`, `defect_rate` 0–1)
- **7 composite indexes** for analytical query performance
- `fx_simulation_results` table DDL

**Currency ID mapping (critical for correctness):**

| ID | Code | Notes |
|----|------|-------|
| 1 | USD | Base currency — no FX rates stored |
| 2 | EUR | European suppliers |
| 3 | NGN | Nigerian Naira — primary volatility target |
| 4 | GBP | British Pound |
| 5 | CNY | Chinese Yuan |

---

## 4. Phase 3 — Realistic Data Generation

### Goal
Replace prototype synthetic data with 3 years of realistic procurement data including live FX rates.

### Implementation: `data_ingestion/seed_realistic_data.py` (504 lines)

**Key capabilities:**

#### Live FX Rate Fetching
The seed script fetches **real-time FX rates** from three APIs with cascading fallback:

1. **open.er-api.com** (primary — supports all currencies including NGN)
2. **exchangerate-api.com** (backup — supports NGN)
3. **frankfurter.app** (ECB source — EUR/GBP only, no NGN)

An HTTP client with `User-Agent: PVIS/1.1` prevents 403 blocks from APIs.

#### NGN Historical Backcast
Since no free API provides NGN historical data, the system:
- Starts at 65% of the live spot rate
- Applies an **accelerating depreciation curve** (power 1.3) modeling real NGN devaluation
- Adds seasonality (sinusoidal) and daily noise (±0.3%)
- Pins the final date exactly to the live market rate

#### EUR/GBP Historical Rates
Real historical data from Frankfurter's time-series API (ECB source).

#### Supplier Ecosystem

| Supplier | Country | Currency | OTD Probability |
|----------|---------|----------|----------------|
| Houston Petrochem Inc | USA | USD | 98% |
| Bavaria Chem GmbH | Germany | EUR | 90% |
| Lagos Polymers Ltd | Nigeria | NGN | 80% |
| Yorkshire Compounds Ltd | UK | GBP | 92% |
| Shenzhen Industrial Co | China | CNY | 82% |
| Mumbai Steel & Alloys | India | USD | 85% |
| São Paulo Resinas SA | Brazil | USD | 80% |
| Johannesburg Mining Corp | S. Africa | USD | 92% |

Each supplier has a calibrated on-time delivery probability controlling whether `delivery_date ≤ order_date + lead_time_days`.

#### Data Volumes Generated
- 8 suppliers × 3 years of POs → ~778 purchase orders, ~1,952 line items
- 4 currencies × ~3 years daily rates → ~4,384 FX records
- ~106 quality incidents (5–10% of deliveries)
- 50 materials × 36 months → 1,800 inventory snapshots
- 36 months each of payables and receivables summaries

---

## 5. Phase 4 — Star-Schema ETL Pipeline

### Goal
Build a warehouse ETL that transforms transactional data into analytical dimensions, facts, and aggregates.

### Implementation: `data_ingestion/populate_warehouse.py` (477 lines)

**ETL functions (executed in order):**

| # | Function | Target Table | Logic |
|---|----------|-------------|-------|
| 1 | `populate_dim_date()` | `dim_date` | 4-year calendar (2023–2026), date_key = YYYYMMDD |
| 2 | `populate_dim_material()` | `dim_material` | Maps material_id → surrogate material_key |
| 3 | `populate_dim_supplier()` | `dim_supplier` | Joins `suppliers` ↔ `countries`, assigns surrogate keys |
| 4 | `populate_fact_procurement()` | `fact_procurement` | Joins PO items with closest-date FX rate, calculates `total_usd_value = local_value / rate_to_usd` |
| 5 | `populate_supplier_spend_summary()` | `supplier_spend_summary` | Annual USD spend per supplier using avg FX rate |
| 6 | `populate_supplier_performance_metrics()` | `supplier_performance_metrics` | 5-factor composite risk score |
| 7 | `populate_financial_kpis()` | `financial_kpis` | DIO, DPO, CCC from payables/receivables/inventory |

**FX Rate Lookup Logic:**
For each PO item, the ETL finds the FX rate with the closest date ≤ the order date:
```sql
LEFT JOIN fx_rates fr ON fr.currency_id = po.currency_id
    AND fr.rate_date = (
        SELECT MAX(rate_date) FROM fx_rates
        WHERE currency_id = po.currency_id AND rate_date <= po.order_date
    )
```

**On-Time Delivery Calculation:**
```sql
OTD % = COUNT(po.delivery_date <= DATE_ADD(po.order_date, INTERVAL s.lead_time_days DAY))
        / COUNT(*)
```
This compares ACTUAL delivery date against the supplier's PUBLISHED `lead_time_days`, not the PO's `expected_delivery_date`.

**Composite Risk Score Formula:**
```
Risk = (0.30 × LeadTimeNorm + 0.35 × DefectNorm + 0.25 × (1 - OTD) + 0.10 × FXExposure) × 100
```
Each factor normalized to [0, 1] using min-max scaling across all suppliers.

**Cash Conversion Cycle:**
```
CCC = DIO − DPO
```
Where:
- DIO = (avg_inventory / annualized_cost) × 365
- DPO = (avg_payable / annualized_spend) × 365

---

## 6. Phase 5 — Advanced Analytics Engine

### Goal
Build Monte Carlo FX simulation and composite supplier risk scoring modules.

### Implementation: `analytics/advanced_analytics.py` (279 lines)

#### Monte Carlo FX Simulation

**Method:** Geometric Brownian Motion (GBM)

1. Load historical FX rates for the chosen currency from `fx_rates`
2. Calculate daily log returns: $r_t = \ln(S_t / S_{t-1})$
3. Estimate drift ($\mu$) and volatility ($\sigma$) from historical returns
4. Run **10,000 simulations** over 90 trading days:

$$S_{t+1} = S_t \times \exp\left(\mu \cdot dt + \sigma \cdot \sqrt{dt} \cdot Z\right)$$

Where $Z \sim N(0,1)$ and $dt = 1/252$

5. Extract P5, P50, P95 percentiles from terminal rates
6. Store results in `fx_simulation_results` table

**Latest results (NGN/USD):**
- Current rate: 1,345.77
- P5 (bear case): 1,338.91
- P50 (median): 1,346.01
- P95 (bull case): 1,353.23

#### Supplier Risk Scoring

Queries live transactional data and computes:
- Average lead time (days) and standard deviation
- Average defect rate from quality incidents
- On-time delivery percentage
- Cost variance vs. material standard cost
- FX exposure (% of spend in non-USD currencies)

Normalizes each metric to [0, 1] and applies the weighted composite formula.

---

## 7. Phase 6 — Streamlit Executive Dashboard

### Goal
Replace the Flask prototype with a production-grade 7-page Streamlit dashboard.

### Implementation: `streamlit_app.py` (724 lines)

**Page structure:**

| # | Page | Key Visuals |
|---|------|-------------|
| 1 | **Executive Summary** | 4 KPI metrics (total POs, total spend, active suppliers, avg risk score) + monthly spend trend + risk distribution + top 5 materials |
| 2 | **FX Volatility & Monte Carlo** | Live NGN rate from API + historical rate chart + inline 10K-path Monte Carlo simulation with fan chart and histogram |
| 3 | **Supplier Risk Analysis** | Composite risk bar chart + detailed risk metrics table + risk score distribution histogram |
| 4 | **Spend & Cost Analysis** | Spend by supplier (bar) + spend by category (bar) + monthly spend trend + cost leakage analysis |
| 5 | **Working Capital** | DIO/DPO/CCC gauges + payables timeline + receivables timeline + inventory value trend |
| 6 | **Scenario Planning** | FX impact simulator: user inputs rate change %, system calculates USD impact per supplier |
| 7 | **Pipeline Runner** | One-click buttons to re-run seed data, ETL, and FX simulation directly from the dashboard |

**Key technical decisions:**
- `@st.cache_resource` used for database engine (connection pooling)
- `run_query()` helper wraps all SQL in `text()` for SQLAlchemy 2.0 compliance
- Live NGN rate fetched from `open.er-api.com` on page load
- Monte Carlo simulation runs entirely in-process (NumPy), not from stored results
- `DATE_FORMAT` MySQL function uses `%%` escaping for Python string safety
- All `GROUP BY` clauses use full expressions (not aliases) for MySQL 8.0 ONLY_FULL_GROUP_BY compliance

**Streamlit configuration (`.streamlit/config.toml`):**
- Custom dark-blue theme (`#1d4f91` primary)
- Headless mode for server deployment
- XSRF protection enabled
- Usage stats gathering disabled

---

## 8. Phase 7 — Production Hardening

### Goal
Make the system deployment-ready with proper config management, containerization, and CI.

### Changes Made

**`config.py` — Environment-aware configuration:**
```python
try:
    db = st.secrets["database"]  # Streamlit Cloud secrets
    DATABASE_URL = f"mysql+pymysql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:***@localhost:3306/pro_intel_2")
```

**`Dockerfile` — Streamlit container:**
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**`docker-compose.yml` — Full stack:**
- Streamlit app container on port 8501
- MySQL 8.0 container with persistent volume
- Environment variable injection for credentials

**`.streamlit/secrets.toml.example`** — Template for credentials (never committed)

**GitHub Actions CI** (`.github/workflows/python-app.yml`):
- Triggers on push/PR to main
- Python 3.13 on ubuntu-latest
- Installs requirements.txt + pytest
- Runs `python -m pytest tests/ -v`

**GitHub release:** Tagged as v1.0.0 and published

---

## 9. Phase 8 — Comprehensive Accuracy Audit

### Goal
Conduct a thorough data accuracy audit to find and fix every numerical, logical, and query error.

### Issues Found and Fixed (8 Critical Fixes)

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | OTD always 100% | Useless metric | Changed OTD calc to compare actual delivery vs published `lead_time_days` |
| 2 | DIO/DPO/CCC identity | CCC always = DIO − DPO with no real meaning | Rewrote to use actual inventory, payables, and receivables data |
| 3 | Cost leakage label wrong | Misleading dashboard | Fixed label to accurately describe above-standard-cost analysis |
| 4 | `fx_simulation_results` stale data | Old rows polluting results | Added cleanup before each simulation run |
| 5 | Currency_id=1 default for FX sim | Simulating USD (base currency) instead of NGN | Changed default to `currency_id=3` (NGN) |
| 6 | `DATE_FORMAT` escaping | Python `%M` interpreted as format specifier | Used `%%M`, `%%Y` etc. for MySQL compatibility |
| 7 | `GROUP BY` alias error | MySQL ONLY_FULL_GROUP_BY rejection | Changed to GROUP BY full expressions |
| 8 | Live NGN rate not displayed | Dashboard showed stale rate | Added API call to `open.er-api.com` on FX page load |

### Verification
After fixes, all 6 dashboard queries were re-run against the database:
- Executive KPIs: 778 POs, $79.6M spend, 8 suppliers, 28.2 avg risk
- All 8 suppliers showing realistic risk scores (3.7 to 47.4)
- OTD ranging from 79.8% (São Paulo) to 98.9% (Houston) — realistic variation
- CCC: −4.62 days (strong working capital position)
- Zero FK orphans across all tables

---

## 10. Phase 9 — Final Integrity Review & Cleanup

### Goal
Three recursive reviews ensuring zero errors, followed by project synchronization.

### Review 1: Full Code Audit
Read every file in the project. Identified:
- **15+ stale legacy files** from Phase 1 (Flask app, old analytics stubs, spaCy/sklearn modules, old ETL, sample CSV, pinned-requirements, etc.)
- **7 config files** needing updates (Dockerfile, docker-compose, requirements, .gitignore, pytest.ini, CI workflow, README)
- **1 code bug** (misleading default `currency_id=1` in `run_fx_simulation`)

### Review 2: Data & Query Integrity
- Verified all 19 table row counts
- Ran all 6 key dashboard queries — all returned valid data
- Confirmed zero FK orphans (purchase_orders → suppliers, fact_procurement → dimensions)
- Validated `financial_kpis` column names match dashboard queries

### Review 3: Runtime Verification
- All Python files compile without syntax errors
- All imports resolve (streamlit, pandas, numpy, plotly, sqlalchemy, requests, pymysql)
- Advanced analytics module imports correctly
- Streamlit config.toml CORS/XSRF conflict resolved

### Cleanup Actions

**Files deleted (25+):**
- `app.py` (Flask entry point)
- `ui/app.py` + `ui/__pycache__/` (Flask dashboard)
- `analytics/supplier_scoring.py`, `spend_analysis.py`, `market_intelligence.py`, `price_forecast.py`, `risk_assessment.py` (old stubs)
- `analytics/risk_model.pkl` (stale model)
- `automation/contract_analysis.py` (spaCy stub)
- `data_ingestion/etl_pipeline.py`, `generate_sample_data.py`, `sample_data.csv` (superseded)
- `pinned-requirements.txt` (164-line Flask-era file)
- `tests/test_hello.py`, `test_analytics.py`, `test_etl.py`, `test_risk_assessment.py` (tested stale modules)
- `IMPLEMENTATION_SUMMARY.md`, `QUICK_START.md`, `SETUP_GUIDE.md`, `PROJECT_WALKTHROUGH.md` (outdated docs)
- `settings.json`, `pytest.log`, `procurement.db`, `pro-intel-2-analytics/` (junk files)

**Files updated (8):**
- `Dockerfile` → Streamlit container (was Flask/Gunicorn)
- `docker-compose.yml` → Port 8501 + MySQL service (was port 5000)
- `requirements.txt` → 8 deps (was 15 including tensorflow, spacy, flask)
- `.gitignore` → Added `.pytest_cache/`, `*.pkl`, `settings.json`, `.venv/`
- `pytest.ini` → Removed log file output
- `.github/workflows/python-app.yml` → Python 3.13 + pytest (was 3.11 + unittest)
- `.streamlit/config.toml` → Fixed CORS/XSRF conflict
- `analytics/advanced_analytics.py` → Default `currency_id=3` (NGN)

**New files created (5):**
- `tests/conftest.py` — Shared pytest fixtures
- `tests/test_config.py` — Config module tests
- `tests/test_advanced_analytics.py` — Analytics module tests
- `tests/test_data_ingestion.py` — ETL module tests
- `tests/test_integration.py` — Database connectivity and table integrity tests
- This `PROJECT_WALKTHROUGH.md`

**Test results:** 12/12 tests passing

---

## 11. Final Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LIVE FX APIs                            │
│   open.er-api.com → exchangerate-api.com → frankfurter.app │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│      DATA GENERATION  (data_ingestion/seed_realistic_data.py)│
│  • Fetches live NGN/EUR/GBP/CNY rates                       │
│  • Backcasts 3 years of NGN with depreciation curve         │
│  • Generates 778 POs, 1952 items, 106 quality incidents     │
│  • Creates inventory snapshots + financial summaries         │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│      STAR-SCHEMA ETL  (data_ingestion/populate_warehouse.py) │
│  • dim_date (1,461) · dim_supplier (8) · dim_material (50)  │
│  • fact_procurement (1,952) with FX-converted USD values     │
│  • Composite risk scoring (5 weighted factors)               │
│  • Financial KPIs: DIO, DPO, CCC                            │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│      ANALYTICS  (analytics/advanced_analytics.py)            │
│  • Monte Carlo: 10K GBM paths × 90 trading days             │
│  • Reports P5/P50/P95 percentiles                            │
│  • Stores results in fx_simulation_results                   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│      STREAMLIT DASHBOARD  (streamlit_app.py)                 │
│  Page 1: Executive Summary (KPIs, trends, top materials)     │
│  Page 2: FX Volatility & Monte Carlo (live rate, sim)        │
│  Page 3: Supplier Risk Analysis (scores, metrics)            │
│  Page 4: Spend & Cost Analysis (by supplier/category)        │
│  Page 5: Working Capital (DIO/DPO/CCC, timelines)           │
│  Page 6: Scenario Planning (FX impact calculator)            │
│  Page 7: Pipeline Runner (re-run seed/ETL/analytics)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Database Schema Reference

### Currency Mapping
| currency_id | currency_code | Used By |
|-------------|--------------|---------|
| 1 | USD | Houston Petrochem, Mumbai Steel, São Paulo Resinas, Johannesburg Mining |
| 2 | EUR | Bavaria Chem GmbH |
| 3 | NGN | Lagos Polymers Ltd |
| 4 | GBP | Yorkshire Compounds Ltd |
| 5 | CNY | Shenzhen Industrial Co |

### Table Row Counts (as of Feb 20, 2026)
| Table | Rows |
|-------|------|
| countries | 8 |
| currencies | 5 |
| suppliers | 8 |
| materials | 50 |
| purchase_orders | 778 |
| purchase_order_items | 1,952 |
| fx_rates | 4,384 |
| quality_incidents | 106 |
| inventory_snapshots | 1,800 |
| payables_summary | 36 |
| receivables_summary | 36 |
| dim_date | 1,461 |
| dim_supplier | 8 |
| dim_material | 50 |
| fact_procurement | 1,952 |
| supplier_spend_summary | 24 |
| supplier_performance_metrics | 8 |
| financial_kpis | 1 |
| fx_simulation_results | 9 |

---

## 13. File Manifest

### Final Project Structure (after cleanup)
```
procurement-intelligence-engine/
├── .github/
│   ├── copilot-instructions.md
│   └── workflows/
│       └── python-app.yml            # CI: Python 3.13, pytest
├── .streamlit/
│   ├── config.toml                   # Theme + server settings
│   ├── secrets.toml                  # (gitignored) Real credentials
│   └── secrets.toml.example          # Template for credentials
├── analytics/
│   └── advanced_analytics.py         # Monte Carlo FX + risk scoring (279 lines)
├── database/
│   └── add_constraints_migration.sql # FK + CHECK constraints (288 lines)
├── data_ingestion/
│   ├── seed_realistic_data.py        # Live FX + realistic data gen (504 lines)
│   └── populate_warehouse.py         # Star-schema ETL (477 lines)
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_advanced_analytics.py    # Analytics unit tests
│   ├── test_config.py               # Config module tests
│   ├── test_data_ingestion.py        # ETL module tests
│   └── test_integration.py          # DB connectivity + table tests
├── .gitignore
├── config.py                         # DB connection (20 lines)
├── docker-compose.yml                # Streamlit + MySQL stack
├── Dockerfile                        # Streamlit container
├── PROJECT_WALKTHROUGH.md            # This document
├── pytest.ini                        # pytest configuration
├── README.md                         # Quick-start guide
├── requirements.txt                  # 8 Python dependencies
└── streamlit_app.py                  # 7-page executive dashboard (724 lines)
```

### Dependencies (`requirements.txt`)
```
pandas          # Data manipulation
numpy           # Numerical computation + Monte Carlo
sqlalchemy      # Database ORM
pymysql         # MySQL driver
cryptography    # SSL for DB connections
streamlit       # Dashboard framework
plotly          # Interactive charts
requests        # Live FX API calls
```

---

*End of walkthrough. Generated February 20, 2026.*
