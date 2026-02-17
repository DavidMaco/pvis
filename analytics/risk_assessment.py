import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib

def load_risk_data():
    """Load simulated risk data: features and failure labels."""
    # Simulate: supplier features and if they failed (1) or not (0)
    data = {
        'rating': [4.5, 3.0, 4.0, 2.5, 5.0],
        'avg_spend': [10000, 5000, 8000, 2000, 15000],
        'location_risk': [0.2, 0.7, 0.3, 0.8, 0.1],  # From market_intelligence
        'failed': [0, 1, 0, 1, 0]
    }
    df = pd.DataFrame(data)
    return df

def train_risk_model(df):
    """Train logistic regression for failure prediction."""
    X = df[['rating', 'avg_spend', 'location_risk']]
    y = df['failed']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LogisticRegression()
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    print(f"Risk Model Accuracy: {acc}")
    joblib.dump(model, 'analytics/risk_model.pkl')
    return model

def predict_failure(model, rating, avg_spend, location_risk):
    """Predict failure probability."""
    prob = model.predict_proba([[rating, avg_spend, location_risk]])[0][1]
    return prob

def compliance_check(supplier_location):
    """Check compliance for regulations (simulated)."""
    # Example: REACH compliance for EU
    eu_countries = ['Germany', 'France']
    if supplier_location in eu_countries:
        return "Compliant"
    else:
        return "Check Required"

if __name__ == '__main__':
    df = load_risk_data()
    model = train_risk_model(df)
    # Example prediction
    risk_prob = predict_failure(model, 3.5, 7000, 0.5)
    print(f"Failure Risk Probability: {risk_prob:.2f}")
    compliance = compliance_check('China')
    print(f"Compliance Status: {compliance}")