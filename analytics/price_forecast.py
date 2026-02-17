import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import joblib

def load_data():
    """Load historical price data (simulated)."""
    # Simulate data: date, commodity_price, demand
    data = {
        'date': pd.date_range('2020-01-01', periods=100, freq='M'),
        'commodity_price': [100 + i*0.5 + (i%10)*2 for i in range(100)],
        'demand': [50 + (i%5)*10 for i in range(100)]
    }
    df = pd.DataFrame(data)
    df['date_ordinal'] = df['date'].map(pd.Timestamp.toordinal)
    return df

def train_model(df):
    """Train a simple linear regression model for price forecasting."""
    X = df[['date_ordinal', 'demand']]
    y = df['commodity_price']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    print(f"Model MSE: {mse}")
    joblib.dump(model, 'analytics/price_forecast_model.pkl')
    return model

def forecast_price(model, future_date, demand):
    """Forecast price for future date."""
    date_ordinal = pd.Timestamp(future_date).toordinal()
    prediction = model.predict([[date_ordinal, demand]])
    return prediction[0]

if __name__ == '__main__':
    df = load_data()
    model = train_model(df)
    # Example forecast
    future_price = forecast_price(model, '2024-01-01', 60)
    print(f"Forecasted price for 2024-01-01 with demand 60: ${future_price:.2f}")