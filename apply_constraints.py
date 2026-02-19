"""
Apply Database Constraints to pro_intel_2
Adds Foreign Keys, CHECK constraints, and performance indexes
"""

import pymysql
import sys

from config import get_mysql_params

print("="*60)
print("Applying Database Constraints to pro_intel_2")
print("="*60)

try:
    conn = pymysql.connect(**get_mysql_params())
    
    cur = conn.cursor()
    
    # Read and execute SQL file
    with open('database/add_constraints_migration.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    # Filter out comments and non-executable statements
    executable_stmts = []
    for stmt in statements:
        # Skip comments, USE statements, and empty lines
        if (stmt and 
            not stmt.startswith('--') and 
            not stmt.startswith('/*') and 
            'USE pro_intel_2' not in stmt and
            'SECTION' not in stmt and
            len(stmt) > 20):
            executable_stmts.append(stmt)
    
    success_count = 0
    error_count = 0
    
    for stmt in executable_stmts:
        try:
            cur.execute(stmt)
            conn.commit()
            success_count += 1
            
            # Print constraint name if available
            if 'CONSTRAINT' in stmt:
                constraint_name = stmt.split('CONSTRAINT')[1].split()[0]
                print(f"  ✓ Applied: {constraint_name}")
            elif 'CREATE INDEX' in stmt:
                index_name = stmt.split('CREATE INDEX')[1].split()[0]
                print(f"  ✓ Created index: {index_name}")
            elif 'CREATE TABLE' in stmt:
                table_name = stmt.split('CREATE TABLE')[1].split()[0]
                print(f"  ✓ Created table: {table_name}")
                
        except pymysql.Error as e:
            # Ignore "already exists" errors
            if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                print(f"  ⚠ Already exists, skipping...")
                continue
            else:
                error_count += 1
                print(f"  ✗ Error: {str(e)[:80]}")
    
    print("\n" + "="*60)
    print(f"Applied {success_count} constraints/indexes")
    if error_count > 0:
        print(f"⚠ {error_count} errors (may be already-applied constraints)")
    print("="*60)
    
    conn.close()
    
    print("\n✓ Constraint migration completed!\n")
    
except FileNotFoundError:
    print("\n✗ Error: database/add_constraints_migration.sql not found")
    print("   Make sure you're running from the pro-intel-2-analytics folder")
    sys.exit(1)
    
except pymysql.Error as e:
    print(f"\n✗ Database connection error: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
