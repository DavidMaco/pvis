"""
External Data Loader for PVIS
Allows importing company procurement data from CSV files with schema validation.

USAGE:
    python data_ingestion/external_data_loader.py --input-dir ./company_data

EXPECTED STRUCTURE:
    company_data/
      ├─ suppliers.csv
      ├─ materials.csv
      ├─ purchase_orders.csv
      ├─ purchase_order_items.csv
      └─ (optional) fx_rates.csv

See EXTERNAL_DATA_GUIDE.md for detailed specifications.
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DATABASE_URL
except Exception:
    DATABASE_URL = "mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2"

engine = create_engine(DATABASE_URL)

# Schema validation rules
SCHEMA = {
    "suppliers": {
        "required": ["supplier_name", "country", "default_currency", "lead_time_days"],
        "optional": ["lead_time_stddev", "defect_rate_pct"],
        "types": {
            "supplier_name": str,
            "country": str,
            "default_currency": str,
            "lead_time_days": (int, float),
            "lead_time_stddev": (int, float),
            "defect_rate_pct": (int, float),
        }
    },
    "materials": {
        "required": ["material_name", "category", "standard_cost"],
        "optional": [],
        "types": {
            "material_name": str,
            "category": str,
            "standard_cost": (int, float),
        }
    },
    "purchase_orders": {
        "required": ["po_date", "supplier_name", "currency", "total_value"],
        "optional": ["po_number", "delivery_status"],
        "types": {
            "po_date": str,
            "supplier_name": str,
            "currency": str,
            "total_value": (int, float),
        }
    },
    "purchase_order_items": {
        "required": ["po_number", "material_name", "quantity", "unit_price"],
        "optional": [],
        "types": {
            "po_number": str,
            "material_name": str,
            "quantity": (int, float),
            "unit_price": (int, float),
        }
    },
}


class DataValidator:
    """Validates external data against schema requirements."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_file(self, file_path, file_type):
        """Validate a CSV file against schema."""
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            self.errors.append(f"Failed to read {file_type}: {e}")
            return False
        
        spec = SCHEMA.get(file_type)
        if not spec:
            self.errors.append(f"Unknown file type: {file_type}")
            return False
        
        # Check required columns
        missing = set(spec["required"]) - set(df.columns)
        if missing:
            self.errors.append(f"{file_type}: Missing required columns: {missing}")
            return False
        
        # Check for empty dataframe
        if df.empty:
            self.warnings.append(f"{file_type}: File is empty")
            return True
        
        # Type checking (lenient)
        for col in df.columns:
            if col in spec["types"]:
                expected = spec["types"][col]
                if not self._check_type(df[col], expected):
                    self.warnings.append(f"{file_type}.{col}: Found mixed types (lenient check passed)")
        
        # File-specific validations
        if file_type == "suppliers":
            self._validate_suppliers(df)
        elif file_type == "materials":
            self._validate_materials(df)
        elif file_type == "purchase_orders":
            self._validate_purchase_orders(df)
        elif file_type == "purchase_order_items":
            self._validate_po_items(df)
        
        return len(self.errors) == 0
    
    def _check_type(self, series, expected_type):
        """Check if series matches expected type(s)."""
        if isinstance(expected_type, tuple):
            return series.dtype in [np.int64, np.float64] or all(
                isinstance(x, expected_type) for x in series.dropna()
            )
        return True  # Lenient
    
    def _validate_suppliers(self, df):
        """Supplier-specific validation."""
        if "lead_time_days" in df.columns:
            invalid = df[df["lead_time_days"] <= 0]
            if not invalid.empty:
                self.errors.append(f"suppliers: lead_time_days must be positive")
    
    def _validate_materials(self, df):
        """Material-specific validation."""
        if "standard_cost" in df.columns:
            invalid = df[df["standard_cost"] < 0]
            if not invalid.empty:
                self.errors.append(f"materials: standard_cost cannot be negative")
    
    def _validate_purchase_orders(self, df):
        """PO-specific validation."""
        if "po_date" in df.columns:
            try:
                pd.to_datetime(df["po_date"])
            except Exception as e:
                self.errors.append(f"purchase_orders: invalid po_date format: {e}")
        
        if "total_value" in df.columns:
            invalid = df[df["total_value"] < 0]
            if not invalid.empty:
                self.errors.append(f"purchase_orders: total_value cannot be negative")
    
    def _validate_po_items(self, df):
        """PO Items-specific validation."""
        if "quantity" in df.columns:
            invalid = df[df["quantity"] <= 0]
            if not invalid.empty:
                self.warnings.append(f"purchase_order_items: quantity should be positive")
        
        if "unit_price" in df.columns:
            invalid = df[df["unit_price"] < 0]
            if not invalid.empty:
                self.errors.append(f"purchase_order_items: unit_price cannot be negative")


class ExternalDataLoader:
    """Load and import external company data into PVIS."""
    
    def __init__(self, input_dir):
        self.input_dir = Path(input_dir)
        self.validator = DataValidator()
        self.data = {}
    
    def load_all_files(self):
        """Load and validate all input CSV files."""
        required_files = ["suppliers", "materials", "purchase_orders", "purchase_order_items"]
        
        print(f"Loading external data from: {self.input_dir}")
        print()
        
        for file_type in required_files:
            file_path = self.input_dir / f"{file_type}.csv"
            
            if not file_path.exists():
                print(f"⚠ Missing: {file_type}.csv")
                continue
            
            print(f"Validating {file_type}.csv...", end=" ")
            if self.validator.validate_file(str(file_path), file_type):
                print("✓")
                self.data[file_type] = pd.read_csv(file_path)
            else:
                print("✗")
                for err in self.validator.errors:
                    print(f"  Error: {err}")
                self.validator.errors.clear()
        
        if self.validator.warnings:
            print()
            print("Warnings:")
            for warn in self.validator.warnings:
                print(f"  ⚠ {warn}")
            self.validator.warnings.clear()
        
        return len(self.data) == 4
    
    def import_data(self):
        """Import validated data into database."""
        if not self.data:
            print("No data to import.")
            return False
        
        try:
            print()
            print("Importing data into database...")
            
            with engine.connect() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                conn.commit()
            
            # Clear existing transactional tables (keep reference data)
            self._clear_tables()
            
            # Import each table
            self._import_suppliers()
            self._import_materials()
            self._import_purchase_orders()
            self._import_purchase_order_items()
            
            with engine.connect() as conn:
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                conn.commit()
            
            print()
            print("✓ External data imported successfully!")
            return True
        
        except Exception as e:
            print(f"✗ Import failed: {e}")
            return False
    
    def _clear_tables(self):
        """Clear transactional tables before import."""
        tables = [
            "fact_procurement", "supplier_performance_metrics",
            "supplier_spend_summary", "financial_kpis",
            "purchase_order_items", "purchase_orders",
            "quality_incidents", "inventory_snapshots",
            "payables_summary", "receivables_summary",
            "supplier_performance_metrics",
            "dim_supplier", "dim_material"
        ]
        with engine.connect() as conn:
            for table in tables:
                try:
                    conn.execute(text(f"DELETE FROM {table}"))
                    conn.commit()
                except:
                    pass
    
    def _import_suppliers(self):
        """Import suppliers."""
        df = self.data["suppliers"]
        
        # Map country names to IDs (or create new entries)
        country_map = self._get_country_map()
        currency_map = self._get_currency_map()
        
        df["country_id"] = df["country"].map(country_map)
        df["currency_id"] = df["default_currency"].map(currency_map)
        
        # Ensure required columns exist
        df["lead_time_stddev"] = df.get("lead_time_stddev", df["lead_time_days"] * 0.2)
        df["defect_rate_pct"] = df.get("defect_rate_pct", 2.0)
        
        insert_df = df[[
            "supplier_name", "country_id", "currency_id",
            "lead_time_days", "lead_time_stddev", "defect_rate_pct"
        ]].copy()
        insert_df.columns = [
            "supplier_name", "country_id", "currency_id",
            "lead_time_days", "lead_time_stddev", "defect_rate_pct"
        ]
        
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM suppliers"))
            conn.commit()
        
        insert_df.to_sql("suppliers", engine, if_exists="append", index=False)
        print(f"  ✓ Imported {len(insert_df)} suppliers")
    
    def _import_materials(self):
        """Import materials."""
        df = self.data["materials"]
        
        insert_df = df[["material_name", "category", "standard_cost"]].copy()
        
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM materials"))
            conn.commit()
        
        insert_df.to_sql("materials", engine, if_exists="append", index=False)
        print(f"  ✓ Imported {len(insert_df)} materials")
    
    def _import_purchase_orders(self):
        """Import purchase orders."""
        df = self.data["purchase_orders"].copy()
        
        supplier_map = self._get_supplier_map()
        currency_map = self._get_currency_map()
        
        df["supplier_id"] = df["supplier_name"].map(supplier_map)
        df["currency_id"] = df["currency"].map(currency_map)
        df["po_date"] = pd.to_datetime(df["po_date"]).dt.date
        
        # Auto-generate PO numbers if missing
        if "po_number" not in df.columns:
            df["po_number"] = ["PO-" + str(i).zfill(6) for i in range(1, len(df) + 1)]
        
        df["delivery_status"] = df.get("delivery_status", "DELIVERED")
        
        insert_df = df[[
            "po_number", "po_date", "supplier_id", "currency_id", "total_value", "delivery_status"
        ]].copy()
        
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM purchase_orders"))
            conn.commit()
        
        insert_df.to_sql("purchase_orders", engine, if_exists="append", index=False)
        print(f"  ✓ Imported {len(insert_df)} purchase orders")
    
    def _import_purchase_order_items(self):
        """Import purchase order items."""
        df = self.data["purchase_order_items"].copy()
        
        # Get mappings
        with engine.connect() as conn:
            po_df = pd.read_sql("SELECT po_id, po_number FROM purchase_orders", engine)
            mat_df = pd.read_sql("SELECT material_id, material_name FROM materials", engine)
        
        po_map = dict(zip(po_df["po_number"], po_df["po_id"]))
        mat_map = dict(zip(mat_df["material_name"], mat_df["material_id"]))
        
        df["po_id"] = df["po_number"].map(po_map)
        df["material_id"] = df["material_name"].map(mat_map)
        
        # Calculate line total
        df["line_total"] = df["quantity"] * df["unit_price"]
        
        insert_df = df[[
            "po_id", "material_id", "quantity", "unit_price", "line_total"
        ]].dropna(subset=["po_id", "material_id"])
        
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM purchase_order_items"))
            conn.commit()
        
        insert_df.to_sql("purchase_order_items", engine, if_exists="append", index=False)
        print(f"  ✓ Imported {len(insert_df)} purchase order items")
    
    def _get_country_map(self):
        """Get country name to ID mapping."""
        df = pd.read_sql("SELECT country_id, country_name FROM countries", engine)
        return dict(zip(df["country_name"].str.lower(), df["country_id"]))
    
    def _get_currency_map(self):
        """Get currency code to ID mapping."""
        df = pd.read_sql("SELECT currency_id, currency_code FROM currencies", engine)
        return dict(zip(df["currency_code"], df["currency_id"]))
    
    def _get_supplier_map(self):
        """Get supplier name to ID mapping."""
        df = pd.read_sql("SELECT supplier_id, supplier_name FROM suppliers", engine)
        return dict(zip(df["supplier_name"], df["supplier_id"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load external company procurement data into PVIS"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="./external_data",
        help="Directory containing CSV input files"
    )
    
    args = parser.parse_args()
    
    loader = ExternalDataLoader(args.input_dir)
    
    if loader.load_all_files():
        if loader.import_data():
            print()
            print("Next steps:")
            print("  1. Run: python data_ingestion/populate_warehouse.py")
            print("  2. Run: python data_ingestion/rebuild_fx_historical.py (or provide fx_rates.csv)")
            print("  3. Launch Streamlit: streamlit run streamlit_app.py")
            sys.exit(0)
    
    sys.exit(1)
