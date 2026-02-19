"""
PVIS end-to-end execution pipeline.
"""

from data_ingestion.generate_sample_data import main as generate_sample_data
from data_ingestion.populate_warehouse import main as run_etl
from analytics.advanced_analytics import run_fx_simulation, run_supplier_risk
from analytics.optimization_engine import main as run_optimization
from reports.generate_pvis_visuals import main as generate_visuals
from reports.generate_executive_report import generate_report


def main():
    print("=" * 70)
    print("PVIS END-TO-END PIPELINE")
    print("=" * 70)

    generate_sample_data()
    run_etl()
    run_fx_simulation(currency_code="NGN", days=90, simulations=10000)
    run_supplier_risk()
    run_optimization()
    generate_visuals()
    generate_report()

    print("=" * 70)
    print("✓ PVIS pipeline complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
