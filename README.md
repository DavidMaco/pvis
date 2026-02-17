# Procurement Intelligence Engine

A production-ready procurement intelligence engine for manufacturing organizations. This repository includes ETL pipelines, analytics, supplier intelligence, risk models, contract automation, and a Flask-based dashboard.

## Quickstart (local)

1. Clone the repository and cd into it

2. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install pinned dependencies:

```powershell
pip install -r pinned-requirements.txt
```

4. Initialize the database and load sample data:

```powershell
python data_ingestion/etl_pipeline.py
```

5. Run tests:

```powershell
python -m unittest discover -v
```

6. Start the app:

```powershell
python app.py
# then open http://127.0.0.1:5000
```

## Deployment

Options:

- Docker (recommended for consistent environments):

```bash
docker build -t procurement-engine .
docker run -p 5000:5000 procurement-engine
```

- Docker Compose:

```bash
docker-compose up --build
```

- GitHub Actions is configured to run tests on push via `.github/workflows/python-app.yml`.

## Repository Contents

- `data_ingestion/` — ETL and sample data
- `analytics/` — models and analysis scripts
- `automation/` — contract NLP and RFP helpers
- `ui/` — Flask dashboard
- `tests/` — unit tests
- `pinned-requirements.txt` — reproducible dependency pins for deployment
- `Dockerfile`, `docker-compose.yml` — containerization

## GitHub push instructions

1. Create a new repository on GitHub (use the web UI).
2. Add your remote and push:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

If you want, provide me the repository URL and I can push for you (requires a personal access token).

## Notes

- All major runtime errors were fixed and unit tests were executed locally. CI is configured to run tests on push.
- For production, switch to PostgreSQL by updating `config.py` and updating the DATABASE_URL accordingly.
- Secrets (API keys) should be stored as GitHub Secrets or environment variables and not committed to the repo.

---

If you want I can create the remote GitHub repo for you and push these commits — provide the repo URL or a token with repo scope.
