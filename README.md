# EduPath AI — Career Counsellor

A smart AI-powered career counselling platform that helps students discover the best career path based on their interests, skills, and personality.

## What is This?

EduPath AI is a web application that:
- **Collects student information** through a 21-step interview
- **Generates AI reports** using DeepSeek AI to suggest career paths
- **Explores career fields** with detailed scope and comparison reports
- **Saves progress** so students can resume anytime

## Features

✅ **21-Step Student Interview** — collects academic background, interests, skills, goals, and personality  
✅ **AI Career Report** — personalized recommendations based on student profile  
✅ **Field Scope Explorer** — detailed information about any career field  
✅ **Field Comparison** — compare 2+ fields side-by-side  
✅ **PDF Export** — download all reports as PDFs  
✅ **Session Persistence** — save progress to `sessions.json`  
✅ **REST API** — ready for frontend integration (Next.js, React, etc.)  

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- DeepSeek API (AI report generation)
- ReportLab (PDF creation)
- Pydantic (data validation)

**Data:**
- JSON file storage (sessions.json)
- Configurable paths (works from any directory)

## Project Structure

```
project/
├── fastapi_app/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py              # app factory + path setup
│   │   ├── schemas.py           # request/response models
│   │   ├── session_store.py     # session management
│   │   └── routers/
│   │       ├── sessions.py      # 21-step endpoints
│   │       ├── reports.py       # AI generation endpoints
│   │       └── config_router.py # dropdown lists
│   ├── tests/
│   │   └── test_api.py          # automated tests
│   ├── requirements.txt
│   ├── README.md
│   └── sessions.json            # student session storage
│
├── api_client.py                # DeepSeek API calls
├── config.py                    # constants & settings
├── prompts.py                   # AI system prompts
├── report_generator.py          # report creation logic
├── storage.py                   # file & data storage
├── interview.py                 # interview step definitions
├── validators.py                # input validation
├── utils.py                     # helper functions
├── new_prompt_(e)_Claud-prompt.txt     # main counselling prompt
├── new_prompt_(e)2_Claud-prompt.txt    # field scope prompt
├── new_prompt_(e)3_Claud-prompt.txt    # field comparison prompt
├── .env                         # API key (not in repo)
└── reports/                     # generated PDFs (auto-created)
```

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/edupath-ai.git
cd edupath-ai
```

### 2. Create `.env` file
In the project root, create a file named `.env`:
```
DEEPSEEK_API_KEY=sk-your-api-key-here
CORS_ORIGINS=http://localhost:3000
```

Get your DeepSeek API key from: https://platform.deepseek.com

### 3. Install dependencies
```bash
cd fastapi_app
pip install -r requirements.txt
```

### 4. Run the server
```bash
cd fastapi_app
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at `http://localhost:8000`

## API Documentation

Open your browser to:
- **Swagger UI** (interactive): `http://localhost:8000/docs`
- **ReDoc** (readable): `http://localhost:8000/redoc`

### Quick Example

**1. Create a new session:**
```bash
curl -X POST http://localhost:8000/sessions/
```
Response:
```json
{ "session_id": "SES001", "message": "..." }
```

**2. Submit Step 2 (Personal Info):**
```bash
curl -X POST http://localhost:8000/sessions/SES001/steps/personal-info \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ali Khan",
    "age": 18,
    "gender": "Male",
    "country": "Pakistan",
    "city": "Lahore",
    "native_language": "Urdu",
    "education_language": "English"
  }'
```

**3. After all 21 steps, generate report:**
```bash
curl -X POST http://localhost:8000/reports/career \
  -H "Content-Type: application/json" \
  -d '{ "session_id": "SES001" }'
```

**4. Download PDF:**
```bash
# Use the pdf_path from the report response
curl http://localhost:8000/reports/career/SES001/download -o report.pdf
```

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Check if server is running |
| GET | `/config/options` | Get all dropdown options |
| POST | `/sessions/` | Create new session |
| GET | `/sessions/{id}` | Get session state |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/steps/*` | Submit interview step (20 endpoints) |
| POST | `/reports/career` | Generate AI career report |
| POST | `/reports/field-scope` | Analyze a career field |
| POST | `/reports/field-comparison` | Compare career fields |

## Testing

Run automated tests (no API key needed):
```bash
cd fastapi_app
pytest tests/test_api.py -v
```

## Connecting a Frontend

### Next.js / React Example

```typescript
// .env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000

// pages/interview.tsx
const createSession = async () => {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/sessions/`, {
    method: "POST",
  });
  const { session_id } = await res.json();
  return session_id;
};

const submitStep = async (sessionId, step, data) => {
  await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE}/sessions/${sessionId}/steps/${step}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
};
```

## Important Notes

**Session Storage:**
- Sessions are stored in `sessions.json` (one session at a time)
- On server restart, the session is automatically loaded from disk
- Use different session IDs to manage multiple students

**Report Generation:**
- Takes 1–5 minutes (depends on AI response time)
- PDFs are saved to the `reports/` folder
- For large scale, consider using a job queue (Celery, Bull)

**Prompt Files:**
- Three prompt files define AI behavior
- Located in project root
- Modify them to customize AI responses
- Changes take effect after server restart

## Production Deployment

For production servers:

1. **Set environment variables:**
   ```bash
   export DEEPSEEK_API_KEY=sk-...
   export CORS_ORIGINS=https://yourdomain.com
   ```

2. **Use a production ASGI server:**
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

3. **Add session persistence** (optional):
   - Replace in-memory store with Redis for multi-server setups
   - Modify only `session_store.py` — other files stay the same

## Troubleshooting

**"Session not found" error:**
- Make sure `sessions.json` is in `fastapi_app/` folder
- Check that session ID is correct (e.g., `SES001`)

**"Prompt file not found" error:**
- Verify `.txt` prompt files are in project root
- Restart the server after moving files

**"API key error" error:**
- Check `.env` file has correct `DEEPSEEK_API_KEY`
- Get key from https://platform.deepseek.com

**DeepSeek API slow/timeout:**
- Normal behavior — can take 1–5 minutes
- Increase timeout in `config.py` if needed

## Contributing

Found a bug or have an idea? Open an issue or pull request!

## License

This project is open source and available under the MIT License.

## Support

Need help?
- Check the `/docs` endpoint for API details
- Read `fastapi_app/README.md` for technical info
- Open an issue on GitHub

---

**Built with ❤️ for students exploring their career path.**
<br>
Author: Junaid Shabeer
