"""
Generate PVIS Executive PDF Report.
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
        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "Procurement Volatility Intelligence System (PVIS)")
        fig.text(0.5, 0.82, "Executive Report", ha="center", fontsize=14)
        fig.text(0.12, 0.68, "Business Problem:", fontsize=12, weight="bold")
        fig.text(0.12, 0.64, "Volatile FX, supplier risk, and working capital drag are compressing procurement margin.", fontsize=11)
        fig.text(0.12, 0.54, "Strategic Recommendations:", fontsize=12, weight="bold")
        fig.text(0.12, 0.50, "1) Hedge/rebalance currency exposure\n2) Contract volatility triggers\n3) Optimize DPO/DIO for CCC improvement", fontsize=11)
        pdf.savefig(fig); plt.close(fig)

        for title, img in [
            ("Executive Dashboard Blueprint", "dashboard_blueprint.png"),
            ("Supplier Risk Ranking & Volatility", "risk_heatmap.png"),
            ("Cost Leakage Breakdown", "cost_leakage_breakdown.png"),
        ]:
            fig = plt.figure(figsize=(11, 8.5))
            _page_title(fig, title)
            _add_image(fig, FIG_DIR / img)
            pdf.savefig(fig); plt.close(fig)

        fig = plt.figure(figsize=(11, 8.5))
        _page_title(fig, "FX Scenario Planning: Monte Carlo Forecast")
        _add_image(fig, FIG_DIR / "fx_scenario_band.png", y=0.52, h=0.36)
        _add_image(fig, FIG_DIR / "fx_distribution.png", y=0.10, h=0.36)
        pdf.savefig(fig); plt.close(fig)

    print(f"✓ Executive report generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_report()
