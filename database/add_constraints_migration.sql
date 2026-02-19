-- ============================================================
-- Database Migration Script: Add Constraints to pro_intel_2
-- Adds Foreign Keys and CHECK constraints for data integrity
-- ============================================================

USE pro_intel_2;

ALTER TABLE suppliers
ADD CONSTRAINT fk_suppliers_country 
    FOREIGN KEY (country_id) REFERENCES countries(country_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE suppliers
ADD CONSTRAINT fk_suppliers_currency 
    FOREIGN KEY (default_currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE purchase_orders
ADD CONSTRAINT fk_po_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE purchase_orders
ADD CONSTRAINT fk_po_currency 
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE purchase_order_items
ADD CONSTRAINT fk_poi_po 
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE purchase_order_items
ADD CONSTRAINT fk_poi_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE quality_incidents
ADD CONSTRAINT fk_qi_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE quality_incidents
ADD CONSTRAINT fk_qi_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE fx_rates
ADD CONSTRAINT fk_fx_currency 
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

ALTER TABLE inventory_snapshots
ADD CONSTRAINT fk_inventory_material 
    FOREIGN KEY (material_id) REFERENCES materials(material_id)
    ON DELETE RESTRICT ON UPDATE CASCADE;

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

ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT fk_perf_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE supplier_spend_summary
ADD CONSTRAINT fk_spend_supplier 
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE suppliers
ADD CONSTRAINT chk_suppliers_risk_index CHECK (risk_index >= 0 AND risk_index <= 100);
ALTER TABLE suppliers
ADD CONSTRAINT chk_suppliers_lead_time CHECK (lead_time_days >= 0);
ALTER TABLE materials
ADD CONSTRAINT chk_materials_cost CHECK (standard_cost > 0);
ALTER TABLE purchase_orders
ADD CONSTRAINT chk_po_dates CHECK (delivery_date IS NULL OR delivery_date >= order_date);
ALTER TABLE purchase_order_items
ADD CONSTRAINT chk_poi_quantity CHECK (quantity > 0);
ALTER TABLE purchase_order_items
ADD CONSTRAINT chk_poi_unit_price CHECK (unit_price > 0);
ALTER TABLE quality_incidents
ADD CONSTRAINT chk_qi_defect_rate CHECK (defect_rate >= 0 AND defect_rate <= 1);
ALTER TABLE fx_rates
ADD CONSTRAINT chk_fx_rate CHECK (rate_to_usd > 0);
ALTER TABLE inventory_snapshots
ADD CONSTRAINT chk_inventory_quantity CHECK (quantity_on_hand >= 0);
ALTER TABLE inventory_snapshots
ADD CONSTRAINT chk_inventory_value CHECK (inventory_value_usd >= 0);
ALTER TABLE fact_procurement
ADD CONSTRAINT chk_fact_quantity CHECK (quantity > 0);
ALTER TABLE fact_procurement
ADD CONSTRAINT chk_fact_value CHECK (total_local_value >= 0 AND total_usd_value >= 0);
ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_defect_rate CHECK (avg_defect_rate >= 0 AND avg_defect_rate <= 100);
ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_otd CHECK (on_time_delivery_pct >= 0 AND on_time_delivery_pct <= 100);
ALTER TABLE supplier_performance_metrics
ADD CONSTRAINT chk_perf_risk_score CHECK (composite_risk_score >= 0 AND composite_risk_score <= 100);
ALTER TABLE payables_summary
ADD CONSTRAINT chk_payables_amount CHECK (accounts_payable_usd >= 0);
ALTER TABLE receivables_summary
ADD CONSTRAINT chk_receivables_amount CHECK (accounts_receivable_usd >= 0);

CREATE INDEX idx_po_supplier_date ON purchase_orders(supplier_id, order_date);
CREATE INDEX idx_po_status_date ON purchase_orders(status, order_date);
CREATE INDEX idx_qi_supplier_date ON quality_incidents(supplier_id, incident_date);
CREATE INDEX idx_qi_material_date ON quality_incidents(material_id, incident_date);
CREATE INDEX idx_inventory_material_date ON inventory_snapshots(material_id, snapshot_date);
CREATE INDEX idx_fact_date_supplier ON fact_procurement(date_key, supplier_key);
CREATE INDEX idx_fact_date_material ON fact_procurement(date_key, material_key);

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
