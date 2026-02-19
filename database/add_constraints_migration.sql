-- ============================================================
-- Database Migration Script: Add Constraints to pro_intel_2
-- Adds Foreign Keys and CHECK constraints for data integrity
-- ============================================================

USE pro_intel_2;

-- ============================================================
-- SECTION 1: ADD FOREIGN KEY CONSTRAINTS
-- ============================================================

-- Suppliers table FKs
ALTER TABLE suppliers
ADD CONSTRAINT fk_suppliers_country 
    FOREIGN KEY (country_id) REFERENCES countries(country_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE suppliers
ADD CONSTRAINT fk_suppliers_currency 
    FOREIGN KEY (default_currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Purchase Orders FKs
ALTER TABLE purchase_orders
ADD CONSTRAINT fk_po_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE purchase_orders
ADD CONSTRAINT fk_po_currency 
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Purchase Order Items FKs
ALTER TABLE purchase_order_items
ADD CONSTRAINT fk_poi_po 
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE purchase_order_items
ADD CONSTRAINT fk_poi_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Quality Incidents FKs
ALTER TABLE quality_incidents
ADD CONSTRAINT fk_qi_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE quality_incidents
ADD CONSTRAINT fk_qi_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- FX Rates FK
ALTER TABLE fx_rates
ADD CONSTRAINT fk_fx_currency 
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Inventory Snapshots FK
ALTER TABLE inventory_snapshots
ADD CONSTRAINT fk_inventory_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Fact Procurement FKs
ALTER TABLE fact_procurement
ADD CONSTRAINT fk_fact_supplier 
    FOREIGN KEY (supplier_key) REFERENCES dim_supplier(supplier_key)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE fact_procurement
ADD CONSTRAINT fk_fact_material 
    FOREIGN KEY (material_key) REFERENCES dim_material(material_key)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE fact_procurement
ADD CONSTRAINT fk_fact_date 
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- Supplier Performance Metrics FK
ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT fk_perf_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

-- Supplier Spend Summary FK
ALTER TABLE supplier_spend_summary
ADD CONSTRAINT fk_spend_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

-- ============================================================
-- SECTION 2: ADD CHECK CONSTRAINTS
-- ============================================================

-- Suppliers: risk_index should be between 0 and 100
ALTER TABLE suppliers
ADD CONSTRAINT chk_suppliers_risk_index 
    CHECK (risk_index >= 0 AND risk_index <= 100);

-- Suppliers: lead_time_days should be positive
ALTER TABLE suppliers
ADD CONSTRAINT chk_suppliers_lead_time 
    CHECK (lead_time_days >= 0);

-- Materials: standard_cost should be positive
ALTER TABLE materials
ADD CONSTRAINT chk_materials_cost 
    CHECK (standard_cost > 0);

-- Purchase Orders: dates should be logical
ALTER TABLE purchase_orders
ADD CONSTRAINT chk_po_dates 
    CHECK (delivery_date IS NULL OR delivery_date >= order_date);

-- Purchase Order Items: quantity and price should be positive
ALTER TABLE purchase_order_items
ADD CONSTRAINT chk_poi_quantity 
    CHECK (quantity > 0);

ALTER TABLE purchase_order_items
ADD CONSTRAINT chk_poi_unit_price 
    CHECK (unit_price > 0);

-- Quality Incidents: defect_rate should be between 0 and 1
ALTER TABLE quality_incidents
ADD CONSTRAINT chk_qi_defect_rate 
    CHECK (defect_rate >= 0 AND defect_rate <= 1);

-- FX Rates: rate should be positive
ALTER TABLE fx_rates
ADD CONSTRAINT chk_fx_rate 
    CHECK (rate_to_usd > 0);

-- Inventory Snapshots: quantity and value should be non-negative
ALTER TABLE inventory_snapshots
ADD CONSTRAINT chk_inventory_quantity 
    CHECK (quantity_on_hand >= 0);

ALTER TABLE inventory_snapshots
ADD CONSTRAINT chk_inventory_value 
    CHECK (inventory_value_usd >= 0);

-- Fact Procurement: quantities and values should be positive
ALTER TABLE fact_procurement
ADD CONSTRAINT chk_fact_quantity 
    CHECK (quantity > 0);

ALTER TABLE fact_procurement
ADD CONSTRAINT chk_fact_value 
    CHECK (total_local_value >= 0 AND total_usd_value >= 0);

-- Supplier Performance Metrics: percentages and scores should be bounded
ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_defect_rate 
    CHECK (avg_defect_rate >= 0 AND avg_defect_rate <= 100);

ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_otd 
    CHECK (on_time_delivery_pct >= 0 AND on_time_delivery_pct <= 100);

ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_risk_score 
    CHECK (composite_risk_score >= 0 AND composite_risk_score <= 100);

-- Payables and Receivables: amounts should be non-negative
ALTER TABLE payables_summary
ADD CONSTRAINT chk_payables_amount 
    CHECK (accounts_payable_usd >= 0);

ALTER TABLE receivables_summary
ADD CONSTRAINT chk_receivables_amount 
    CHECK (accounts_receivable_usd >= 0);

-- ============================================================
-- SECTION 3: ADD ADDITIONAL INDEXES FOR PERFORMANCE
-- ============================================================

-- Composite indexes for common analytical queries
CREATE INDEX idx_po_supplier_date ON purchase_orders(supplier_id, order_date);
CREATE INDEX idx_po_status_date ON purchase_orders(status, order_date);

CREATE INDEX idx_qi_supplier_date ON quality_incidents(supplier_id, incident_date);
CREATE INDEX idx_qi_material_date ON quality_incidents(material_id, incident_date);

CREATE INDEX idx_inventory_material_date ON inventory_snapshots(material_id, snapshot_date);

CREATE INDEX idx_fact_date_supplier ON fact_procurement(date_key, supplier_key);
CREATE INDEX idx_fact_date_material ON fact_procurement(date_key, material_key);

-- ============================================================
-- SECTION 4: CREATE FX SIMULATION RESULTS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS fx_simulation_results (
    simulation_id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_date DATE NOT NULL,
    currency_id INT NOT NULL,
    forecast_days INT NOT NULL,
    current_rate DECIMAL(18,8) NOT NULL,
    p5_rate DECIMAL(18,8) NOT NULL,
    median_rate DECIMAL(18,8) NOT NULL,
    p95_rate DECIMAL(18,8) NOT NULL,
    simulations_count INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fx_sim_currency_date (currency_id, simulation_date)
);

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Show all foreign keys
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    REFERENCED_TABLE_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'pro_intel_2'
    AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- Show all check constraints
SELECT 
    TABLE_NAME,
    CONSTRAINT_NAME,
    CHECK_CLAUSE
FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'pro_intel_2'
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- ============================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================

/*
-- To remove all constraints added by this migration:

-- Drop Foreign Keys
ALTER TABLE suppliers DROP FOREIGN KEY fk_suppliers_country;
ALTER TABLE suppliers DROP FOREIGN KEY fk_suppliers_currency;
ALTER TABLE purchase_orders DROP FOREIGN KEY fk_po_supplier;
ALTER TABLE purchase_orders DROP FOREIGN KEY fk_po_currency;
ALTER TABLE purchase_order_items DROP FOREIGN KEY fk_poi_po;
ALTER TABLE purchase_order_items DROP FOREIGN KEY fk_poi_material;
ALTER TABLE quality_incidents DROP FOREIGN KEY fk_qi_supplier;
ALTER TABLE quality_incidents DROP FOREIGN KEY fk_qi_material;
ALTER TABLE fx_rates DROP FOREIGN KEY fk_fx_currency;
ALTER TABLE inventory_snapshots DROP FOREIGN KEY fk_inventory_material;
ALTER TABLE fact_procurement DROP FOREIGN KEY fk_fact_supplier;
ALTER TABLE fact_procurement DROP FOREIGN KEY fk_fact_material;
ALTER TABLE fact_procurement DROP FOREIGN KEY fk_fact_date;
ALTER TABLE supplier_performance_metrics DROP FOREIGN KEY fk_perf_supplier;
ALTER TABLE supplier_spend_summary DROP FOREIGN KEY fk_spend_supplier;

-- Drop Check Constraints
ALTER TABLE suppliers DROP CHECK chk_suppliers_risk_index;
ALTER TABLE suppliers DROP CHECK chk_suppliers_lead_time;
ALTER TABLE materials DROP CHECK chk_materials_cost;
ALTER TABLE purchase_orders DROP CHECK chk_po_dates;
ALTER TABLE purchase_order_items DROP CHECK chk_poi_quantity;
ALTER TABLE purchase_order_items DROP CHECK chk_poi_unit_price;
ALTER TABLE quality_incidents DROP CHECK chk_qi_defect_rate;
ALTER TABLE fx_rates DROP CHECK chk_fx_rate;
ALTER TABLE inventory_snapshots DROP CHECK chk_inventory_quantity;
ALTER TABLE inventory_snapshots DROP CHECK chk_inventory_value;
ALTER TABLE fact_procurement DROP CHECK chk_fact_quantity;
ALTER TABLE fact_procurement DROP CHECK chk_fact_value;
ALTER TABLE supplier_performance_metrics DROP CHECK chk_perf_defect_rate;
ALTER TABLE supplier_performance_metrics DROP CHECK chk_perf_otd;
ALTER TABLE supplier_performance_metrics DROP CHECK chk_perf_risk_score;
ALTER TABLE payables_summary DROP CHECK chk_payables_amount;
ALTER TABLE receivables_summary DROP CHECK chk_receivables_amount;

-- Drop Additional Indexes
DROP INDEX idx_po_supplier_date ON purchase_orders;
DROP INDEX idx_po_status_date ON purchase_orders;
DROP INDEX idx_qi_supplier_date ON quality_incidents;
DROP INDEX idx_qi_material_date ON quality_incidents;
DROP INDEX idx_inventory_material_date ON inventory_snapshots;
DROP INDEX idx_fact_date_supplier ON fact_procurement;
DROP INDEX idx_fact_date_material ON fact_procurement;
*/
