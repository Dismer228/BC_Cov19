# BC_Cov19

## API (FastAPI)

### Setup
1. Python 3.11+
2. Create and fill `.env` from `.env.example`.
3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Endpoints
- `GET /data/cases_by_region` — queries Snowflake; supports `region_id`, `date_from`, `date_to`, `columns`, `aggregate=rolling_mean`, `window`
- `GET /comments` — list comments from MongoDB with filters
- `POST /comments` — create comment

### Notes
- Requires Snowflake credentials and MongoDB instance.
- MongoDB schema/validators: see `FINAL_REPORT.md`.