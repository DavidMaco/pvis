from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import matplotlib.pyplot as plt

# Database setup
DATABASE_URL = 'sqlite:///procurement.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_spend_data():
    """Retrieve spend data from database."""
    session = Session()
    query = session.execute("""
        SELECT s.name as supplier, i.amount, i.date, i.category
        FROM invoices i
        JOIN suppliers s ON i.supplier_id = s.id
    """)
    df = pd.DataFrame(query.fetchall(), columns=['supplier', 'amount', 'date', 'category'])
    session.close()
    return df

def analyze_spend(df):
    """Perform basic spend analysis."""
    total_spend = df['amount'].sum()
    spend_by_supplier = df.groupby('supplier')['amount'].sum()
    spend_by_category = df.groupby('category')['amount'].sum()
    print(f"Total Spend: ${total_spend}")
    print("Spend by Supplier:")
    print(spend_by_supplier)
    print("Spend by Category:")
    print(spend_by_category)
    return spend_by_supplier, spend_by_category

def plot_spend(spend_by_supplier, spend_by_category):
    """Generate simple plots."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    spend_by_supplier.plot(kind='bar', ax=ax1, title='Spend by Supplier')
    spend_by_category.plot(kind='pie', ax=ax2, title='Spend by Category', autopct='%1.1f%%')
    plt.tight_layout()
    plt.savefig('analytics/spend_analysis.png')
    plt.show()

if __name__ == '__main__':
    df = get_spend_data()
    if not df.empty:
        supplier_spend, category_spend = analyze_spend(df)
        plot_spend(supplier_spend, category_spend)
    else:
        print("No data found. Run ETL first.")