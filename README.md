# PVIS: Procurement Volatility Intelligence System

![PVIS Logo](https://img.icons8.com/fluency/128/combo-chart.png)

**A procurement analytics platform that combines Monte Carlo simulation, real-time FX monitoring, composite supplier risk scoring, and working capital optimization in a single executive dashboard.**

[![CI](https://github.com/DavidMaco/pvis/actions/workflows/python-app.yml/badge.svg)](https://github.com/DavidMaco/pvis/actions)
![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue?logo=python&logoColor=white)
![MySQL 8.0](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.54-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit_Cloud-FF4B4B?logo=streamlit&logoColor=white)](https://davidmaco-pvis.streamlit.app)

[Live Demo](#-live-demo) • [Features](#-key-features) • [Architecture](#-architecture) • [Getting Started](#-getting-started) • [Dashboard](#-dashboard-pages) • [Your Data](#-import-your-company-data) • [Deploy](#-deployment) • [Data Model](#-data-model) • [Contributing](#-contributing)

---

## 🎯 Live Demo

> **[▶ Launch PVIS Dashboard](https://davidmaco-pvis.streamlit.app)**
>
> The live demo runs on Streamlit Cloud with Aiven MySQL. All 8 pages are fully interactive. Explore FX simulations, supplier risk heatmaps, spend analysis, and more.

---

## 🧠 What Problem Does PVIS Solve?

Manufacturing procurement teams face three critical blind spots:

| Blind Spot | Business Impact | PVIS Solution |
| :--- | :--- | :--- |
| **FX Volatility** | A 15% NGN devaluation can wipe out ₦180M+ in margin on a single quarter | Regime-weighted Monte Carlo simulation (10K-50K paths) with live API rates, P5/P50/P95 bands, and VaR/CVaR |
| **Supplier Risk** | Late deliveries and defects cascade into production stoppages | Composite risk scoring (6 weighted factors including geographic risk index) with automated negotiation playbooks |
| **Cash Leakage** | Cost variances against standard costs go undetected across 1,000+ PO lines | Spend decomposition by supplier × category × year with leakage attribution |

PVIS turns raw procurement data into **actionable intelligence**. It provides specific recommendations on which contracts to renegotiate, where to hedge FX exposure, and how to optimize the cash conversion cycle.

---

## ✨ Key Features

### Analytics Engine

- **Regime-Weighted Monte Carlo FX Simulation:** Low/high volatility regime detection with separate drift and volatility estimates, then weighted-path simulation over up to 1,095 trading days
- **Composite Supplier Risk Scoring:** Weighted model: on-time delivery, defect rate, cost variance, FX sensitivity, lead-time consistency, and geographic risk index
- **Cash Conversion Cycle Optimization:** DIO/DPO modeling with target scenario recommendations
- **Landed Cost Model:** Base cost + freight + insurance + duties + FX impact + payment delay cost
- **Cost Leakage Detection:** Automated identification of unit-price vs. standard-cost variances by category
- **FX Stress Testing and Risk Metrics:** Interactive scenario planner, VaR/CVaR, and explicit FX shock sensitivity (±10%, ±20%)

### Data Platform

- **Live Exchange Rates:** Dual-API failover (open.er-api.com to frankfurter.dev), 150+ currencies including NGN
- **Star-Schema Data Warehouse:** Dimensional model (3 dimensions, 1 fact table) with ETL pipeline
- **3-Year Historical Backcast:** Realistic procurement data generator with configurable parameters
- **External Data Import:** CSV-based ingestion with validation for company data (suppliers, materials, POs)
- **Company Data Upload:** Interactive file uploader in the dashboard to run simulations on your own data

### Dashboard

- **8 Interactive Pages:** Executive Summary, FX Volatility & Monte Carlo, Supplier Risk Analysis, Spend & Cost Analysis, Working Capital, Scenario Planning, Company Data Upload, Pipeline Runner
- **Real-Time KPIs:** Live USD/NGN rate, total spend, FX exposure %, average risk score, CCC days, Procurement Cost Volatility Index, and Working Capital Forecast
- **Auto-Negotiation Playbooks:** Per-supplier action items generated from risk metrics
- **Demo Mode:** Full dashboard functionality with synthetic data when no database is connected
- **Decision Layer for Power BI:** Semantic SQL views for executive KPI cards, supplier risk heatmap, and scenario comparison

---

## 🏗 Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
│                                                                              │
│   📡 Live FX APIs              📁 Company CSV Upload        🏭 Seed Generator│
│   (open.er-api.com)            (st.file_uploader)           (synthetic 3yr)  │
│   (frankfurter.dev)                                                          │
└─────────┬──────────────────────────┬──────────────────────────┬──────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                                       │
│                                                                              │
│   external_data_loader.py    ◄── CSV validation + schema enforcement         │
│   seed_realistic_data.py     ◄── 3-year realistic data with live FX          │
│   rebuild_fx_historical.py   ◄── FX backfill from APIs                       │
│                                                                              │
│                  MySQL 8.0 with 19 transactional tables                      │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        WAREHOUSE LAYER                                       │
│                                                                              │
│   populate_warehouse.py      ◄── Star-schema ETL                             │
│                                                                              │
│   ┌──────────┐  ┌──────────────┐  ┌──────────────┐                          │
│   │ dim_date  │  │ dim_supplier │  │ dim_material │                          │
│   └─────┬────┘  └──────┬───────┘  └──────┬───────┘                          │
│         └──────────────┼──────────────────┘                                  │
│                        ▼                                                     │
│              ┌──────────────────┐                                            │
│              │ fact_procurement │  + supplier_spend_summary                   │
│              └──────────────────┘  + supplier_performance_metrics             │
│                                    + financial_kpis                           │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       ANALYTICS ENGINE                                       │
│                                                                              │
│   advanced_analytics.py                                                      │
│   ├── Monte Carlo FX Simulation  (regime-weighted GBM, configurable paths)   │
│   ├── Composite Supplier Risk    (6-factor weighted scoring model)            │
│   ├── Spend Aggregation          (supplier × category × year)                │
│   └── Working Capital KPIs       (DIO, DPO, CCC optimization)               │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       PRESENTATION LAYER                                     │
│                                                                              │
│   streamlit_app.py: 8-page executive dashboard                               │
│                                                                              │
│   🏠 Executive Summary    📈 FX Monte Carlo      🏭 Supplier Risk            │
│   💰 Spend Analysis       🏦 Working Capital      🔄 Scenario Planning       │
│   📂 Company Data Upload  ⚙️ Pipeline Runner                                 │
│                                                                              │
│   Plotly charts • Live KPIs • Interactive sliders • File upload              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
| :------ | :----------- | :-------- |
| **Database** | MySQL 8.0 | 19-table transactional store + star-schema warehouse |
| **Cloud DB** | Aiven MySQL | Streamlit Cloud connectivity (free tier) |
| **ORM** | SQLAlchemy + PyMySQL | Connection pooling, parameterized queries |
| **Processing** | pandas · NumPy | DataFrame operations, statistical computation |
| **Simulation** | NumPy (GBM) | Geometric Brownian Motion Monte Carlo engine |
| **FX Data** | open.er-api.com · frankfurter.dev | Live rates for 150+ currencies, dual-API failover |
| **Dashboard** | Streamlit 1.54 + Plotly | Interactive visualizations, file upload, 8-page app |
| **CI/CD** | GitHub Actions | Automated testing on push/PR |
| **Containerization** | Docker + docker-compose | One-command full-stack deployment |
| **Language** | Python 3.13+ | Type hints, modern stdlib (tomllib, pathlib) |

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version | Check |
| :--- | :--- | :--- |
| Python | 3.13+ | `python --version` |
| MySQL | 8.0+ | `mysql --version` |
| Git | Any | `git --version` |

### One-Command Setup (Windows/PowerShell)

```powershell
# Clone
git clone https://github.com/DavidMaco/pvis.git
cd pvis

# Environment
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure database credentials
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit .streamlit\secrets.toml with your MySQL credentials

# Seed data → ETL → Analytics (one pipeline)
python data_ingestion\seed_realistic_data.py
python data_ingestion\populate_warehouse.py
python analytics\advanced_analytics.py

# Launch
.\RUN_STREAMLIT.ps1
```

> **No MySQL?** The dashboard detects the absence of a database and runs in **Demo Mode** with synthetic data.

### macOS / Linux

```bash
git clone https://github.com/DavidMaco/pvis.git && cd pvis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml, then:
python data_ingestion/seed_realistic_data.py
python data_ingestion/populate_warehouse.py
python analytics/advanced_analytics.py
streamlit run streamlit_app.py
```

### Run Tests

```powershell
pip install pytest
python -m pytest tests/ -v
```

---

## 📊 Dashboard Pages

### 1. 🏠 Executive Summary

Real-time KPI cards (total spend, FX exposure %, avg risk score, CCC days, live USD/NGN rate, Procurement Cost Volatility Index) plus Working Capital Forecast, scenario delta, supplier risk ranking, monthly trend, and supplier risk heatmap.

### 2. 📈 FX Volatility & Monte Carlo

Select any currency, configure horizon (30-1,095 days) and simulations (1K-50K paths). Renders historical rate chart with live marker, regime-weighted P5/P50/P95 fan chart, terminal distribution, VaR/CVaR, and FX shock sensitivity (±10%, ±20%).

### 3. 🏭 Supplier Risk Analysis

Normalized risk heatmap across core risk metrics, detailed performance table with conditional formatting, lead-time trend, cost-volatility trend, and country risk exposure map.

### 4. 💰 Spend & Cost Analysis

Spend donut charts by supplier and category, cost leakage waterfall by material category, annual spend grouped bar chart with year-over-year comparison.

### 5. 🏦 Working Capital

Inventory value trend, payables/receivables dual timeline, CCC breakdown (DIO/DPO), inventory turnover KPI, and CCC scenario simulation (Base, Stress, Optimized).

### 6. 🔄 Scenario Planning

Interactive FX stress test slider (-30% to +50%), landed cost model component breakdown, procurement volatility audit deliverables, multi-scenario comparison table, and per-supplier negotiation action playbooks.

---

## 📊 Power BI Decision Layer

PVIS now includes a Power BI semantic layer in `powerbi/`:

- `powerbi/pvis_decision_layer.sql`: Creates executive reporting views (`v_pvis_procurement_volatility`, `v_pvis_fx_exposure`, `v_pvis_supplier_risk`, `v_pvis_working_capital`, `v_pvis_scenario_comparison`)
- `powerbi/PVIS_Dashboard_BUILD.md`: Build guide, visual mapping, and starter DAX measures

### 7. 📂 Company Data Upload

Drag-and-drop file uploader for company CSV or ZIP data. It validates, processes, and runs the full analytics pipeline on your own procurement data from the browser.

### 8. ⚙️ Pipeline Runner

One-click buttons to regenerate seed data, run ETL, execute Monte Carlo simulation, and refresh supplier risk scores. Includes database health check with row counts for all 11 key tables.

---

## 📂 Import Your Company Data

PVIS supports two methods for using your own procurement data:

### Method A: Dashboard Upload (Recommended)

Navigate to the **📂 Company Data Upload** page in the dashboard and drag-and-drop your CSV files or a ZIP archive. The system validates, imports, runs ETL + analytics, and refreshes all dashboard pages automatically.

### Method B: Command-Line Import

```powershell
# Prepare CSVs (use external_data_samples/ as templates)
mkdir .\company_data

# Import → ETL → Analytics
python data_ingestion\external_data_loader.py --input-dir .\company_data
python data_ingestion\populate_warehouse.py
python analytics\advanced_analytics.py
```

### Required CSV Files

| File | Key Columns | Description |
| :----- | :------------ | :------------ |
| `suppliers.csv` | supplier_name, country, lead_time, defect_rate | Supplier master data |
| `materials.csv` | material_name, category, standard_cost | Material catalog |
| `purchase_orders.csv` | po_date, supplier, total_amount, currency | PO headers |
| `purchase_order_items.csv` | po_id, material, quantity, unit_price | PO line items |
| `fx_rates.csv` *(optional)* | rate_date, currency_code, rate_to_usd | Auto-generated if omitted |

See [EXTERNAL_DATA_GUIDE.md](EXTERNAL_DATA_GUIDE.md) and `external_data_samples/` for complete specs and templates.

---

## 🐳 Deployment

### Docker (One Command)

```powershell
docker-compose up --build
# Dashboard → http://localhost:8501
# MySQL → localhost:3306
```

### Streamlit Cloud

1. Fork/push to GitHub
2. Connect at [share.streamlit.io](https://share.streamlit.io)
3. Set **Secrets** (Settings → Secrets):

   ```toml
   [database]
   host = "your-cloud-mysql-host"
   port = 3306
   user = "your_user"
   password = "your_password"
   name = "your_database"
   ```

4. Deploy, or skip secrets to run in Demo Mode

---

## 🗄 Data Model

### Transactional Layer (19 Tables)

```text
countries ─┐
            ├── suppliers ──── purchase_orders ──── purchase_order_items
currencies ─┘                        │
                                     ├── fx_rates
                                     ├── quality_incidents
materials ───────────────────────────┘
                              
inventory_snapshots    payables_summary    receivables_summary
```

### Warehouse Layer (Star Schema)

```text
           dim_date
              │
dim_supplier ─┼── fact_procurement
              │
         dim_material

+ supplier_spend_summary
+ supplier_performance_metrics
+ financial_kpis
+ fx_simulation_results
```

### Key Metrics

| Metric | Formula / Method |
| :------- | :----------------- |
| **Composite Risk Score** | 0.30 × lead_time_vol + 0.35 × defect_rate + 0.25 × (1 − OTD%) + 0.10 × fx_exposure |
| **Monte Carlo FX** | GBM: S(t+1) = S(t) × exp((μ − σ²/2)Δt + σ√Δt × Z), Z ~ N(0,1) |
| **Cash Conversion Cycle** | CCC = DIO − DPO (days inventory outstanding − days payable outstanding) |
| **On-Time Delivery** | `COUNT(actual_lead ≤ published_lead) / COUNT(*)` |
| **Cost Leakage** | `Σ (unit_price − standard_cost) × quantity` where unit_price > standard_cost |

---

## 📁 Repository Structure

```text
pvis/
├── streamlit_app.py                  # 8-page Streamlit executive dashboard
├── demo_data.py                      # Synthetic data engine for demo mode
├── config.py                         # DB connection (secrets / env fallback)
├── RUN_STREAMLIT.ps1                 # Windows quick-launcher script
├── requirements.txt                  # Python dependencies (pinned)
├── Dockerfile                        # Streamlit container image
├── docker-compose.yml                # Full stack (app + MySQL)
│
├── analytics/
│   └── advanced_analytics.py         # Monte Carlo FX + supplier risk scoring
│
├── data_ingestion/
│   ├── seed_realistic_data.py        # 3-year data generator (live FX rates)
│   ├── external_data_loader.py       # CSV import with validation
│   ├── populate_warehouse.py         # Star-schema ETL pipeline
│   └── rebuild_fx_historical.py      # FX backfill utility
│
├── external_data_samples/            # Template CSVs for external import
│   ├── suppliers.csv
│   ├── materials.csv
│   ├── purchase_orders.csv
│   └── purchase_order_items.csv
│
├── database/
│   └── add_constraints_migration.sql # FK/CHECK constraints + indexes
│
├── tests/                            # pytest suite
│
├── .streamlit/
│   ├── config.toml                   # Theme & server settings
│   └── secrets.toml.example          # Credentials template
│
├── .github/workflows/
│   └── python-app.yml                # CI pipeline
│
├── EXTERNAL_DATA_GUIDE.md            # CSV import specifications
├── WINDOWS_SETUP_GUIDE.md            # Windows/PowerShell guide
├── FX_DATA_INTEGRITY.md              # FX data rebuild documentation
└── PROJECT_WALKTHROUGH.md            # Technical walkthrough
```

---

## 🔮 Roadmap

- [ ] Anomaly detection on supplier performance trends
- [ ] Multi-currency portfolio hedge optimizer
- [ ] Automated PDF report generation with executive summaries
- [ ] REST API layer for ERP integration (SAP, Oracle)
- [ ] Role-based access control (RBAC) for enterprise deployment
- [ ] Real-time alerting via Slack/Teams webhooks

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 👤 Author

### David Maco

- GitHub: [@DavidMaco](https://github.com/DavidMaco)

---

Built with ❤️ for procurement intelligence
