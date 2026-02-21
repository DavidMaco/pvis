# ============================================================================
# PVIS Streamlit Dashboard Launcher (Windows PowerShell)
# ============================================================================
# 
# This script sets up the environment and launches the Streamlit dashboard.
# Usage: .\RUN_STREAMLIT.ps1
#

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " PVIS - Procurement Intelligence System                    " -ForegroundColor Cyan
Write-Host " Streamlit Dashboard Launcher                              " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Activate virtual environment
Write-Host "[1/5] Activating virtual environment..." -ForegroundColor Yellow
$venvPath = ".\.venv\Scripts\Activate.ps1"
$venvPathParent = "..\.venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    . $venvPath
    Write-Host "SUCCESS: Virtual environment activated (project local)" -ForegroundColor Green
} elseif (Test-Path $venvPathParent) {
    Push-Location
    Set-Location "..\"
    . ".venv\Scripts\Activate.ps1"
    Pop-Location
    Write-Host "SUCCESS: Virtual environment activated (workspace shared)" -ForegroundColor Green
} else {
    Write-Host "ERROR: Virtual environment not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Searched locations:" -ForegroundColor Yellow
    Write-Host "  1. $venvPath (project-local)"
    Write-Host "  2. $venvPathParent (workspace-shared)"
    Write-Host ""
    Write-Host "To create a virtual environment, run ONE of:" -ForegroundColor Yellow
    Write-Host "  Option A (project-local):" -ForegroundColor Cyan
    Write-Host "    python -m venv .venv" -ForegroundColor Cyan
    Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Option B (use existing workspace venv):" -ForegroundColor Cyan
    Write-Host "    cd ..\" -ForegroundColor Cyan
    Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host "    cd procurement-intelligence-engine" -ForegroundColor Cyan
    Write-Host "    pip install -r requirements.txt" -ForegroundColor Cyan
    exit 1
}

# Step 2: Check if secrets.toml exists
Write-Host ""
Write-Host "[2/5] Checking Streamlit secrets configuration..." -ForegroundColor Yellow
if (!(Test-Path ".\.streamlit\secrets.toml")) {
    Write-Host "WARNING: .streamlit/secrets.toml not found." -ForegroundColor Magenta
    Write-Host "   The app will use default credentials:" -ForegroundColor Magenta
    Write-Host "   - Host: localhost" -ForegroundColor Magenta
    Write-Host "   - User: root" -ForegroundColor Magenta
    Write-Host "   - Database: pro_intel_2" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "   To customize credentials:" -ForegroundColor Magenta
    Write-Host "   1. Copy: cp .\.streamlit\secrets.toml.example .\.streamlit\secrets.toml" -ForegroundColor Cyan
    Write-Host "   2. Edit: .\.streamlit\secrets.toml with your MySQL password" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "SUCCESS: Secrets configured" -ForegroundColor Green
}

# Step 3: Check database connectivity
Write-Host ""
Write-Host "[3/5] Checking database connectivity..." -ForegroundColor Yellow
try {
    # Try importing pymysql to verify installation
    $pythonTest = python -c "import pymysql; print('PyMySQL installed')" 2>&1
    Write-Host "SUCCESS: Dependencies OK" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Missing dependencies" -ForegroundColor Red
    Write-Host "  Run: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Step 4: Check if data has been seeded
Write-Host ""
Write-Host "[4/5] Checking if data has been seeded..." -ForegroundColor Yellow
Write-Host "   (This check is informational only)" -ForegroundColor Gray
Write-Host "   If this is your first run, use external data or seed mode:" -ForegroundColor Gray
Write-Host ""
Write-Host "   OPTION A: Use sample seed data (demo):" -ForegroundColor Cyan
Write-Host "     python data_ingestion\seed_realistic_data.py" -ForegroundColor Cyan
Write-Host "     python data_ingestion\populate_warehouse.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "   OPTION B: Use your own company data:" -ForegroundColor Cyan
Write-Host "     1. Prepare CSVs in ./company_data/ (see external_data_samples/)" -ForegroundColor Cyan
Write-Host "     2. python data_ingestion\external_data_loader.py --input-dir .\company_data" -ForegroundColor Cyan
Write-Host "     3. python data_ingestion\populate_warehouse.py" -ForegroundColor Cyan
Write-Host ""

# Step 5: Launch Streamlit
Write-Host "[5/5] Launching Streamlit dashboard..." -ForegroundColor Yellow

# Check if Streamlit is already running on port 8501
$streamlitProcesses = Get-Process -Name streamlit -ErrorAction SilentlyContinue
if ($streamlitProcesses) {
    Write-Host "WARNING: Streamlit is already running. Stopping existing instance..." -ForegroundColor Magenta
    Stop-Process -Name streamlit -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " Dashboard will open at: http://localhost:8501              " -ForegroundColor Green
Write-Host " Press Ctrl+C to stop the server                            " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

streamlit run streamlit_app.py
