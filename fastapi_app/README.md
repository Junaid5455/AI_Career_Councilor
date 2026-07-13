# EduPath AI — FastAPI Backend

This folder wraps the original EduPath AI console project with a production-ready
FastAPI layer. **Zero business logic was changed.** Every original module
(`api_client.py`, `config.py`, `interview.py`, `prompts.py`, `report_generator.py`,
`storage.py`, `utils.py`, `validators.py`) sits untouched in the project root.

---

## Directory Layout

```
your-project/
│
├── api_client.py          ← UNCHANGED original modules
├── config.py
├── interview.py
├── prompts.py
├── report_generator.py
├── storage.py
├── utils.py
├── validators.py
├── new_prompt_(e)_Claud-prompt.txt
├── new_prompt_(e)2_Claud-prompt.txt
├── new_prompt_(e)3_Claud-prompt.txt
├── .env                   ← DEEPSEEK_API_KEY goes here
├── reports/               ← auto-created; generated PDFs saved here
│
└── fastapi_app/           ← NEW — FastAPI layer only
    ├── requirements.txt
    ├── README.md
    ├── tests/
    │   └── test_api.py
    └── app/
        ├── __init__.py
        ├── main.py            ← FastAPI app factory + CORS + health check
        ├── schemas.py         ← Pydantic request/response models
        ├── session_store.py   ← In-memory concurrent session registry
        └── routers/
            ├── __init__.py
            ├── sessions.py        ← /sessions/* — 21-step interview
            ├── reports.py         ← /reports/* — AI generation + PDF download
            └── config_router.py   ← /config/* — frontend dropdown lists
```

---

## Setup

### 1. Copy / place files

Put the `fastapi_app/` folder **inside** your existing project root
(next to `api_client.py`, `config.py`, etc.).

### 2. Install dependencies

```bash
cd fastapi_app
pip install -r requirements.txt
```

### 3. Set your API key

Your existing `.env` in the project root already works:

```
DEEPSEEK_API_KEY=sk-...
```

Optionally set CORS origins for production:

```
CORS_ORIGINS=https://yourfrontend.com,https://www.yourfrontend.com
```

### 4. Run the server

From **inside** `fastapi_app/`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag restarts the server on every file save (development only).
Remove it in production.

---

## API Reference

The server auto-generates interactive docs at:

- **Swagger UI** → http://localhost:8000/docs  ← best for manual testing
- **ReDoc**       → http://localhost:8000/redoc

### Endpoint Map

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check |
| GET | `/config/options` | All dropdown lists for the frontend |
| POST | `/sessions/` | Start a new 21-step session |
| GET | `/sessions/{id}` | Get current session state (resume) |
| DELETE | `/sessions/{id}` | Discard a session |
| POST | `/sessions/{id}/steps/personal-info` | Step 2 |
| POST | `/sessions/{id}/steps/secondary-education` | Step 3 |
| POST | `/sessions/{id}/steps/higher-education` | Step 4 |
| POST | `/sessions/{id}/steps/subject-performance` | Step 5 |
| POST | `/sessions/{id}/steps/favourite-subject` | Step 6 |
| POST | `/sessions/{id}/steps/career-decision` | Step 7 |
| POST | `/sessions/{id}/steps/preferred-countries` | Step 8 |
| POST | `/sessions/{id}/steps/interest-ratings` | Step 9 |
| POST | `/sessions/{id}/steps/programming` | Step 10 |
| POST | `/sessions/{id}/steps/math` | Step 11 |
| POST | `/sessions/{id}/steps/communication` | Step 12 |
| POST | `/sessions/{id}/steps/personality` | Step 13 |
| POST | `/sessions/{id}/steps/learning-style` | Step 14 |
| POST | `/sessions/{id}/steps/hobbies` | Step 15 |
| POST | `/sessions/{id}/steps/games` | Step 16 |
| POST | `/sessions/{id}/steps/financial` | Step 17 |
| POST | `/sessions/{id}/steps/family` | Step 18 |
| POST | `/sessions/{id}/steps/career-goals` | Step 19 |
| POST | `/sessions/{id}/steps/lifestyle` | Step 20 |
| POST | `/sessions/{id}/steps/additional-notes` | Step 21 |
| POST | `/reports/career` | Generate AI career report |
| GET | `/reports/career/{id}/download` | Download career PDF |
| POST | `/reports/field-scope` | Generate Field Scope report |
| GET | `/reports/field-scope/download?pdf_path=...` | Download scope PDF |
| POST | `/reports/field-comparison` | Generate Field Comparison report |
| GET | `/reports/field-comparison/download?pdf_path=...` | Download comparison PDF |

---

## Testing

### Option A — Automated tests (no live API key needed)

```bash
# from inside fastapi_app/
pytest tests/test_api.py -v
```

This uses FastAPI's `TestClient` which runs the app in-process.
All tests that don't call the real DeepSeek API pass without a key.

### Option B — Swagger UI (manual, browser)

1. Start the server (see Setup step 4).
2. Open http://localhost:8000/docs
3. Click **POST /sessions/** → **Try it out** → **Execute**
4. Copy the returned `session_id`.
5. Work through each `/steps/*` endpoint in order.
6. After Step 21, POST to `/reports/career` with the `session_id`.

### Option C — curl (terminal)

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Create session
curl -s -X POST http://localhost:8000/sessions/ | python3 -m json.tool

# 3. Submit Step 2 (replace SES001 with your session_id)
curl -s -X POST http://localhost:8000/sessions/SES001/steps/personal-info \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ali Khan",
    "age": 18,
    "gender": "Male",
    "country": "Pakistan",
    "city": "Lahore",
    "native_language": "Urdu",
    "education_language": "English"
  }' | python3 -m json.tool

# 4. Get session state at any time
curl http://localhost:8000/sessions/SES001 | python3 -m json.tool

# 5. Field Scope (no session needed)
curl -s -X POST http://localhost:8000/reports/field-scope \
  -H "Content-Type: application/json" \
  -d '{"field_name": "Software Engineering"}' | python3 -m json.tool
```

### Option D — Postman / Insomnia

Import the OpenAPI schema from http://localhost:8000/openapi.json into
Postman or Insomnia to get all endpoints with auto-generated request bodies.

---

## Connecting to Next.js

In your Next.js project, set:

```
# .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Then call the API from any page or server action:

```ts
// Example: create a session
const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/sessions/`, {
  method: "POST",
});
const { session_id } = await res.json();

// Example: submit Step 2
await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/sessions/${session_id}/steps/personal-info`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name, age, gender, country, city, native_language, education_language }),
});
```

---

## Production Notes

- **Session persistence**: The in-memory store resets on restart. For production,
  replace `session_store.py`'s dict with Redis (`redis-py` or `aioredis`).
  The interface (`create_session`, `get_session`, `save_session_in_memory`) stays identical.

- **Long-running AI calls**: `POST /reports/career` can take 1–5 minutes.
  For production, offload it to a background task queue (Celery + Redis, or
  FastAPI's `BackgroundTasks` for lighter loads) and poll for completion.

- **CORS**: Change `CORS_ORIGINS` in `.env` to your production frontend domain.

- **Gunicorn + Uvicorn workers** (production):
  ```bash
  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
