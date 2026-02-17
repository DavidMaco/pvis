import requests
import pandas as pd
from datetime import datetime, timedelta

# Simulate market data fetching (replace with real API)
def fetch_commodity_prices(commodity='COPPER'):
    """Fetch current commodity prices (simulated)."""
    # In real: use API like Alpha Vantage or Quandl
    # Example: response = requests.get(f'https://api.example.com/commodity/{commodity}')
    # For now, simulate
    base_price = 3.5 if commodity == 'COPPER' else 2.0  # USD per lb or something
    prices = []
    for i in range(30):  # Last 30 days
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        price = base_price + (i % 10) * 0.1  # Fluctuate
        prices.append({'date': date, 'price': price, 'commodity': commodity})
    return pd.DataFrame(prices)

def analyze_market_trends(df):
    """Analyze trends: average price, volatility."""
    avg_price = df['price'].mean()
    volatility = df['price'].std()
    trend = 'Increasing' if df['price'].iloc[0] < df['price'].iloc[-1] else 'Decreasing'
    return {'avg_price': avg_price, 'volatility': volatility, 'trend': trend}

def get_geopolitical_risks():
    """Simulate geopolitical risk data."""
    # In real, integrate with news APIs or risk indices
    risks = {
        'China': 0.7,  # High risk
        'USA': 0.2,
        'Germany': 0.3
    }
    return risks

if __name__ == '__main__':
    copper_prices = fetch_commodity_prices('COPPER')
    trends = analyze_market_trends(copper_prices)
    print(f"Copper Market Trends: {trends}")
    risks = get_geopolitical_risks()
    print(f"Geopolitical Risks: {risks}")