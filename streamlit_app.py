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


def _safe_div(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator not in (0, None) else 0.0


def detect_volatility_regimes(log_returns: pd.Series, window: int = 20) -> dict:
    clean = pd.Series(log_returns).dropna().astype(float)
    if clean.empty:
        return {
            "p_low": 0.5,
            "p_high": 0.5,
            "mu_low": 0.0,
            "sigma_low": 1e-6,
            "mu_high": 0.0,
            "sigma_high": 1e-6,
        }

    rolling_vol = clean.rolling(window=window).std().dropna()
    if rolling_vol.empty:
        mu = float(clean.mean())
        sigma = float(clean.std()) if float(clean.std()) > 0 else 1e-6
        return {
            "p_low": 0.5,
            "p_high": 0.5,
            "mu_low": mu,
            "sigma_low": sigma,
            "mu_high": mu,
            "sigma_high": sigma,
        }

    threshold = float(rolling_vol.median())
    aligned = clean.loc[rolling_vol.index]
    high_mask = rolling_vol > threshold

    low_returns = aligned[~high_mask]
    high_returns = aligned[high_mask]
    if low_returns.empty:
        low_returns = aligned
    if high_returns.empty:
        high_returns = aligned

    mu_low = float(low_returns.mean())
    sigma_low = float(low_returns.std()) if float(low_returns.std()) > 0 else 1e-6
    mu_high = float(high_returns.mean())
    sigma_high = float(high_returns.std()) if float(high_returns.std()) > 0 else 1e-6
    p_high = float(high_mask.mean())

    return {
        "p_low": 1.0 - p_high,
        "p_high": p_high,
        "mu_low": mu_low,
        "sigma_low": sigma_low,
        "mu_high": mu_high,
        "sigma_high": sigma_high,
    }


def simulate_regime_weighted_paths(current_rate: float, days: int, simulations: int, regime: dict, seed: int = 42):
    dt = 1 / 252
    rng = np.random.default_rng(seed)
    paths = np.zeros((simulations, days), dtype=float)

    for i in range(simulations):
        rate = float(current_rate)
        for d in range(days):
            if rng.random() < regime["p_high"]:
                shock = rng.normal(regime["mu_high"] * dt, regime["sigma_high"] * np.sqrt(dt))
            else:
                shock = rng.normal(regime["mu_low"] * dt, regime["sigma_low"] * np.sqrt(dt))
            rate *= np.exp(shock)
            paths[i, d] = rate
    return paths


def build_working_capital_scenarios(dio: float, dpo: float, ccc: float) -> pd.DataFrame:
    dso = ccc - dio + dpo
    scenarios = [
        {"Scenario": "Base", "DIO Δ%": 0, "DPO Δ%": 0, "DSO Δ%": 0},
        {"Scenario": "Stress", "DIO Δ%": 15, "DPO Δ%": -10, "DSO Δ%": 10},
        {"Scenario": "Optimized", "DIO Δ%": -10, "DPO Δ%": 10, "DSO Δ%": -5},
    ]
    rows = []
    for s in scenarios:
        dio_s = dio * (1 + s["DIO Δ%"] / 100)
        dpo_s = dpo * (1 + s["DPO Δ%"] / 100)
        dso_s = dso * (1 + s["DSO Δ%"] / 100)
        ccc_s = dio_s + dso_s - dpo_s
        rows.append({
            "Scenario": s["Scenario"],
            "DIO": dio_s,
            "DPO": dpo_s,
            "DSO": dso_s,
            "CCC": ccc_s,
            "CCC vs Base": ccc_s - ccc,
        })
    return pd.DataFrame(rows)


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

    # ── KPI snapshot (de-cluttered) ─────────────────────────────────────────

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

    # Procurement Cost Volatility Index (monthly spend volatility / mean)
    pcvi_df = run_query("""
        SELECT
            DATE_FORMAT(d.full_date, '%Y-%m') AS month,
            SUM(f.total_usd_value) AS spend_usd
        FROM fact_procurement f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY DATE_FORMAT(d.full_date, '%Y-%m')
        ORDER BY month
    """)
    if len(pcvi_df) > 1:
        monthly_std = float(pcvi_df["spend_usd"].std())
        monthly_mean = float(pcvi_df["spend_usd"].mean())
        pcvi = _safe_div(monthly_std, monthly_mean) * 100
    else:
        pcvi = 0.0

    # Working Capital Forecast (simple trend on historical CCC)
    wc_hist_df = run_query("SELECT kpi_date, ccc FROM financial_kpis ORDER BY kpi_date")
    wc_forecast = ccc_val
    if len(wc_hist_df) >= 3:
        y = wc_hist_df["ccc"].astype(float).values
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        wc_forecast = float(intercept + slope * (len(y) + 3))

    # Scenario comparison (Base vs Stress +20%)
    scenario_base_df = run_query("""
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
    stress_delta = 0.0
    if not scenario_base_df.empty and scenario_base_df.iloc[0]["spend_usd"]:
        base_total = float(scenario_base_df.iloc[0]["spend_usd"])
        non_usd = float(scenario_base_df.iloc[0]["non_usd_spend"] or 0)
        stress_total = (base_total - non_usd) + non_usd * 1.2
        stress_delta = stress_total - base_total

    # Current NGN rate — live API with DB fallback
    ngn_rate = _fetch_live_ngn_rate()

    st.subheader("KPI Snapshot")
    core1, core2, core3, core4 = st.columns(4)
    core1.metric("Total Spend", f"${total_spend:,.0f}")
    core2.metric("FX Exposure", f"{fx_pct:.1f}%")
    core3.metric("Avg Risk", f"{avg_risk:.1f}")
    core4.metric("CCC", f"{ccc_val:,.0f} days")

    dec1, dec2, dec3, dec4 = st.columns(4)
    dec1.metric("USD/NGN", f"₦{ngn_rate:,.2f}")
    dec2.metric("Cost Volatility", f"{pcvi:.1f}%")
    dec3.metric("WC Forecast (+3m)", f"{wc_forecast:,.1f} days")
    dec4.metric("Stress Delta (+20%)", f"${stress_delta:,.0f}")

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
            st.plotly_chart(fig, width='stretch')

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
            st.plotly_chart(fig, width='stretch')

    st.subheader("Supplier Risk Heatmap")
    heat_df = run_query("""
        SELECT s.supplier_name,
               spm.avg_lead_time, spm.avg_defect_rate,
               spm.cost_variance_pct, spm.on_time_delivery_pct,
               spm.fx_exposure_pct, spm.composite_risk_score
        FROM supplier_performance_metrics spm
        JOIN suppliers s ON spm.supplier_id = s.supplier_id
        ORDER BY spm.composite_risk_score DESC
    """)
    if not heat_df.empty:
        heat_metrics = [
            "avg_lead_time", "avg_defect_rate", "cost_variance_pct",
            "on_time_delivery_pct", "fx_exposure_pct", "composite_risk_score",
        ]
        z = heat_df.set_index("supplier_name")[heat_metrics]
        z_norm = (z - z.min()) / (z.max() - z.min() + 1e-9)
        fig = px.imshow(
            z_norm.values,
            y=z_norm.index.tolist(),
            x=["Lead Time", "Defect %", "Cost Var %", "OTD %", "FX Exp %", "Composite"],
            color_continuous_scale="YlOrRd",
            aspect="auto",
        )
        fig.update_layout(height=max(320, len(z_norm) * 42))
        st.plotly_chart(fig, width='stretch')


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
    st.plotly_chart(fig_hist, width='stretch')

    # ── Run Monte Carlo ──────────────────────────────────────────────────────
    if st.button("🎲 Run Monte Carlo Simulation", type="primary"):
        hist_df["log_return"] = np.log(hist_df["rate_to_usd"] / hist_df["rate_to_usd"].shift(1))
        hist_df = hist_df.dropna()
        regime = detect_volatility_regimes(hist_df["log_return"])
        paths = simulate_regime_weighted_paths(
            current_rate=current_rate,
            days=sim_days,
            simulations=sim_count,
            regime=regime,
            seed=42,
        )

        p5 = np.percentile(paths, 5, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p95 = np.percentile(paths, 95, axis=0)

        # Summary metrics (de-cluttered layout)
        st.subheader("Simulation Snapshot")
        top1, top2, top3 = st.columns(3)
        top1.metric("Current Rate", f"{current_rate:,.4f}")
        top2.metric("P50 (Median)", f"{p50[-1]:,.4f}")
        top3.metric("High-Vol Weight", f"{regime['p_high']:.1%}")

        bot1, bot2 = st.columns(2)
        bot1.metric("P5 (Downside)", f"{p5[-1]:,.4f}")
        bot2.metric("P95 (Upside)", f"{p95[-1]:,.4f}")

        st.caption(
            f"Rate source: {current_rate_source}. "
            f"Regime detection — low-vol μ={regime['mu_low']:.6f}, σ={regime['sigma_low']:.6f}; "
            f"high-vol μ={regime['mu_high']:.6f}, σ={regime['sigma_high']:.6f}."
        )

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
        st.plotly_chart(fig_fan, width='stretch')

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
        st.plotly_chart(fig_dist, width='stretch')

        # VaR on FX-exposed spend
        exposure_df = run_query("""
            SELECT
                SUM((poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)) AS total_spend_usd,
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

        if not exposure_df.empty and exposure_df.iloc[0]["non_usd_spend"]:
            non_usd_spend = float(exposure_df.iloc[0]["non_usd_spend"] or 0)
            terminal_change = (final_rates / current_rate) - 1.0
            pnl = non_usd_spend * terminal_change
            var95 = np.percentile(pnl, 5)
            cvar95 = pnl[pnl <= var95].mean() if np.any(pnl <= var95) else var95

            st.subheader("Value-at-Risk (FX Exposure)")
            v1, v2 = st.columns(2)
            v1.metric("VaR 95% (1-tail)", f"${abs(var95):,.0f}")
            v2.metric("CVaR 95%", f"${abs(cvar95):,.0f}")

        # Explicit FX Shock Sensitivity table (±10%, ±20%)
        st.subheader("FX Shock Sensitivity (±10%, ±20%)")
        sensitivity_rows = []
        for shock in [-20, -10, 10, 20]:
            shocked_rate = current_rate * (1 + shock / 100)
            rate_change = shocked_rate / current_rate - 1
            sensitivity_rows.append(
                {
                    "Shock %": shock,
                    f"{chosen_code} Rate": shocked_rate,
                    "Rate Change %": rate_change * 100,
                }
            )
        sensitivity_df = pd.DataFrame(sensitivity_rows)
        st.dataframe(
            sensitivity_df.style.format({
                f"{chosen_code} Rate": "{:,.4f}",
                "Rate Change %": "{:+.1f}%",
            }),
            width='stretch',
            hide_index=True,
        )


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

    # Fix encoding corruption from cloud DB import (São → S??o / S├úo)
    for col in perf_df.select_dtypes(include="object").columns:
        perf_df[col] = perf_df[col].str.replace(r"S[\u00e3\u00c3\u0103]o", "Sao", regex=True)
        perf_df[col] = perf_df[col].str.replace(r"S..o(?= Paulo)", "Sao", regex=True)

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
    st.plotly_chart(fig_heat, width='stretch')

    # ── Detail table ─────────────────────────────────────────────────────────
    st.subheader("Detailed Metrics")

    def _risk_bg(val):
        """Risk score → CSS background color (no matplotlib needed)."""
        try:
            v = float(val)
        except (ValueError, TypeError):
            return ""
        if v >= 7:
            return "background-color: #fecaca; color: #991b1b"
        elif v >= 5:
            return "background-color: #fed7aa; color: #9a3412"
        elif v >= 3:
            return "background-color: #fef9c3; color: #854d0e"
        else:
            return "background-color: #bbf7d0; color: #166534"

    st.dataframe(
        perf_df.style.format({
            "avg_lead_time": "{:.1f}",
            "lead_time_stddev": "{:.2f}",
            "avg_defect_rate": "{:.2f}%",
            "cost_variance_pct": "{:.2f}%",
            "on_time_delivery_pct": "{:.1f}%",
            "fx_exposure_pct": "{:.1f}%",
            "composite_risk_score": "{:.2f}",
        }).map(_risk_bg, subset=["composite_risk_score"]),
        width='stretch',
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
    st.plotly_chart(fig_lt, width='stretch')

    trend_left, trend_right = st.columns(2)

    with trend_left:
        st.subheader("Lead Time Trend")
        lt_trend_df = run_query("""
            SELECT
                DATE_FORMAT(order_date, '%Y-%m') AS month,
                AVG(DATEDIFF(delivery_date, order_date)) AS avg_lead_time
            FROM purchase_orders
            WHERE delivery_date IS NOT NULL
            GROUP BY DATE_FORMAT(order_date, '%Y-%m')
            ORDER BY month
        """)
        if not lt_trend_df.empty:
            fig = px.line(
                lt_trend_df,
                x="month",
                y="avg_lead_time",
                markers=True,
                labels={"avg_lead_time": "Avg Lead Time (days)", "month": "Month"},
            )
            fig.update_layout(height=330)
            st.plotly_chart(fig, width='stretch')

    with trend_right:
        st.subheader("Cost Volatility Trend")
        cv_trend_df = run_query("""
            SELECT
                DATE_FORMAT(po.order_date, '%Y-%m') AS month,
                STDDEV(poi.unit_price) AS cost_volatility
            FROM purchase_orders po
            JOIN purchase_order_items poi ON po.po_id = poi.po_id
            GROUP BY DATE_FORMAT(po.order_date, '%Y-%m')
            ORDER BY month
        """)
        if not cv_trend_df.empty:
            fig = px.line(
                cv_trend_df,
                x="month",
                y="cost_volatility",
                markers=True,
                labels={"cost_volatility": "Std Dev of Unit Price", "month": "Month"},
            )
            fig.update_layout(height=330)
            st.plotly_chart(fig, width='stretch')

    st.subheader("Country Risk Exposure Map")
    country_risk_df = run_query("""
        SELECT
            c.country_name,
            AVG(s.risk_index) AS geographic_risk_index,
            SUM((poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)) AS exposure_usd
        FROM suppliers s
        JOIN countries c ON s.country_id = c.country_id
        JOIN purchase_orders po ON po.supplier_id = s.supplier_id
        JOIN purchase_order_items poi ON po.po_id = poi.po_id
        LEFT JOIN fx_rates fx ON po.currency_id = fx.currency_id
            AND fx.rate_date = (
                SELECT MAX(rate_date) FROM fx_rates f2
                WHERE f2.currency_id = po.currency_id AND f2.rate_date <= po.order_date
            )
        GROUP BY c.country_name
        ORDER BY exposure_usd DESC
    """)
    if not country_risk_df.empty:
        fig = px.choropleth(
            country_risk_df,
            locations="country_name",
            locationmode="country names",
            color="geographic_risk_index",
            hover_data={"exposure_usd": ":,.0f", "geographic_risk_index": ":.2f"},
            color_continuous_scale="OrRd",
            title="Geographic Risk Index by Country",
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, width='stretch')


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
            st.plotly_chart(fig, width='stretch')

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
            st.plotly_chart(fig, width='stretch')

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
        st.plotly_chart(fig, width='stretch')

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
        st.plotly_chart(fig, width='stretch')


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
        st.plotly_chart(fig, width='stretch')

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
            st.plotly_chart(fig, width='stretch')

    with right:
        st.subheader("Receivables Trend")
        rec_df = run_query(
            "SELECT summary_date, accounts_receivable_usd FROM receivables_summary ORDER BY summary_date"
        )
        if not rec_df.empty:
            fig = px.line(rec_df, x="summary_date", y="accounts_receivable_usd")
            fig.update_layout(height=300)
            st.plotly_chart(fig, width='stretch')

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

        # Inventory turnover KPI
        spend_df = run_query("SELECT SUM(total_usd_value) AS total_spend FROM fact_procurement")
        total_spend = float(spend_df.iloc[0]["total_spend"] or 0) if not spend_df.empty else 0
        annual_spend = total_spend / 3 if total_spend > 0 else 0
        avg_inventory = float(inv_df["total_inv"].mean()) if not inv_df.empty else 0
        inventory_turnover = _safe_div(annual_spend, avg_inventory)
        st.metric("Inventory Turnover (annualized)", f"{inventory_turnover:,.2f}x")

        # Working capital stress simulation (CCC)
        st.subheader("Cash Conversion Cycle Simulation")
        wc_scenarios = build_working_capital_scenarios(
            dio=float(row["dio"]),
            dpo=float(row["dpo"]),
            ccc=float(row["ccc"]),
        )
        fig = px.bar(
            wc_scenarios,
            x="Scenario",
            y="CCC",
            color="CCC",
            color_continuous_scale="RdYlGn_r",
            labels={"CCC": "Cash Conversion Cycle (days)"},
        )
        fig.update_layout(height=320)
        st.plotly_chart(fig, width='stretch')

        st.dataframe(
            wc_scenarios.style.format({
                "DIO": "{:.1f}",
                "DPO": "{:.1f}",
                "DSO": "{:.1f}",
                "CCC": "{:.1f}",
                "CCC vs Base": "{:+.1f}",
            }),
            width='stretch',
            hide_index=True,
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
        st.plotly_chart(fig, width='stretch')

        st.dataframe(
            scenario_df.style.format({
                "Baseline USD": "${:,.0f}",
                "Stressed USD": "${:,.0f}",
                "Impact USD": "${:,.0f}",
            }),
            width='stretch',
            hide_index=True,
        )

        st.divider()
        st.subheader("Landed Cost Model")
        st.caption("Components: base cost, freight, insurance, duties, FX impact, and payment delay cost")

        assumption_col1, assumption_col2 = st.columns(2)
        with assumption_col1:
            insurance_pct = st.slider("Insurance %", 0.0, 5.0, 1.5, 0.1) / 100
            annual_carry_rate = st.slider("Payment delay financing % (annual)", 0.0, 30.0, 12.0, 0.5) / 100
        with assumption_col2:
            freight_scale = st.slider("Freight scaling factor", 0.5, 2.0, 1.0, 0.1)
            duty_scale = st.slider("Duty scaling factor", 0.5, 2.0, 1.0, 0.1)

        landed_df = run_query("""
            SELECT
                s.supplier_name,
                c.country_name,
                COALESCE(spm.avg_lead_time, s.lead_time_days) AS lead_time_days,
                COALESCE(spm.fx_exposure_pct, 0) AS fx_exposure_pct,
                COALESCE(s.risk_index, 0) AS geographic_risk_index,
                SUM((poi.quantity * poi.unit_price) / COALESCE(fx.rate_to_usd, 1)) AS base_cost_usd
            FROM suppliers s
            JOIN countries c ON s.country_id = c.country_id
            JOIN purchase_orders po ON po.supplier_id = s.supplier_id
            JOIN purchase_order_items poi ON poi.po_id = po.po_id
            LEFT JOIN supplier_performance_metrics spm ON spm.supplier_id = s.supplier_id
            LEFT JOIN fx_rates fx ON po.currency_id = fx.currency_id
                AND fx.rate_date = (
                    SELECT MAX(rate_date) FROM fx_rates f2
                    WHERE f2.currency_id = po.currency_id AND f2.rate_date <= po.order_date
                )
            GROUP BY s.supplier_name, c.country_name, COALESCE(spm.avg_lead_time, s.lead_time_days),
                     COALESCE(spm.fx_exposure_pct, 0), COALESCE(s.risk_index, 0)
            ORDER BY base_cost_usd DESC
        """)

        if not landed_df.empty:
            freight_by_country = {
                "Nigeria": 0.08,
                "Germany": 0.05,
                "China": 0.10,
                "India": 0.09,
                "United States": 0.04,
                "United Kingdom": 0.05,
                "Brazil": 0.09,
                "South Africa": 0.08,
            }
            duty_by_country = {
                "Nigeria": 0.06,
                "Germany": 0.04,
                "China": 0.08,
                "India": 0.07,
                "United States": 0.03,
                "United Kingdom": 0.03,
                "Brazil": 0.06,
                "South Africa": 0.05,
            }

            landed_df["freight_usd"] = landed_df.apply(
                lambda r: r["base_cost_usd"] * freight_by_country.get(r["country_name"], 0.06) * freight_scale,
                axis=1,
            )
            landed_df["insurance_usd"] = landed_df["base_cost_usd"] * insurance_pct
            landed_df["duties_usd"] = landed_df.apply(
                lambda r: r["base_cost_usd"] * duty_by_country.get(r["country_name"], 0.05) * duty_scale,
                axis=1,
            )
            landed_df["fx_impact_usd"] = landed_df["base_cost_usd"] * (landed_df["fx_exposure_pct"] / 100) * (shock_pct / 100)
            landed_df["payment_delay_cost_usd"] = (
                landed_df["base_cost_usd"] * annual_carry_rate * (landed_df["lead_time_days"] / 365)
            )
            landed_df["landed_cost_usd"] = (
                landed_df["base_cost_usd"]
                + landed_df["freight_usd"]
                + landed_df["insurance_usd"]
                + landed_df["duties_usd"]
                + landed_df["fx_impact_usd"]
                + landed_df["payment_delay_cost_usd"]
            )

            component_totals = pd.DataFrame([
                {"Component": "Base Cost", "USD": landed_df["base_cost_usd"].sum()},
                {"Component": "Freight", "USD": landed_df["freight_usd"].sum()},
                {"Component": "Insurance", "USD": landed_df["insurance_usd"].sum()},
                {"Component": "Duties", "USD": landed_df["duties_usd"].sum()},
                {"Component": "FX Impact", "USD": landed_df["fx_impact_usd"].sum()},
                {"Component": "Payment Delay Cost", "USD": landed_df["payment_delay_cost_usd"].sum()},
            ])

            fig = px.bar(
                component_totals,
                x="Component",
                y="USD",
                color="USD",
                color_continuous_scale="Blues",
                labels={"USD": "Total USD"},
            )
            fig.update_layout(height=340)
            st.plotly_chart(fig, width='stretch')

            st.dataframe(
                landed_df[[
                    "supplier_name", "country_name", "base_cost_usd", "freight_usd", "insurance_usd",
                    "duties_usd", "fx_impact_usd", "payment_delay_cost_usd", "landed_cost_usd",
                ]].style.format({
                    "base_cost_usd": "${:,.0f}",
                    "freight_usd": "${:,.0f}",
                    "insurance_usd": "${:,.0f}",
                    "duties_usd": "${:,.0f}",
                    "fx_impact_usd": "${:,.0f}",
                    "payment_delay_cost_usd": "${:,.0f}",
                    "landed_cost_usd": "${:,.0f}",
                }),
                width='stretch',
                hide_index=True,
            )

            # Procurement Volatility Audit deliverables
            st.divider()
            st.subheader("Procurement Volatility Audit")

            fx_exposure_analysis = pd.DataFrame([
                {
                    "Metric": "FX Exposure % of Spend",
                    "Value": f"{(base_non_usd / base_total * 100) if base_total else 0:.1f}%",
                },
                {
                    "Metric": "Stress +20% Impact",
                    "Value": f"${scenario_df.loc[scenario_df['Scenario'].str.contains('Severe'), 'Impact USD'].iloc[0]:,.0f}",
                },
            ])

            supplier_risk_assessment = run_query("""
                SELECT s.supplier_name, spm.composite_risk_score, spm.on_time_delivery_pct,
                       spm.avg_defect_rate, spm.cost_variance_pct, spm.fx_exposure_pct
                FROM supplier_performance_metrics spm
                JOIN suppliers s ON s.supplier_id = spm.supplier_id
                ORDER BY spm.composite_risk_score DESC
                LIMIT 10
            """)

            wc_df = run_query("SELECT dio, dpo, ccc FROM financial_kpis ORDER BY kpi_date DESC LIMIT 1")
            if not wc_df.empty:
                wc_base = wc_df.iloc[0]
                wc_stress = build_working_capital_scenarios(float(wc_base["dio"]), float(wc_base["dpo"]), float(wc_base["ccc"]))
            else:
                wc_stress = pd.DataFrame()

            optimization_reco = pd.DataFrame([
                {"Recommendation": "Increase hedge coverage for non-USD supplier contracts", "Priority": "High"},
                {"Recommendation": "Negotiate freight corridors for high-cost geographies", "Priority": "High"},
                {"Recommendation": "Apply duty optimization and bonded-warehouse routing", "Priority": "Medium"},
                {"Recommendation": "Tie payment terms to supplier risk and OTD performance", "Priority": "Medium"},
                {"Recommendation": "Set monthly trigger alerts for cost volatility and lead-time spikes", "Priority": "High"},
            ])

            a1, a2 = st.columns(2)
            with a1:
                st.markdown("**FX exposure analysis**")
                st.dataframe(fx_exposure_analysis, width='stretch', hide_index=True)
                st.markdown("**Landed cost breakdown**")
                st.dataframe(component_totals.style.format({"USD": "${:,.0f}"}), width='stretch', hide_index=True)
            with a2:
                st.markdown("**Cost optimization recommendations**")
                st.dataframe(optimization_reco, width='stretch', hide_index=True)

            st.markdown("**Supplier risk assessment**")
            if not supplier_risk_assessment.empty:
                st.dataframe(
                    supplier_risk_assessment.style.format({
                        "composite_risk_score": "{:.2f}",
                        "on_time_delivery_pct": "{:.1f}%",
                        "avg_defect_rate": "{:.2f}%",
                        "cost_variance_pct": "{:.2f}%",
                        "fx_exposure_pct": "{:.1f}%",
                    }),
                    width='stretch',
                    hide_index=True,
                )

            st.markdown("**Working capital stress test**")
            if not wc_stress.empty:
                st.dataframe(
                    wc_stress.style.format({
                        "DIO": "{:.1f}",
                        "DPO": "{:.1f}",
                        "DSO": "{:.1f}",
                        "CCC": "{:.1f}",
                        "CCC vs Base": "{:+.1f}",
                    }),
                    width='stretch',
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
                st.dataframe(df.head(10), width='stretch', hide_index=True)

        # ── Processing ───────────────────────────────────────────────────────
        st.divider()

        if not missing and validation_passed:
            st.success("✅ All validations passed. Ready to import.")

            col_import, col_info = st.columns([1, 2])
            with col_import:
                run_import = st.button(
                    "🚀 Import & Run Analytics",
                    type="primary",
                    width='stretch',
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
        if st.button("1️⃣ Generate Sample Data", width='stretch'):
            with st.spinner("Generating sample data..."):
                try:
                    from data_ingestion.seed_realistic_data import main as gen_data
                    gen_data()
                    st.success("Sample data generated!")
                except Exception as e:
                    st.error(f"Failed: {e}")

        if st.button("2️⃣ Run ETL / Populate Warehouse", width='stretch'):
            with st.spinner("Running ETL pipeline..."):
                try:
                    from data_ingestion.populate_warehouse import main as run_etl
                    run_etl()
                    st.success("Warehouse populated!")
                except Exception as e:
                    st.error(f"Failed: {e}")

    with col_b:
        st.subheader("Analytics")
        if st.button("3️⃣ Run FX Simulation", width='stretch'):
            with st.spinner("Running Monte Carlo simulation (10K paths)..."):
                try:
                    from analytics.advanced_analytics import run_fx_simulation
                    run_fx_simulation(currency_id=3, days=90, simulations=10000)
                    st.success("FX simulation complete!")
                except Exception as e:
                    st.error(f"Failed: {e}")

        if st.button("4️⃣ Run Supplier Risk Scoring", width='stretch'):
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
    st.dataframe(pd.DataFrame(health_rows), width='stretch', hide_index=True)
