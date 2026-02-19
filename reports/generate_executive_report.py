"""
Generate PVIS Executive PDF Report.
Outputs reports/Executive_Report.pdf.
"""

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


REPORT_DIR = Path(__file__).resolve().parent
FIG_DIR = REPORT_DIR / "figures"
OUTPUT_PDF = REPORT_DIR / "Executive_Report.pdf"


def _page_title(fig, title, subtitle=None):
    fig.text(0.5, 0.93, title, ha="center", fontsize=18, weight="bold")
    if subtitle:
        fig.text(0.5, 0.90, subtitle, ha="center", fontsize=11)


def _add_image(fig, image_path, y=0.1, h=0.75):
    ax = fig.add_axes([0.08, y, 0.84, h])
    ax.imshow(plt.imread(image_path))
    ax.axis("off")


def generate_report():
    if not FIG_DIR.exists():
        raise FileNotFoundError("Run generate_pvis_visuals.py first")

    with PdfPages(OUTPUT_PDF) as pdf:
        # Cover page
        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Procurement Volatility Intelligence System (PVIS)")
        fig.text(0.5, 0.82, "Executive Report", ha="center", fontsize=14)
        fig.text(0.12, 0.68, "Business Problem:", fontsize=12, weight="bold")
        fig.text(
            0.12,
            0.64,
            (
                "Volatile FX rates, supplier risk, and working capital drag are "
                "eroding procurement margins and creating unpredictable cash cycles."
            ),
            fontsize=11,
        )
        fig.text(0.12, 0.54, "PVIS Mandate:", fontsize=12, weight="bold")
        fig.text(
            0.12,
            0.50,
            (
                "Provide real-time visibility into FX exposure, supplier risk, and "
                "cash conversion performance with scenario-ready analytics."
            ),
            fontsize=11,
        )
        fig.text(0.12, 0.40, "Strategic Recommendations:", fontsize=12, weight="bold")
        fig.text(
            0.12,
            0.36,
            (
                "1) Rebalance sourcing toward low-volatility currencies and hedge top "
                "exposures by tier."
            ),
            fontsize=11,
        )
        fig.text(
            0.12,
            0.32,
            (
                "2) Renegotiate top-risk supplier contracts using lead-time and quality "
                "volatility triggers."
            ),
            fontsize=11,
        )
        fig.text(
            0.12,
            0.28,
            (
                "3) Compress cash conversion by optimizing DPO/DIO and eliminating "
                "leakage in high-variance categories."
            ),
            fontsize=11,
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Dashboard blueprint page
        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Executive Dashboard Blueprint")
        _add_image(fig, FIG_DIR / "dashboard_blueprint.png")
        pdf.savefig(fig)
        plt.close(fig)

        # Risk heatmap
        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Supplier Risk Ranking & Volatility")
        _add_image(fig, FIG_DIR / "risk_heatmap.png")
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Supplier Risk Analysis")
        _add_image(fig, FIG_DIR / "lead_time_volatility.png", y=0.52, h=0.34)
        _add_image(fig, FIG_DIR / "top10_risk_suppliers.png", y=0.10, h=0.34)
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Cost Variance and Leakage")
        _add_image(fig, FIG_DIR / "cost_variance_table.png", y=0.54, h=0.30)
        _add_image(fig, FIG_DIR / "cost_leakage_breakdown.png", y=0.10, h=0.34)
        pdf.savefig(fig)
        plt.close(fig)

        # FX scenario
        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "FX Scenario Planning: Monte Carlo Forecast")
        _add_image(fig, FIG_DIR / "fx_scenario_band.png", y=0.52, h=0.36)
        _add_image(fig, FIG_DIR / "fx_distribution.png", y=0.10, h=0.36)
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Landed Cost Stress Impact")
        _add_image(fig, FIG_DIR / "landed_cost_stress_impact.png")
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Working Capital Optimization")
        _add_image(fig, FIG_DIR / "inventory_trend.png", y=0.58, h=0.30)
        _add_image(fig, FIG_DIR / "dpo_vs_dio.png", y=0.31, h=0.24)
        _add_image(fig, FIG_DIR / "ccc_trend.png", y=0.05, h=0.24)
        pdf.savefig(fig)
        plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Optimization Opportunity Estimator")
        _add_image(fig, FIG_DIR / "optimization_estimator.png")
        pdf.savefig(fig)
        plt.close(fig)

    print(f"✓ Executive report generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_report()
