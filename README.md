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

### Setup (Windows/PowerShell)

**QUICKEST: Use the launcher script**
```powershell
# Clone and setup (one-time)
git clone https://github.com/DavidMaco/Procurement_Intelligence_Proj1.git
cd Procurement_Intelligence_Proj1
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# [Optional] Configure custom MySQL credentials
cp .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit .streamlit\secrets.toml with your credentials if needed

# Seed sample data
python data_ingestion\seed_realistic_data.py
python data_ingestion\populate_warehouse.py
python analytics\advanced_analytics.py

# ✓ Launch dashboard with auto-setup
.\RUN_STREAMLIT.ps1
# Opens automatically at http://localhost:8501
```

**MANUAL: Step-by-step**
```powershell
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed data (generates realistic 3-year procurement data with live FX rates)
python data_ingestion\seed_realistic_data.py

# 4. Populate warehouse (star-schema ETL)
python data_ingestion\populate_warehouse.py

# 5. Run analytics (Monte Carlo + supplier risk scoring)
python analytics\advanced_analytics.py

# 6. Launch dashboard
streamlit run streamlit_app.py
# Opens at http://localhost:8501
```

**FULL GUIDE:** See [WINDOWS_SETUP_GUIDE.md](WINDOWS_SETUP_GUIDE.md) for detailed Windows/PowerShell instructions.

### Run Tests

```powershell
pip install pytest
python -m pytest tests\ -v
```

## Using Your Own Data (External Import)

PVIS can now import your company's actual procurement data instead of using generated seed data.

### Quick Start with External Data

```powershell
# 1. Prepare CSV files (see external_data_samples\ for templates)
mkdir .\company_data
# Copy/edit: suppliers.csv, materials.csv, purchase_orders.csv, purchase_order_items.csv

# 2. Import your data
python data_ingestion\external_data_loader.py --input-dir .\company_data

# 3. Build warehouse (same as seed workflow)
python data_ingestion\populate_warehouse.py

# 4. Launch dashboard
streamlit run streamlit_app.py
```

### Format & Validation

- See `EXTERNAL_DATA_GUIDE.md` for complete CSV specifications
- See `external_data_samples/` for example files ready to customize
- The loader validates all inputs before importing

**Required Files:**
- `suppliers.csv` — supplier details, country, lead times, defect rates
- `materials.csv` — material name, category, unit cost
- `purchase_orders.csv` — PO header (date, supplier, amount, currency)
- `purchase_order_items.csv` — PO line items (quantity, unit price per material)

**Optional:**
- `fx_rates.csv` — historical FX rates (auto-generated if omitted)

### Workflow Comparison

| Step | Seed Mode (Default) | External Mode |
|------|-------------------|----------------|
| Generate Data | `seed_realistic_data.py` | Manual CSV prep |
| Import Data | (automated) | `external_data_loader.py` |
| Warehouse ETL | `populate_warehouse.py` | `populate_warehouse.py` |
| Analytics | `advanced_analytics.py` | `advanced_analytics.py` |
| Dashboard | `streamlit run streamlit_app.py` | `streamlit run streamlit_app.py` |

---

## Deployment (Docker)

**On Windows:**
```powershell
docker-compose up --build
# Dashboard at http://localhost:8501
```

**Prerequisites:** Docker Desktop for Windows installed and running.

## Repository Structure

```
├── streamlit_app.py              # 7-page Streamlit executive dashboard
├── RUN_STREAMLIT.ps1             # Windows: Quick launcher script
├── config.py                     # DB connection (Streamlit secrets / env fallback)
├── WINDOWS_SETUP_GUIDE.md        # Windows/PowerShell setup instructions
├── EXTERNAL_DATA_GUIDE.md        # Complete CSV import guide
├── analytics/
│   └── advanced_analytics.py     # Monte Carlo FX sim + supplier risk scoring
├── data_ingestion/
│   ├── seed_realistic_data.py    # 3-year realistic data generator (live FX)
│   ├── external_data_loader.py   # CSV import with validation
│   └── populate_warehouse.py     # Star-schema ETL pipeline
├── external_data_samples/        # Template CSV files for external import
│   ├── suppliers.csv
│   ├── materials.csv
│   ├── purchase_orders.csv
│   ├── purchase_order_items.csv
│   └── README.md
├── database/
│   └── add_constraints_migration.sql  # FK/CHECK constraints + indexes
├── tests/                        # pytest suite (12 tests)
├── .streamlit/
│   ├── config.toml               # Streamlit theme and server settings
│   └── secrets.toml.example      # MySQL credentials template
├── .github/workflows/
│   └── python-app.yml            # CI pipeline
├── Dockerfile                    # Streamlit container
├── docker-compose.yml            # Full stack (app + MySQL)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
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

*Last updated: February 21, 2026*  
**Note:** For Streamlit dashboard standalone execution on Windows, see [WINDOWS_SETUP_GUIDE.md](WINDOWS_SETUP_GUIDE.md) and use `RUN_STREAMLIT.ps1`
