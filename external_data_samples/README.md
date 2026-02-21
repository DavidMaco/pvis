# External Data Sample Files

This directory contains example CSV files showing the expected format for importing company procurement data into PVIS.

## Quick Start

1. **Copy the sample files** to a working directory (Windows PowerShell):
   ```powershell
   cp -Recurse external_data_samples\* .\my_company_data\
   ```
   Or using File Explorer: Right-click external_data_samples → Copy, then paste as my_company_data

2. **Edit the CSV files** with your company data (see `EXTERNAL_DATA_GUIDE.md` for field specifications)

3. **Run the import**:
   ```powershell
   python data_ingestion\external_data_loader.py --input-dir .\my_company_data
   ```

## File Contents

- **suppliers.csv**: 8 sample suppliers with country, currency, lead times, defect rates
- **materials.csv**: 15 sample materials across Polymers, Chemicals, Metals, Fluids categories
- **purchase_orders.csv**: 10 sample POs dated Jan–Apr 2024 with various statuses
- **purchase_order_items.csv**: 14 sample line items linking POs to materials

## Notes

- **Do NOT edit these sample files directly** — they're templates read-only examples
- **Copy them** to your own directory before customization
- Sample data uses realistic suppliers (Germany, China, Nigeria, India, etc.) to demonstrate multi-currency procurement
- Currency values and material costs are illustrative; adjust to your business

## For More Information

See `EXTERNAL_DATA_GUIDE.md` for:
- Detailed field specifications
- Data validation rules
- Common issues & solutions
- Complete workflow example
