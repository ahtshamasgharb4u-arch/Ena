# AI Visibility & Search Intelligence API (Flask)

RESTful Flask API that registers business profiles and runs a **3-agent AI pipeline**:

- **Agent 1 (Query Discovery)**: generate 10–20 commercially relevant questions for a business space
- **Agent 2 (Visibility Scoring)**: check whether the target domain appears in AI answers (simulated visibility), and fetch **real** search volume / difficulty from **DataForSEO**
- **Agent 3 (Content Recommendations)**: generate 3–5 actionable content recommendations for top opportunities where the domain is **not visible**

This implementation follows the assessment spec (v1.0) using:

- **Flask app factory** (`create_app()`)
- **SQLAlchemy + Flask-Migrate** migrations
- **Three distinct agent classes** in `app/agents/`
- **Structured JSON prompts** and **strict JSON validation** (Pydantic) with retry/fallback
- Consistent JSON error format

## Model / provider choice (deliberate)

- **OpenAI**: best default for consistent structured JSON generation and broad tooling support.
- **Anthropic**: strong at long-form reasoning; used as an alternative provider via env.

Select provider via `LLM_PROVIDER=openai|anthropic` in `.env`.

## External data API (required)

Search volume and competitive difficulty are fetched from DataForSEO. Configure:

- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`
- `DATAFORSEO_LOCATION_CODE` (default 2840 = US)
- `DATAFORSEO_LANGUAGE_CODE` (default `en`)

If these are missing, the pipeline returns a **422** with a clear error.

## Setup (local)

```bash
cd python/ai_visibility_api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Initialize DB + migrations:

```bash
export FLASK_APP=run.py
flask db upgrade
```

Run:

```bash
python run.py
```

## Setup (Docker)

```bash
cd python/ai_visibility_api
cp .env.example .env
docker compose up --build
```

## API endpoints

- `POST /api/v1/profiles`
- `GET /api/v1/profiles/{profile_uuid}`
- `POST /api/v1/profiles/{profile_uuid}/run`
- `GET /api/v1/profiles/{profile_uuid}/queries?min_score=&status=&page=&per_page=`
- `GET /api/v1/profiles/{profile_uuid}/recommendations`
- `POST /api/v1/queries/{query_uuid}/recheck`

## Opportunity score formula (0–1)

We compute opportunity as a weighted product of:

- **Volume factor**: \( \text{vol\_norm} = \min(1, \log_{10}(1+\text{volume}) / 4) \)
- **Difficulty factor**: \( \text{ease} = 1 - (\text{difficulty}/100) \)
- **Visibility gap**: \( \text{gap} = 1 \) if not visible else \( 0.25 \)
- **Commercial intent**: inferred from query text (best/compare/vs/pricing/alternatives etc.)

Final:

\[
\text{opportunity} = \text{clip}_{0..1}\big(0.45\cdot \text{vol\_norm} + 0.25\cdot \text{ease} + 0.2\cdot \text{gap} + 0.1\cdot \text{intent}\big)
\]

## Architecture

- `app/api/` blueprints implement routes + validation
- `app/services/pipeline.py` orchestrates sequential Agent1 → Agent2 → Agent3 with partial failure handling
- `app/agents/*` contain isolated, testable agents
- `app/utils/json_tools.py` does strict JSON extraction + Pydantic validation + retry
- `app/utils/dataforseo.py` wraps DataForSEO “keywords_data” calls

## Tests

Agent parsing + scoring formula can be tested with mocked LLM responses:

```bash
pytest -q
```

## Notes / trade-offs

- Pipeline runs synchronously (per spec). Typical runtime depends on LLM + DataForSEO latency.
- “Domain visibility in AI answers” is simulated deterministically (because real AI answer scraping is out of scope), but stored as fields per query and can be re-checked via `recheck`.

