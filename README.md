# Procurement Intelligence Engine

A production-grade procurement intelligence system for manufacturing organizations built on Python, MySQL, and Streamlit. Features FX volatility monitoring (Monte Carlo simulation), composite supplier risk scoring, spend analysis, working capital optimization, and an interactive 7-page executive dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LIVE FX APIs                            │
│   open.er-api.com → exchangerate-api.com → frankfurter.app │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│           DATA GENERATION  (seed_realistic_data.py)         │
│   FX rates · Purchase orders · Quality incidents            │
│   Inventory snapshots · Payables/Receivables                │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│           STAR-SCHEMA ETL  (populate_warehouse.py)          │
│   dim_date · dim_supplier · dim_material                    │
│   fact_procurement · spend summary · risk metrics · KPIs    │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│           ANALYTICS ENGINE  (advanced_analytics.py)         │
│   Monte Carlo FX simulation (10K paths × 90 days)          │
│   Composite supplier risk scoring (5 weighted factors)      │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│           STREAMLIT DASHBOARD  (streamlit_app.py)           │
│   7 pages: Executive · FX · Risk · Spend · Working Capital  │
│   Scenario Planning · Pipeline Runner                       │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Database | MySQL 8.0 (`pro_intel_2`) — 19 tables |
| ORM | SQLAlchemy + PyMySQL |
| Data Processing | pandas, NumPy |
| Simulation | NumPy (Geometric Brownian Motion) |
| FX Data | Live rates from open.er-api.com, exchangerate-api.com, Frankfurter |
| Dashboard | Streamlit 1.54 + Plotly |
| Deployment | Docker, GitHub Actions CI |

## Quickstart

### Prerequisites
- Python 3.13+
- MySQL 8.0+ with database `pro_intel_2` created
- Git

### Setup

```powershell
# Clone and install
git clone https://github.com/DavidMaco/Procurement_Intelligence_Proj1.git
cd Procurement_Intelligence_Proj1

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure database credentials
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your MySQL password

# Seed data (fetches live FX rates)
python data_ingestion/seed_realistic_data.py

# Build star-schema warehouse
python data_ingestion/populate_warehouse.py

# Run analytics (Monte Carlo + risk scoring)
python analytics/advanced_analytics.py

# Launch dashboard
streamlit run streamlit_app.py
# Open http://localhost:8501
```

### Run Tests

```powershell
pip install pytest
python -m pytest tests/ -v
```

## Deployment (Docker)

```bash
docker-compose up --build
# Dashboard at http://localhost:8501
```

## Repository Structure

```
├── streamlit_app.py              # 7-page Streamlit executive dashboard
├── config.py                     # DB connection (Streamlit secrets / env fallback)
├── analytics/
│   └── advanced_analytics.py     # Monte Carlo FX sim + supplier risk scoring
├── data_ingestion/
│   ├── seed_realistic_data.py    # 3-year realistic data generator (live FX)
│   └── populate_warehouse.py     # Star-schema ETL pipeline
├── database/
│   └── add_constraints_migration.sql  # FK/CHECK constraints + indexes
├── tests/                        # pytest suite (12 tests)
├── .streamlit/
│   ├── config.toml               # Theme and server settings
│   └── secrets.toml.example      # Credentials template
├── .github/workflows/
│   └── python-app.yml            # CI pipeline
├── Dockerfile                    # Streamlit container
├── docker-compose.yml            # Full stack (app + MySQL)
├── requirements.txt              # Python dependencies
└── PROJECT_WALKTHROUGH.md        # Detailed build history
```

## Data Model

**Transactional tables:** countries, currencies, suppliers, materials, purchase_orders, purchase_order_items, fx_rates, quality_incidents, inventory_snapshots, payables_summary, receivables_summary

**Warehouse tables:** dim_date, dim_supplier, dim_material, fact_procurement, supplier_spend_summary, supplier_performance_metrics, financial_kpis, fx_simulation_results

## Key Metrics

| Metric | Description |
|--------|-------------|
| Composite Risk Score | Weighted: 30% lead time + 35% defects + 25% OTD + 10% FX exposure |
| Monte Carlo P5/P50/P95 | 10,000-path GBM simulation over 90 trading days |
| Cash Conversion Cycle | DIO − DPO (days inventory outstanding − days payable outstanding) |
| On-Time Delivery % | `actual_lead_time ≤ published_lead_time_days` |

## GitHub

Repository: [DavidMaco/Procurement_Intelligence_Proj1](https://github.com/DavidMaco/Procurement_Intelligence_Proj1)

---

*Last updated: February 20, 2026*
