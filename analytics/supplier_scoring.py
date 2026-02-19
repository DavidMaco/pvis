from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd

# Database setup
DATABASE_URL = 'mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_supplier_data():
    """Retrieve supplier data."""
    session = Session()
    query = session.execute(text("""
        SELECT s.id, s.name, s.location, s.rating, AVG(i.amount) as avg_spend, COUNT(i.id) as invoice_count
        FROM suppliers s
        LEFT JOIN invoices i ON s.id = i.supplier_id
        GROUP BY s.id, s.name, s.location, s.rating
    """))
    df = pd.DataFrame(query.fetchall(), columns=['id', 'name', 'location', 'rating', 'avg_spend', 'invoice_count'])
    session.close()
    return df

def score_suppliers(df):
    """Calculate supplier scores based on criteria."""
    # Simple scoring: rating * 0.5 + (1 / avg_spend) * 100 + invoice_count * 0.1
    # Adjust for location risk (e.g., higher risk for certain countries)
    risk_countries = ['China', 'Russia']  # Example geopolitical risks
    df['location_risk'] = df['location'].apply(lambda x: 0.8 if x in risk_countries else 1.0)
    df['score'] = (df['rating'] * 0.4 + (1 / (df['avg_spend'] + 1)) * 50 + df['invoice_count'] * 0.1) * df['location_risk']
    df = df.sort_values('score', ascending=False)
    return df

def get_top_suppliers(n=5):
    """Get top n suppliers."""
    df = get_supplier_data()
    scored_df = score_suppliers(df)
    return scored_df.head(n)

if __name__ == '__main__':
    top_suppliers = get_top_suppliers()
    print("Top Suppliers:")
    print(top_suppliers[['name', 'score']])