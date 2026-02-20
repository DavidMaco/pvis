# Configuration file
import os

try:
    import streamlit as st
    db = st.secrets["database"]
    DATABASE_URL = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['name']}"
    )
except Exception:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2",
    )

API_KEY_COMMODITY = os.getenv("API_KEY_COMMODITY", "your_api_key")
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")