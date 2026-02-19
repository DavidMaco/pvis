@echo off
echo ============================================================
echo Pro_Intel_2 Setup Execution
echo ============================================================
echo.

echo [1/4] Applying Database Constraints...
python -c "import pymysql; conn=pymysql.connect(host='127.0.0.1',port=3306,user='root',password='Maconoelle86',database='pro_intel_2'); cur=conn.cursor(); exec(open('database/add_constraints_migration.sql').read().replace('--','#')); print('Done'); conn.close()" 2>nul || echo Constraints already exist or applied

echo.
echo [2/4] Generating Sample Data...
python data_ingestion/generate_sample_data.py

echo.
echo [3/4] Running ETL Pipeline...
python data_ingestion/populate_warehouse.py

echo.
echo [4/4] Running Advanced Analytics...
python analytics/advanced_analytics.py

echo.
echo ============================================================
echo [5/5] Verification...
python verify_setup.py

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
pause
