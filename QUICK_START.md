# Quick Start Commands for Your System

## Issue Summary
- ❌ MySQL CLI not installed → Can't use `< database/file.sql` syntax
- ❌ Commands run from wrong directory
- ✅ PyMySQL now installed as workaround

---

## Corrected Execution Commands

### From PowerShell (Current Directory: VSCode Projects)

```powershell
# Navigate to project directory
cd procurement-intelligence-engine

# 1. Apply Database Constraints (via Python since MySQL CLI unavailable)
python -c "import pymysql; conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='Maconoelle86', database='pro_intel_2'); cur = conn.cursor(); print('Applying constraints...'); sql = open('database/add_constraints_migration.sql', 'r', encoding='utf-8').read(); stmts = [s.strip() for s in sql.split(';') if s.strip() and len(s.strip()) > 10 and not s.strip().startswith('--')]; success = 0; [cur.execute(stmt) or conn.commit() or success := success + 1 for stmt in stmts if 'SELECT' not in stmt[:50].upper() and not any(x in stmt for x in ['/*', 'SECTION', 'USE '])]; print(f'Applied {success} constraints'); conn.close()"

# 2. Generate Sample Data (24 months of realistic procurement data)
python data_ingestion/generate_sample_data.py

# 3. Populate Data Warehouse (ETL pipeline)
python data_ingestion/populate_warehouse.py

# 4. Run Advanced Analytics (FX simulation + risk scoring)
python analytics/advanced_analytics.py

# 5. Verify Setup
python verify_setup.py
```

---

## Simplified One-Line Execution

If the above multi-step commands already ran (even if output was truncated), just verify:

```powershell
python verify_setup.py
```

**Expected Output:**
```
======================================================================
DATABASE VERIFICATION STATUS
======================================================================
✓        dim_date                                  1,461 rows
✓        dim_supplier                                  3 rows
✓        dim_material                                  3 rows
✓        fact_procurement                          2,534 rows
✓        supplier_performance_metrics                  3 rows
✓        supplier_spend_summary                        6 rows
✓        fx_simulation_results                         1 rows
✓        purchase_orders                             720 rows
✓        purchase_order_items                      2,534 rows
✓        fx_rates                                  2,190 rows
✓        quality_incidents                           150 rows
======================================================================

FOREIGN KEY CONSTRAINTS:
Foreign Keys: 15
Indexes: 25
======================================================================

✓ Verification complete!
```

---

## Alternative: Use Batch Script

```powershell
# Run all 5 steps automatically
.\run_setup.bat
```

---

## If You Have MySQL CLI Installed

If you later install MySQL CLI tools, you can use the original command:

```powershell
# Get MySQL from: https://dev.mysql.com/downloads/mysql/
# Then use:
Get-Content database\add_constraints_migration.sql | mysql -h 127.0.0.1 -P 3306 -u root -pMaconoelle86 pro_intel_2
```

---

## Troubleshooting

### "No such file or directory"
- **Fix**: Run `pwd` to check you're in `procurement-intelligence-engine` folder
- **Command**: `cd procurement-intelligence-engine` first

### "Table doesn't exist"
- **Fix**: Ensure your MySQL schema has all 18 tables created first
- **Check**: `python -c "import pymysql; c=pymysql.connect(host='127.0.0.1',port=3306,user='root',password='Maconoelle86',db='pro_intel_2'); r=c.cursor(); r.execute('SHOW TABLES'); print([x[0] for x in r.fetchall()]); c.close()"`

### "Foreign key constraint fails"
- **Fix**: Run scripts in order (constraints → data → ETL → analytics)
- **Rollback**: See migration script comments for DROP commands

### Terminal output truncated
- **Fix**: Check individual script outputs in terminal history or run `verify_setup.py`

---

## What Each Script Does

| Script | Purpose | Duration | Output |
|--------|---------|----------|--------|
| **add_constraints_migration.sql** | Adds 15 FKs, 17 CHECKs, 7 indexes | ~5 sec | Schema hardening |
| **generate_sample_data.py** | Creates 24mo of POs, FX rates, incidents | ~30 sec | 5,000+ transactional records |
| **populate_warehouse.py** | Builds dimensions & facts (ETL) | ~15 sec | Star schema ready for Power BI |
| **advanced_analytics.py** | FX Monte Carlo + supplier risk | ~10 sec | Simulation results + risk scores |
| **verify_setup.py** | Checks all tables populated | ~2 sec | Status report |

---

##PowerShell Terminal Output Issue

If you see `[... PREVIOUS OUTPUT TRUNCATED ...]` or large file references:
- ✅ Your commands likely **succeeded**
- ✅ Output was just too large for the terminal buffer
- ✅ Run `python verify_setup.py` to confirm success

---

## Next Steps After Successful Setup

1. **Connect Power BI:**
   - Server: `localhost:3306`
   - Database: `pro_intel_2`
   - Auth: MySQL (`root` / `Maconoelle86`)

2. **Build Dashboards Using:**
   - `fact_procurement` (star schema grain)
   - `supplier_performance_metrics` (KPIs)
   - `fx_simulation_results` (forecasts)
   - `dim_date`, `dim_supplier`, `dim_material` (slicers)

3. **Schedule Weekly Refresh:**
   ```powershell
   # Add to Windows Task Scheduler
   python data_ingestion/populate_warehouse.py
   python analytics/advanced_analytics.py
   ```

---

**📁 All scripts are in:** `procurement-intelligence-engine/`  
**📖 Full documentation:** See `SETUP_GUIDE.md` and `IMPLEMENTATION_SUMMARY.md`
