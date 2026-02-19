import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = 'mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2'
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define tables
class Supplier(Base):
    __tablename__ = 'suppliers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    rating = Column(Float)

class Invoice(Base):
    __tablename__ = 'invoices'
    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer)
    amount = Column(Float)
    date = Column(Date)
    category = Column(String)  # e.g., raw materials

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def extract_data(file_path):
    """Extract data from CSV file."""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        # Simulate sample data
        return pd.DataFrame({
            'supplier_name': ['Supplier A', 'Supplier B'],
            'location': ['USA', 'China'],
            'rating': [4.5, 3.8],
            'amount': [10000, 15000],
            'date': ['2023-01-01', '2023-01-02'],
            'category': ['Raw Materials', 'Components']
        })

def transform_data(df):
    """Clean and transform data."""
    df['date'] = pd.to_datetime(df['date'])
    df['rating'] = df['rating'].fillna(3.0)  # Default rating
    return df

def load_data(df):
    """Load data into database."""
    session = Session()
    for _, row in df.iterrows():
        # Insert supplier if not exists
        supplier = session.query(Supplier).filter_by(name=row['supplier_name']).first()
        if not supplier:
            supplier = Supplier(name=row['supplier_name'], location=row['location'], rating=row['rating'])
            session.add(supplier)
            session.commit()
        # Insert invoice
        invoice = Invoice(supplier_id=supplier.id, amount=row['amount'], date=row['date'], category=row['category'])
        session.add(invoice)
    session.commit()
    session.close()

if __name__ == '__main__':
    data = extract_data('sample_data.csv')
    transformed_data = transform_data(data)
    load_data(transformed_data)
    print("ETL pipeline completed.")