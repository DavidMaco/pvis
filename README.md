# Procurement Intelligence Engine

A comprehensive procurement intelligence engine for manufacturing firms, designed to analyze supplier data, predict costs, and optimize procurement decisions.

## Features

- Data ingestion from various sources (ERP, APIs, market feeds)
- Analytics for spend analysis, supplier scoring, and risk assessment
- Predictive models for price forecasting and demand planning
- User interface for dashboards and reporting
- Automation for RFP and contract management

## Setup

1. Install Python 3.9+
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run ETL: `python data_ingestion/etl_pipeline.py`
6. Run analytics: `python analytics/spend_analysis.py` or `python analytics/price_forecast.py`
7. Run app: `python app.py`
8. Run tests: `python -m unittest tests/test_etl.py`

## Project Structure

- `data_ingestion/`: ETL pipelines and data collection scripts
- `analytics/`: ML models and analysis modules
- `ui/`: Web interface and dashboards
- `tests/`: Unit and integration tests