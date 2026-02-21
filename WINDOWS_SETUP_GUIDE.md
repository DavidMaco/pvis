# Windows Setup Guide for PVIS

This guide explains how to run the Procurement Intelligence System on Windows with PowerShell.

## Prerequisites

- **Windows 10 / Windows 11** with PowerShell 5.1 or higher
- **Python 3.13+** (download from [python.org](https://www.python.org/))
- **MySQL 8.0+** (running locally or on a network server)
- **Git** (optional, for cloning the repository)

---

## Step 1: Clone Repository

```powershell
# Clone from GitHub
git clone https://github.com/DavidMaco/Procurement_Intelligence_Proj1.git
cd Procurement_Intelligence_Proj1
```

Or download as ZIP and extract to your desired folder.

---

## Step 2: Create Virtual Environment

In PowerShell, navigate to the project root directory, then:

```powershell
# Create Python virtual environment
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# If you get an error about script execution policy, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

You should see `(.venv)` prefix in your PowerShell prompt when activated.

---

## Step 3: Install Dependencies

```powershell
# Install all required Python packages
pip install -r requirements.txt

# Verify installation
pip list
```

Key packages installed:
- `streamlit` — Dashboard framework
- `sqlalchemy`, `pymysql` — Database connectivity
- `pandas`, `numpy` — Data processing
- `plotly` — Interactive charts
- `requests` — FX rate API calls

---

## Step 4: Configure MySQL Database

### Option A: Local MySQL (Running on your machine)

```powershell
# Connect to MySQL
mysql -u root -p

# Create the database
CREATE DATABASE pro_intel_2;
EXIT;
```

### Option B: Remote MySQL

Edit `.streamlit/secrets.toml` with your server details (see Step 5).

---

## Step 5: Configure Streamlit Secrets (Optional)

By default, the app uses hardcoded credentials:
- **Host:** localhost
- **User:** root
- **Password:** Maconoelle86
- **Database:** pro_intel_2

To use custom MySQL credentials:

```powershell
# Copy the template
cp .streamlit\secrets.toml.example .streamlit\secrets.toml

# Edit with your credentials (use Notepad or your editor)
notepad .streamlit\secrets.toml
```

Update the values:

```toml
[database]
host = "your_mysql_host"
port = 3306
user = "your_username"
password = "your_password"
name = "pro_intel_2"
```

Save and close the file. Streamlit will automatically read these credentials when you run the app.

---

## Step 6: Seed Data (Choose One Option)

### Option A: Use Demo Sample Data

```powershell
# Generate realistic 3-year procurement data with live FX rates
python data_ingestion\seed_realistic_data.py

# Build the warehouse (star schema)
python data_ingestion\populate_warehouse.py

# Run analytics (Monte Carlo + supplier risk scoring)
python analytics\advanced_analytics.py
```

**Time:** ~2-5 minutes for first complete run.

### Option B: Import Your Own Company Data

```powershell
# Create company_data directory with your CSVs
mkdir company_data

# Copy template CSVs from external_data_samples and customize
# (See EXTERNAL_DATA_GUIDE.md for format specifications)

# Import your data
python data_ingestion\external_data_loader.py --input-dir .\company_data

# Build the warehouse
python data_ingestion\populate_warehouse.py

# Run analytics
python analytics\advanced_analytics.py
```

---

## Step 7: Run the Streamlit Dashboard

### Quickest Way

```powershell
.\RUN_STREAMLIT.ps1
```

This PowerShell script will:
1. ✓ Activate the virtual environment
2. ✓ Check Streamlit configuration
3. ✓ Verify dependencies
4. ✓ Launch the dashboard

### Manual Way

```powershell
# Ensure virtual env is activated
.\.venv\Scripts\Activate.ps1

# Launch dashboard
streamlit run streamlit_app.py
```

The dashboard will automatically open at **http://localhost:8501** in your default browser.

---

## Navigation in Dashboard

| Page | Purpose |
|------|---------|
| **Executive Summary** | KPIs: Total spend, FX exposure, risk score, CCC, live USD/NGN rate |
| **FX Volatility & Monte Carlo** | 90-day FX forecasts with 10K simulation paths |
| **Supplier Risk Analysis** | Risk heatmap, lead time volatility, performance metrics |
| **Spend & Cost Analysis** | Spend by supplier/category, cost leakage detection |
| **Working Capital** | Inventory, payables, receivables, cash conversion cycle |
| **Scenario Planning** | FX stress testing, negotiation insights |
| **Pipeline Runner** | Manually trigger ETL stages and analytics |

---

## Running Tests

```powershell
# Install pytest (if not already installed)
pip install pytest

# Run all tests
python -m pytest tests\ -v

# Run specific test file
python -m pytest tests\test_analytics.py -v

# Run with coverage report
python -m pytest tests\ --cov=. --cov-report=html
```

Expected: **12 tests passing** ✓

---

## Troubleshooting

### Error: "No module named 'streamlit'"

**Solution:**
```powershell
# Ensure virtual env is activated
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

### Error: "Can't connect to MySQL server"

**Possible causes & solutions:**

1. **MySQL not running:**
   ```powershell
   # On Windows, MySQL runs as a service
   # Start it from Services.msc or command line
   NET START MySQL80
   ```

2. **Wrong credentials:**
   - Check `.streamlit/secrets.toml` exists and has correct password
   - Or verify default credentials (root / Maconoelle86)

3. **Database doesn't exist:**
   ```powershell
   mysql -u root -p
   CREATE DATABASE pro_intel_2;
   EXIT;
   ```

### Error: "Script execution disabled"

**Solution:**
```powershell
# Allow PowerShell scripts for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify it worked
Get-ExecutionPolicy
# Should show: RemoteSigned
```

### Error: "No FX data found" or "Empty tables"

**Solution:** You haven't seeded data yet. Run:
```powershell
python data_ingestion\seed_realistic_data.py
python data_ingestion\populate_warehouse.py
python analytics\advanced_analytics.py
```

### Dashboard runs but shows "Database query failed"

**Check MySQL:**
```powershell
# Verify database exists and has tables
mysql -u root -p pro_intel_2
SHOW TABLES;
SELECT COUNT(*) FROM fact_procurement;
```

If tables are empty, run the seed/ETL pipeline again.

---

## Common Commands Cheatsheet

| Task | Command |
|------|---------|
| Activate venv | `.\.venv\Scripts\Activate.ps1` |
| Deactivate venv | `deactivate` |
| Run Streamlit | `streamlit run streamlit_app.py` |
| Seed data | `python data_ingestion\seed_realistic_data.py` |
| Build warehouse | `python data_ingestion\populate_warehouse.py` |
| Run analytics | `python analytics\advanced_analytics.py` |
| Import external data | `python data_ingestion\external_data_loader.py --input-dir .\company_data` |
| Run tests | `python -m pytest tests\ -v` |
| Quick launcher | `.\RUN_STREAMLIT.ps1` |

---

## Next Steps

1. **Explore the dashboard:** Navigate all 7 pages and understand the KPIs
2. **Run Monte Carlo:** Select a currency, adjust parameters, run simulations
3. **Analyze suppliers:** Review risk scores and performance metrics
4. **Import company data:** See EXTERNAL_DATA_GUIDE.md for your procurement data format
5. **Customize:** Modify dashboards, add metrics, or extend analytics

---

## Support

- **PVIS Repository:** [DavidMaco/Procurement_Intelligence_Proj1](https://github.com/DavidMaco/Procurement_Intelligence_Proj1)
- **Streamlit Docs:** [docs.streamlit.io](https://docs.streamlit.io)
- **MySQL Docs:** [dev.mysql.com](https://dev.mysql.com)

---

*Last updated: February 21, 2026*
