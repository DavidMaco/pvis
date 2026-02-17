from flask import Flask, render_template_string
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine
from analytics.supplier_scoring import get_top_suppliers
from analytics.market_intelligence import analyze_market_trends, fetch_commodity_prices

app = Flask(__name__)

DATABASE_URL = 'sqlite:///procurement.db'
engine = create_engine(DATABASE_URL)

def get_data():
    df = pd.read_sql("SELECT * FROM invoices", engine)
    return df

@app.route('/')
def dashboard():
    df = get_data()
    if df.empty:
        return "No data available. Run ETL pipeline first."
    
    # Invoice chart
    fig1 = px.bar(df, x='date', y='amount', title='Invoice Amounts Over Time')
    chart1_html = fig1.to_html(full_html=False)
    
    # Top suppliers
    top_suppliers = get_top_suppliers(3)
    fig2 = px.bar(top_suppliers, x='name', y='score', title='Top Suppliers by Score')
    chart2_html = fig2.to_html(full_html=False)
    
    # Market trends
    copper_prices = fetch_commodity_prices('COPPER')
    trends = analyze_market_trends(copper_prices)
    market_info = f"Avg Price: ${trends['avg_price']:.2f}, Trend: {trends['trend']}"
    
    html = f"""
    <html>
    <head><title>Procurement Intelligence Dashboard</title></head>
    <body>
    <h1>Procurement Intelligence Engine</h1>
    <h2>Invoice Overview</h2>
    {chart1_html}
    <h2>Top Suppliers</h2>
    {chart2_html}
    <h2>Market Intelligence</h2>
    <p>{market_info}</p>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(debug=True)