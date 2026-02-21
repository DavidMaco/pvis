"""
PVIS — Procurement Volatility Intelligence System
Streamlit Executive Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import datetime
import requests
from pathlib import Path
import tomllib
import demo_data

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PVIS — Procurement Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Database connection ──────────────────────────────────────────────────────

@st.cache_resource
def get_engine():
    """Create a cached SQLAlchemy engine from Streamlit secrets or env."""
    try:
        db = st.secrets["database"]
        url = (
            f"mysql+pymysql://{db['user']}:{db['password']}"
            f"@{db['host']}:{db['port']}/{db['name']}"
        )
    except Exception:
        # Fallback to repo-local secrets.toml if Streamlit secrets are not loaded
        try:
            secrets_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
            if secrets_path.exists():
                with secrets_path.open("rb") as handle:
                    secrets = tomllib.load(handle)
                db = secrets.get("database", {})
                if db:
                    url = (
                        f"mysql+pymysql://{db['user']}:{db['password']}"
                        f"@{db['host']}:{db['port']}/{db['name']}"
                    )
                else:
                    url = "mysql+pymysql://root:Maconoelle86@127.0.0.1:3306/pro_intel_2"
            else:
                url = "mysql+pymysql://root:Maconoelle86@127.0.0.1:3306/pro_intel_2"
        except Exception:
            url = "mysql+pymysql://root:Maconoelle86@127.0.0.1:3306/pro_intel_2"
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)


# ── Detect whether a live database is reachable ──────────────────────────────

@st.cache_resource
def _check_db():
    """Return (engine, True) if DB is reachable, else (None, False)."""
    try:
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng, True
    except Exception:
        return None, False


engine, _DB_LIVE = _check_db()
DEMO_MODE: bool = not _DB_LIVE


def run_query(query: str, params=None) -> pd.DataFrame:
    """Execute a read query and return a DataFrame.
    Falls back to synthetic demo data when no database is available."""
    if DEMO_MODE:
        return demo_data.demo_query(query)
    try:
        return pd.read_sql(text(query), engine, params=params)
    except Exception as e:
        st.error(f"Database query failed: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)  # refresh every 5 minutes
def _fetch_live_rates() -> dict:
    """
    Fetch ALL live USD-base exchange rates from a free public API.
    Returns a dict like {"NGN": 1345.77, "EUR": 0.92, "GBP": 0.79, ...}.
    Returns an empty dict if every API is unreachable.
    """
    apis = [
        # Primary: open.er-api.com — supports 150+ currencies including NGN
        ("https://open.er-api.com/v6/latest/USD", lambda j: j.get("rates", {})),
        # Backup: frankfurter.dev (ECB source) — no NGN, but good for EUR/GBP/CNY
        ("https://api.frankfurter.dev/v1/latest?base=USD", lambda j: j.get("rates", {})),
    ]
    for url, parser in apis:
        try:
            resp = requests.get(url, timeout=8)
            if resp.ok:
                rates = parser(resp.json())
                if isinstance(rates, dict) and len(rates) > 0:
                    return rates
        except Exception:
            continue
    return {}


def _fetch_live_rate(currency_code: str) -> float | None:
    """
    Get the live exchange rate (units per 1 USD) for a specific currency.
    Returns None only if all public APIs are unreachable.
    """
    rates = _fetch_live_rates()
    code = currency_code.upper()
    if code == "USD":
        return 1.0
    return float(rates[code]) if code in rates else None


def _fetch_live_ngn_rate() -> float:
    """
    Convenience wrapper: live NGN/USD rate with DB fallback.
    """
    rate = _fetch_live_rate("NGN")
    if rate is not None:
        return rate
    # Fallback: latest rate from seed data
    df = run_query("""
        SELECT fx.rate_to_usd
        FROM fx_rates fx
        JOIN currencies c ON fx.currency_id = c.currency_id
        WHERE UPPER(c.currency_code) = 'NGN'
        ORDER BY fx.rate_date DESC LIMIT 1
    """)
    return float(df.iloc[0]["rate_to_usd"]) if not df.empty else 0.0


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/combo-chart.png",
        width=64,
    )
    st.title("PVIS")
    st.caption("Procurement Volatility Intelligence System")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Executive Summary",
            "📈 FX Volatility & Monte Carlo",
            "🏭 Supplier Risk Analysis",
            "💰 Spend & Cost Analysis",
            "🏦 Working Capital",
            "🔄 Scenario Planning",
            "📂 Company Data Upload",
            "⚙️ Pipeline Runner",
        ],
        index=0,
    )

    st.divider()
    if DEMO_MODE:
        st.warning("⚡ DEMO MODE — no database")
    st.caption(f"Last refresh: {datetime.now():%Y-%m-%d %H:%M}")
    if st.button("🔄 Clear cache & reload"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# DEMO MODE BANNER (shown at top of every page)
# ══════════════════════════════════════════════════════════════════════════════

if DEMO_MODE:
    st.info(
        "📢 **Demo Mode** — The dashboard is running with synthetic sample data "
        "because no MySQL database is connected. All charts, KPIs, and "
        "simulations are fully functional. To connect a live database, "
        "configure `[database]` in `.streamlit/secrets.toml` or Streamlit "
        "Cloud secrets.",
        icon="ℹ️",
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Executive Summary
# ══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Executive Summary":
    st.title("📊 Executive Summary")
    st.markdown(
        "Real-time visibility into **FX exposure**, **supplier risk**, and "
        "**cash conversion** performance."
    )

    # ── KPI row ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    # Total spend
    spend_df = run_query(
        "SELECT SUM(total_usd_value) AS spend FROM fact_procurement"
    )
    total_spend = float(spend_df.iloc[0]["spend"] or 0) if not spend_df.empty else 0

    # FX exposure
    fx_exp_df = run_query("""
        SELECT
            (SUM(CASE WHEN cur.currency_code != 'USD'
                 THEN poi.quantity * poi.unit_price ELSE 0 END) * 100.0 /
             NULLIF(SUM(poi.quantity * poi.unit_price), 0)) AS fx_pct
        FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        JOIN currencies cur ON po.currency_id = cur.currency_id
    """)
    fx_pct = float(fx_exp_df.iloc[0]["fx_pct"] or 0) if not fx_exp_df.empty else 0

    # Average composite risk
    risk_df = run_query(
        "SELECT AVG(composite_risk_score) AS avg_risk FROM supplier_performance_metrics"
    )
    avg_risk = float(risk_df.iloc[0]["avg_risk"] or 0) if not risk_df.empty else 0

    # CCC
    ccc_df = run_query(
        "SELECT ccc FROM financial_kpis ORDER BY kpi_date DESC LIMIT 1"
    )
    ccc_val = float(ccc_df.iloc[0]["ccc"] or 0) if not ccc_df.empty else 0

    # Current NGN rate — live API with DB fallback
    ngn_rate = _fetch_live_ngn_rate()

    col1.metric("Total Spend (USD)", f"${total_spend:,.0f}")
    col2.metric("FX Exposure", f"{fx_pct:.1f}%")
    col3.metric("Avg Risk Score", f"{avg_risk:.1f}")
    col4.metric("CCC (days)", f"{ccc_val:,.0f}")
    col5.metric("USD/NGN (live)", f"₦{ngn_rate:,.2f}")

    st.divider()

    # ── Charts row ───────────────────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("Supplier Risk Ranking")
        risk_data = run_query("""
            SELECT s.supplier_name, spm.composite_risk_score
            FROM supplier_performance_metrics spm
            JOIN suppliers s ON spm.supplier_id = s.supplier_id
            ORDER BY spm.composite_risk_score DESC
            LIMIT 10
        """)
        if not risk_data.empty:
            fig = px.bar(
                risk_data,
                x="composite_risk_score",
                y="supplier_name",
                orientation="h",
                color="composite_risk_score",
                color_continuous_scale="OrRd",
                labels={"composite_risk_score": "Risk Score", "supplier_name": ""},
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Monthly Procurement Trend")
        trend_df = run_query("""
            SELECT
                DATE_FORMAT(d.full_date, '%Y-%m') AS month,
                SUM(f.total_usd_value) AS spend_usd
            FROM fact_procurement f
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY DATE_FORMAT(d.full_date, '%Y-%m')
            ORDER BY month
        """)
        if not trend_df.empty:
            fig = px.area(
                trend_df,
                x="month",
                y="spend_usd",
                labels={"month": "Month", "spend_usd": "Spend (USD)"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — FX Volatility & Monte Carlo
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📈 FX Volatility & Monte Carlo":
    st.title("📈 FX Volatility & Monte Carlo Forecast")

    # Currency selector – only currencies that have FX rate history
    currencies_df = run_query("""
        SELECT DISTINCT c.currency_id, c.currency_code
        FROM currencies c
        JOIN fx_rates f ON c.currency_id = f.currency_id
        ORDER BY c.currency_code
    """)
    if currencies_df.empty:
        st.warning("No currencies with FX rate data found.")
        st.stop()

    currency_options = {
        row["currency_code"]: int(row["currency_id"])
        for _, row in currencies_df.iterrows()
    }

    sel_col, param_col = st.columns([1, 2])
    with sel_col:
        chosen_code = st.selectbox("Currency", list(currency_options.keys()), index=0)
        chosen_id = currency_options[chosen_code]
    with param_col:
        sim_days = st.slider("Forecast horizon (days)", 30, 1095, 90)
        sim_count = st.select_slider(
            "Simulations", options=[1000, 5000, 10000, 25000, 50000], value=10000
        )

    # Historical rates
    hist_df = run_query(
        f"SELECT rate_date, rate_to_usd FROM fx_rates WHERE currency_id = {chosen_id} ORDER BY rate_date"
    )

    if hist_df.empty:
        st.warning(f"No FX data for {chosen_code}.")
        st.stop()

    # Normalize date dtype to avoid mixed datetime.date vs Timestamp comparisons
    hist_df["rate_date"] = pd.to_datetime(hist_df["rate_date"], errors="coerce").dt.normalize()
    hist_df = hist_df.dropna(subset=["rate_date"]).reset_index(drop=True)

    # ── Live rate enrichment ─────────────────────────────────────────────────
    # Always anchor to the real-time API rate so charts and simulations
    # reflect the actual current market, not stale seed/backcast data.
    live_rate = _fetch_live_rate(chosen_code)
    db_latest = float(hist_df["rate_to_usd"].iloc[-1])

    if live_rate is not None:
        # Append today's live rate to the series so the chart ends at reality
        today_row = pd.DataFrame(
            [{"rate_date": pd.Timestamp.today().normalize(), "rate_to_usd": live_rate}]
        )
        hist_df = pd.concat([hist_df, today_row], ignore_index=True)
        hist_df = hist_df.drop_duplicates(subset="rate_date", keep="last")
        hist_df = hist_df.sort_values("rate_date").reset_index(drop=True)
        current_rate_source = "live API"
        current_rate = live_rate
    else:
        current_rate_source = "latest DB record"
        current_rate = db_latest

    # Show live vs DB comparison
    if live_rate is not None and abs(live_rate - db_latest) / max(db_latest, 1) > 0.05:
        st.info(
            f"**Live rate ({chosen_code}/USD):** {live_rate:,.4f}  —  "
            f"DB latest: {db_latest:,.4f}  "
            f"(divergence: {((live_rate - db_latest) / db_latest) * 100:+.1f}%). "
            f"Monte Carlo simulation uses the **live rate** as starting point."
        )

    st.subheader(f"Historical {chosen_code}/USD Rate")
    fig_hist = px.line(hist_df, x="rate_date", y="rate_to_usd", labels={"rate_to_usd": f"{chosen_code} per 1 USD"})
    # Mark the live rate point
    if live_rate is not None:
        fig_hist.add_scatter(
            x=[hist_df["rate_date"].iloc[-1]],
            y=[live_rate],
            mode="markers",
            marker=dict(size=10, color="red", symbol="diamond"),
            name="Live Rate",
        )
    fig_hist.update_layout(height=350)
    st.plotly_chart(fig_hist, use_container_width=True)

    # ── Run Monte Carlo ──────────────────────────────────────────────────────
    if st.button("🎲 Run Monte Carlo Simulation", type="primary"):
        hist_df["log_return"] = np.log(hist_df["rate_to_usd"] / hist_df["rate_to_usd"].shift(1))
        hist_df = hist_df.dropna()
        mu = hist_df["log_return"].mean()
        sigma = hist_df["log_return"].std()
        # current_rate already set above from live API (preferred) or DB

        dt = 1 / 252
        np.random.seed(42)
        paths = np.zeros((sim_count, sim_days))
        for i in range(sim_count):
            rate = current_rate
            for d in range(sim_days):
                shock = np.random.normal(mu * dt, sigma * np.sqrt(dt))
                rate *= np.exp(shock)
                paths[i, d] = rate

        p5 = np.percentile(paths, 5, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p95 = np.percentile(paths, 95, axis=0)

        # Summary metrics
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric(f"Current Rate ({current_rate_source})", f"{current_rate:,.4f}")
        mcol2.metric("P5 (worst)", f"{p5[-1]:,.4f}")
        mcol3.metric("P50 (median)", f"{p50[-1]:,.4f}")
        mcol4.metric("P95 (best)", f"{p95[-1]:,.4f}")

        # Fan chart
        st.subheader("90-Day FX Forecast Band")
        days_range = list(range(1, sim_days + 1))
        fig_fan = go.Figure()
        fig_fan.add_trace(go.Scatter(x=days_range, y=p95, mode="lines", line=dict(width=0), showlegend=False))
        fig_fan.add_trace(
            go.Scatter(
                x=days_range, y=p5, fill="tonexty",
                fillcolor="rgba(0,100,255,0.15)", line=dict(width=0),
                name="5th–95th band",
            )
        )
        fig_fan.add_trace(go.Scatter(x=days_range, y=p50, mode="lines", line=dict(color="#1d4f91", width=2), name="Median"))
        fig_fan.update_layout(xaxis_title="Days Ahead", yaxis_title=f"{chosen_code} per 1 USD", height=400)
        st.plotly_chart(fig_fan, use_container_width=True)

        # Distribution histogram
        st.subheader("Terminal Rate Distribution")
        final_rates = paths[:, -1]
        fig_dist = px.histogram(
            x=final_rates, nbins=60,
            labels={"x": f"{chosen_code} Rate at Day {sim_days}"},
            opacity=0.8,
        )
        fig_dist.add_vline(x=np.percentile(final_rates, 5), line_dash="dash", line_color="red", annotation_text="P5")
        fig_dist.add_vline(x=np.percentile(final_rates, 50), line_dash="dash", line_color="blue", annotation_text="P50")
        fig_dist.add_vline(x=np.percentile(final_rates, 95), line_dash="dash", line_color="green", annotation_text="P95")
        fig_dist.update_layout(height=350)
        st.plotly_chart(fig_dist, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Supplier Risk Analysis
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🏭 Supplier Risk Analysis":
    st.title("🏭 Supplier Risk Analysis")

    perf_df = run_query("""
        SELECT s.supplier_name,
               spm.avg_lead_time, spm.lead_time_stddev,
               spm.avg_defect_rate, spm.cost_variance_pct,
               spm.on_time_delivery_pct, spm.fx_exposure_pct,
               spm.composite_risk_score
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.composite_risk_score DESC
    """)

    if perf_df.empty:
        st.warning("No supplier performance data. Run the analytics pipeline first.")
        st.stop()

    # ── Risk Heatmap ─────────────────────────────────────────────────────────
    st.subheader("Risk Heatmap")
    metrics = [
        "avg_lead_time", "lead_time_stddev", "avg_defect_rate",
        "cost_variance_pct", "on_time_delivery_pct", "fx_exposure_pct",
        "composite_risk_score",
    ]
    labels = ["Lead Time", "LT Vol", "Defect %", "Cost Var %", "OTD %", "FX Exp %", "Composite"]
    heat = perf_df.set_index("supplier_name")[metrics]
    heat_norm = (heat - heat.min()) / (heat.max() - heat.min() + 1e-9)

    fig_heat = px.imshow(
        heat_norm.values,
        y=heat_norm.index.tolist(),
        x=labels,
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig_heat.update_layout(height=max(350, len(heat_norm) * 45))
    st.plotly_chart(fig_heat, use_container_width=True)

    # ── Detail table ─────────────────────────────────────────────────────────
    st.subheader("Detailed Metrics")
    st.dataframe(
        perf_df.style.format({
            "avg_lead_time": "{:.1f}",
            "lead_time_stddev": "{:.2f}",
            "avg_defect_rate": "{:.2f}%",
            "cost_variance_pct": "{:.2f}%",
            "on_time_delivery_pct": "{:.1f}%",
            "fx_exposure_pct": "{:.1f}%",
            "composite_risk_score": "{:.2f}",
        }).background_gradient(subset=["composite_risk_score"], cmap="YlOrRd"),
        use_container_width=True,
        hide_index=True,
    )

    # ── Lead time volatility ─────────────────────────────────────────────────
    st.subheader("Lead Time Volatility")
    fig_lt = make_subplots(specs=[[{"secondary_y": True}]])
    fig_lt.add_trace(
        go.Bar(x=perf_df["supplier_name"], y=perf_df["lead_time_stddev"], name="Volatility (σ)", marker_color="#3b82f6"),
        secondary_y=False,
    )
    fig_lt.add_trace(
        go.Scatter(x=perf_df["supplier_name"], y=perf_df["avg_lead_time"], name="Avg Lead Time", mode="lines+markers", marker_color="#ef4444"),
        secondary_y=True,
    )
    fig_lt.update_layout(height=400)
    fig_lt.update_yaxes(title_text="Std Dev (days)", secondary_y=False)
    fig_lt.update_yaxes(title_text="Avg Lead Time (days)", secondary_y=True)
    st.plotly_chart(fig_lt, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Spend & Cost Analysis
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💰 Spend & Cost Analysis":
    st.title("💰 Spend & Cost Analysis")

    left, right = st.columns(2)

    with left:
        st.subheader("Spend by Supplier")
        spend_sup = run_query("""
            SELECT ds.supplier_name, SUM(f.total_usd_value) AS spend_usd
            FROM fact_procurement f
            JOIN dim_supplier ds ON f.supplier_key = ds.supplier_key
            GROUP BY ds.supplier_name
            ORDER BY spend_usd DESC
        """)
        if not spend_sup.empty:
            fig = px.pie(spend_sup, names="supplier_name", values="spend_usd", hole=0.4)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Spend by Material Category")
        spend_cat = run_query("""
            SELECT dm.category, SUM(f.total_usd_value) AS spend_usd
            FROM fact_procurement f
            JOIN dim_material dm ON f.material_key = dm.material_key
            GROUP BY dm.category
            ORDER BY spend_usd DESC
        """)
        if not spend_cat.empty:
            fig = px.pie(spend_cat, names="category", values="spend_usd", hole=0.4)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

    # ── Cost leakage ─────────────────────────────────────────────────────────
    st.subheader("Cost Leakage by Category")
    leak_df = run_query("""
        SELECT m.category,
               SUM((poi.unit_price - m.standard_cost) * poi.quantity) AS leakage_usd
        FROM purchase_order_items poi
        JOIN materials m ON poi.material_id = m.material_id
        WHERE poi.unit_price > m.standard_cost
        GROUP BY m.category
        ORDER BY leakage_usd DESC
    """)
    if not leak_df.empty:
        fig = px.bar(
            leak_df, x="category", y="leakage_usd",
            color="leakage_usd", color_continuous_scale="Reds",
            labels={"leakage_usd": "Leakage (USD)", "category": "Category"},
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    # ── Annual spend summary ─────────────────────────────────────────────────
    st.subheader("Annual Spend by Supplier")
    annual_df = run_query("""
        SELECT s.supplier_name, ss.year, ss.total_spend_usd
        FROM supplier_spend_summary ss
        JOIN suppliers s ON ss.supplier_id = s.supplier_id
        ORDER BY ss.year, ss.total_spend_usd DESC
    """)
    if not annual_df.empty:
        fig = px.bar(
            annual_df, x="supplier_name", y="total_spend_usd",
            color="year", barmode="group",
            labels={"total_spend_usd": "Spend (USD)", "supplier_name": "Supplier"},
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Working Capital
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🏦 Working Capital":
    st.title("🏦 Working Capital Optimization")

    # ── Inventory trend ──────────────────────────────────────────────────────
    st.subheader("Inventory Trend")
    inv_df = run_query("""
        SELECT snapshot_date, SUM(inventory_value_usd) AS total_inv
        FROM inventory_snapshots
        GROUP BY snapshot_date
        ORDER BY snapshot_date
    """)
    if not inv_df.empty:
        fig = px.area(inv_df, x="snapshot_date", y="total_inv", labels={"total_inv": "Inventory Value (USD)"})
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    # ── DPO vs DIO ───────────────────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("Payables Trend (DPO proxy)")
        pay_df = run_query(
            "SELECT summary_date, accounts_payable_usd FROM payables_summary ORDER BY summary_date"
        )
        if not pay_df.empty:
            fig = px.line(pay_df, x="summary_date", y="accounts_payable_usd")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Receivables Trend")
        rec_df = run_query(
            "SELECT summary_date, accounts_receivable_usd FROM receivables_summary ORDER BY summary_date"
        )
        if not rec_df.empty:
            fig = px.line(rec_df, x="summary_date", y="accounts_receivable_usd")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    # ── CCC ──────────────────────────────────────────────────────────────────
    st.subheader("Cash Conversion Cycle")
    kpi_df = run_query("SELECT kpi_date, dio, dpo, ccc FROM financial_kpis ORDER BY kpi_date DESC LIMIT 1")
    if not kpi_df.empty:
        row = kpi_df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("DIO (Days Inventory Outstanding)", f"{row['dio']:,.0f}")
        c2.metric("DPO (Days Payable Outstanding)", f"{row['dpo']:,.0f}")
        c3.metric("CCC (Cash Conversion Cycle)", f"{row['ccc']:,.0f}")

        # Target CCC
        target_dio = max(float(row["dio"]) * 0.9, 0)
        target_dpo = float(row["dpo"]) * 1.1
        target_ccc = target_dio - target_dpo
        improvement = float(row["ccc"]) - target_ccc

        st.info(
            f"**Optimization target:** Reduce DIO by 10% → {target_dio:,.0f}, "
            f"Extend DPO by 10% → {target_dpo:,.0f}. "
            f"Potential CCC improvement: **{improvement:,.0f} days**"
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Scenario Planning
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔄 Scenario Planning":
    st.title("🔄 Scenario Planning & Negotiation Insights")

    # ── FX Scenario Stress Test ──────────────────────────────────────────────
    st.subheader("FX Landed Cost Stress Test")
    st.markdown("Model the impact of FX shocks on total procurement spend.")

    base_df = run_query("""
        SELECT
            SUM((poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)) AS spend_usd,
            SUM(CASE WHEN cur.currency_code != 'USD'
                THEN (poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)
                ELSE 0 END) AS non_usd_spend
        FROM purchase_orders po
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        JOIN currencies cur ON po.currency_id = cur.currency_id
        LEFT JOIN fx_rates fx ON po.currency_id = fx.currency_id
            AND fx.rate_date = (
                SELECT MAX(rate_date) FROM fx_rates f2
                WHERE f2.currency_id = po.currency_id AND f2.rate_date <= po.order_date)
    """)

    if not base_df.empty and base_df.iloc[0]["spend_usd"]:
        base_total = float(base_df.iloc[0]["spend_usd"])
        base_non_usd = float(base_df.iloc[0]["non_usd_spend"] or 0)

        shock_pct = st.slider(
            "FX shock (%)", min_value=-30, max_value=50, value=0, step=5,
            help="Positive = devaluation (NGN weakens), Negative = appreciation"
        )

        scenarios = [
            {"name": "Appreciation (-10%)", "shock": -10},
            {"name": "Base (0%)", "shock": 0},
            {"name": "Mild Devaluation (+10%)", "shock": 10},
            {"name": "Severe Devaluation (+20%)", "shock": 20},
            {"name": f"Custom ({shock_pct:+d}%)", "shock": shock_pct},
        ]

        rows = []
        for s in scenarios:
            stressed_non_usd = base_non_usd * (1 + s["shock"] / 100.0)
            stressed_total = (base_total - base_non_usd) + stressed_non_usd
            rows.append({
                "Scenario": s["name"],
                "Shock %": s["shock"],
                "Baseline USD": base_total,
                "Stressed USD": stressed_total,
                "Impact USD": stressed_total - base_total,
            })

        scenario_df = pd.DataFrame(rows)

        fig = px.bar(
            scenario_df, x="Scenario", y="Impact USD",
            color="Impact USD",
            color_continuous_scale="RdYlGn_r",
            labels={"Impact USD": "Landed Cost Impact (USD)"},
        )
        fig.add_hline(y=0, line_dash="solid", line_color="black")
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            scenario_df.style.format({
                "Baseline USD": "${:,.0f}",
                "Stressed USD": "${:,.0f}",
                "Impact USD": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # ── Negotiation insights ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Negotiation Insights — Top Risk Suppliers")

    neg_df = run_query("""
        SELECT s.supplier_name, spm.composite_risk_score, spm.avg_lead_time,
               spm.avg_defect_rate, spm.cost_variance_pct, spm.fx_exposure_pct
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.composite_risk_score DESC
        LIMIT 10
    """)

    if not neg_df.empty:
        for _, r in neg_df.iterrows():
            actions = []
            if r["avg_lead_time"] > neg_df["avg_lead_time"].median():
                actions.append("⏱️ Add lead-time SLA penalties")
            if r["avg_defect_rate"] > neg_df["avg_defect_rate"].median():
                actions.append("🔍 Introduce quality rebate clause")
            if r["cost_variance_pct"] > neg_df["cost_variance_pct"].median():
                actions.append("📊 Lock indexed pricing corridor")
            if r["fx_exposure_pct"] > neg_df["fx_exposure_pct"].median():
                actions.append("💱 Shift contract currency / hedge exposure")
            if not actions:
                actions.append("✅ Maintain terms and monitor quarterly")

            with st.expander(f"**{r['supplier_name']}** — Risk Score: {r['composite_risk_score']:.1f}"):
                st.markdown("\n".join(f"- {a}" for a in actions))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — Company Data Upload
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📂 Company Data Upload":
    st.title("📂 Company Data Upload")
    st.markdown(
        "Upload your company's procurement data to run the full PVIS analytics "
        "pipeline on **your own data** instead of the generated seed data."
    )

    if DEMO_MODE:
        st.warning(
            "⚠️ **Database required** — Uploading and processing company data "
            "needs a live MySQL connection. Configure `[database]` in Streamlit "
            "secrets to enable this feature. In demo mode, you can preview file "
            "validation but data won't be imported."
        )

    # ── Upload method selector ───────────────────────────────────────────────
    upload_method = st.radio(
        "Upload method",
        ["📄 Individual CSV files", "📦 ZIP archive (all CSVs in one file)"],
        horizontal=True,
    )

    st.divider()

    REQUIRED_FILES = {
        "suppliers": {
            "description": "Supplier master data",
            "columns": "supplier_name, country, default_currency, lead_time_days, [lead_time_stddev], [defect_rate_pct]",
        },
        "materials": {
            "description": "Material catalog",
            "columns": "material_name, category, standard_cost",
        },
        "purchase_orders": {
            "description": "PO headers",
            "columns": "order_date, supplier_name, total_amount, currency_code, [delivery_date]",
        },
        "purchase_order_items": {
            "description": "PO line items",
            "columns": "po_number, material_name, quantity, unit_price",
        },
    }

    OPTIONAL_FILES = {
        "fx_rates": {
            "description": "Historical FX rates (auto-generated if omitted)",
            "columns": "rate_date, currency_code, rate_to_usd",
        },
    }

    uploaded_dfs: dict[str, pd.DataFrame] = {}
    validation_passed = True

    if upload_method == "📦 ZIP archive (all CSVs in one file)":
        zip_file = st.file_uploader(
            "Upload a ZIP file containing your CSV files",
            type=["zip"],
            help="The ZIP should contain: suppliers.csv, materials.csv, purchase_orders.csv, purchase_order_items.csv",
        )
        if zip_file is not None:
            import zipfile
            import io

            with zipfile.ZipFile(io.BytesIO(zip_file.read())) as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                st.caption(f"Found {len(csv_names)} CSV file(s) in archive: {', '.join(csv_names)}")

                for csv_name in csv_names:
                    stem = Path(csv_name).stem.lower()
                    if stem in REQUIRED_FILES or stem in OPTIONAL_FILES:
                        with zf.open(csv_name) as f:
                            uploaded_dfs[stem] = pd.read_csv(f)

    else:
        st.markdown("Upload the **4 required** CSV files (and optionally `fx_rates.csv`):")
        cols = st.columns(2)

        for i, (name, info) in enumerate(REQUIRED_FILES.items()):
            with cols[i % 2]:
                f = st.file_uploader(
                    f"**{name}.csv** — {info['description']}",
                    type=["csv"],
                    key=f"upload_{name}",
                    help=f"Required columns: {info['columns']}",
                )
                if f is not None:
                    uploaded_dfs[name] = pd.read_csv(f)

        st.divider()
        st.markdown("**Optional:**")
        f = st.file_uploader(
            "fx_rates.csv — Historical FX rates",
            type=["csv"],
            key="upload_fx_rates",
            help="Optional. Auto-generated from live APIs if omitted.",
        )
        if f is not None:
            uploaded_dfs["fx_rates"] = pd.read_csv(f)

    # ── Validation ───────────────────────────────────────────────────────────
    if uploaded_dfs:
        st.divider()
        st.subheader("📋 Validation Results")

        missing = [n for n in REQUIRED_FILES if n not in uploaded_dfs]
        if missing:
            st.error(f"❌ Missing required files: **{', '.join(f'{m}.csv' for m in missing)}**")
            validation_passed = False

        SCHEMA_CHECK = {
            "suppliers": ["supplier_name", "country", "default_currency", "lead_time_days"],
            "materials": ["material_name", "category", "standard_cost"],
            "purchase_orders": ["order_date", "supplier_name", "total_amount", "currency_code"],
            "purchase_order_items": ["po_number", "material_name", "quantity", "unit_price"],
        }

        for name, df in uploaded_dfs.items():
            with st.expander(f"{'✅' if name not in missing else '❌'} **{name}.csv** — {len(df):,} rows, {len(df.columns)} columns", expanded=True):
                # Column check
                if name in SCHEMA_CHECK:
                    required_cols = SCHEMA_CHECK[name]
                    present = [c for c in required_cols if c in df.columns]
                    absent = [c for c in required_cols if c not in df.columns]
                    if absent:
                        st.error(f"Missing columns: {', '.join(absent)}")
                        validation_passed = False
                    else:
                        st.success(f"All required columns present: {', '.join(present)}")

                # Null check
                null_counts = df.isnull().sum()
                nulls = null_counts[null_counts > 0]
                if len(nulls) > 0:
                    st.warning(f"Columns with nulls: {', '.join(f'{c} ({n})' for c, n in nulls.items())}")

                # Preview
                st.dataframe(df.head(10), use_container_width=True, hide_index=True)

        # ── Processing ───────────────────────────────────────────────────────
        st.divider()

        if not missing and validation_passed:
            st.success("✅ All validations passed. Ready to import.")

            col_import, col_info = st.columns([1, 2])
            with col_import:
                run_import = st.button(
                    "🚀 Import & Run Analytics",
                    type="primary",
                    use_container_width=True,
                    disabled=DEMO_MODE,
                )
            with col_info:
                st.caption(
                    "This will: (1) clear existing transactional data, "
                    "(2) import your CSVs, (3) run ETL pipeline, "
                    "(4) run analytics. All dashboard pages will update."
                )

            if run_import and not DEMO_MODE:
                import tempfile
                import shutil

                with st.spinner("Importing data and running analytics pipeline..."):
                    progress = st.progress(0, text="Saving uploaded files...")

                    # Save CSVs to a temp directory
                    tmp_dir = Path(tempfile.mkdtemp(prefix="pvis_upload_"))
                    try:
                        for name, df in uploaded_dfs.items():
                            df.to_csv(tmp_dir / f"{name}.csv", index=False)
                        progress.progress(20, text="Running external data loader...")

                        # Run external data loader
                        from data_ingestion.external_data_loader import ExternalDataLoader
                        loader = ExternalDataLoader(str(tmp_dir))
                        if loader.load_all_files():
                            progress.progress(40, text="Importing into database...")
                            loader.import_data()
                            progress.progress(60, text="Running ETL pipeline...")

                            # Run ETL
                            from data_ingestion.populate_warehouse import main as run_etl
                            run_etl()
                            progress.progress(80, text="Running analytics...")

                            # Run analytics
                            from analytics.advanced_analytics import run_fx_simulation, run_supplier_risk
                            run_supplier_risk()
                            run_fx_simulation(currency_id=3, days=90, simulations=10000)
                            progress.progress(100, text="Complete!")

                            st.success(
                                "🎉 **Import complete!** Your company data is now loaded. "
                                "Navigate to any dashboard page to see your data."
                            )
                            st.balloons()

                            # Clear caches so pages reload with new data
                            st.cache_data.clear()
                        else:
                            st.error("❌ Data validation failed during import. Check your CSV files.")
                    except Exception as e:
                        st.error(f"❌ Import failed: {e}")
                    finally:
                        shutil.rmtree(tmp_dir, ignore_errors=True)
        else:
            st.error("⚠️ Fix the validation errors above before importing.")

    else:
        # Show format guide when no files uploaded
        st.subheader("📘 CSV Format Guide")
        for name, info in {**REQUIRED_FILES, **OPTIONAL_FILES}.items():
            required = "Required" if name in REQUIRED_FILES else "Optional"
            st.markdown(f"**`{name}.csv`** ({required}) — {info['description']}")
            st.code(info["columns"], language=None)

        st.info(
            "💡 **Tip:** Download template files from the "
            "[external_data_samples/](https://github.com/DavidMaco/pvis/tree/main/external_data_samples) "
            "folder to see the exact format expected."
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Pipeline Runner
# ══════════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Pipeline Runner":
    st.title("⚙️ Pipeline Runner")
    st.markdown(
        "Run the PVIS data pipeline stages from this dashboard. "
        "Each stage writes results to the database; the dashboard auto-refreshes."
    )

    if DEMO_MODE:
        st.info(
            "🔒 **Pipeline controls are disabled in demo mode** because no "
            "database is connected. To run pipelines, deploy with a live "
            "MySQL instance and configure `[database]` in Streamlit secrets."
        )

    st.warning(
        "⚠️ Running stages will **overwrite** existing transactional data. "
        "Use with caution in production."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Data Generation & ETL")
        if st.button("1️⃣ Generate Sample Data", use_container_width=True):
            with st.spinner("Generating sample data..."):
                try:
                    from data_ingestion.seed_realistic_data import main as gen_data
                    gen_data()
                    st.success("Sample data generated!")
                except Exception as e:
                    st.error(f"Failed: {e}")

        if st.button("2️⃣ Run ETL / Populate Warehouse", use_container_width=True):
            with st.spinner("Running ETL pipeline..."):
                try:
                    from data_ingestion.populate_warehouse import main as run_etl
                    run_etl()
                    st.success("Warehouse populated!")
                except Exception as e:
                    st.error(f"Failed: {e}")

    with col_b:
        st.subheader("Analytics")
        if st.button("3️⃣ Run FX Simulation", use_container_width=True):
            with st.spinner("Running Monte Carlo simulation (10K paths)..."):
                try:
                    from analytics.advanced_analytics import run_fx_simulation
                    run_fx_simulation(currency_id=3, days=90, simulations=10000)
                    st.success("FX simulation complete!")
                except Exception as e:
                    st.error(f"Failed: {e}")

        if st.button("4️⃣ Run Supplier Risk Scoring", use_container_width=True):
            with st.spinner("Calculating supplier risk metrics..."):
                try:
                    from analytics.advanced_analytics import run_supplier_risk
                    run_supplier_risk()
                    st.success("Supplier risk scores updated!")
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()

    # ── Database health check ────────────────────────────────────────────────
    st.subheader("Database Health Check")
    tables = [
        "dim_date", "dim_supplier", "dim_material", "fact_procurement",
        "supplier_performance_metrics", "supplier_spend_summary",
        "purchase_orders", "purchase_order_items", "fx_rates",
        "quality_incidents", "financial_kpis",
    ]
    health_rows = []
    for tbl in tables:
        cnt_df = run_query(f"SELECT COUNT(*) AS cnt FROM {tbl}")
        cnt = int(cnt_df.iloc[0]["cnt"]) if not cnt_df.empty else 0
        health_rows.append({"Table": tbl, "Row Count": cnt, "Status": "✅" if cnt > 0 else "❌ EMPTY"})
    st.dataframe(pd.DataFrame(health_rows), use_container_width=True, hide_index=True)
