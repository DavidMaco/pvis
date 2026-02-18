import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from analytics.risk_assessment import load_risk_data, predict_failure, compliance_check, train_risk_model

def test_load_risk_data():
    df = load_risk_data()
    assert len(df) == 5
    assert list(df.columns) == ['rating', 'avg_spend', 'location_risk', 'failed']

def test_train_risk_model():
    df = load_risk_data()
    model = train_risk_model(df)
    assert model is not None

def test_compliance_check():
    assert compliance_check('Germany') == "Compliant"
    assert compliance_check('China') == "Check Required"