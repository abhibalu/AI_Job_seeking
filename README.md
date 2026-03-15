# TailorAI

An autonomous job-seeking agent that scrapes LinkedIn, evaluates job fit, and tailors your resume — with a plan-then-execute multi-agent loop that revises until the output is clean.

---

## What it does

1. **Scrapes** LinkedIn job listings via Apify on a schedule
2. **Evaluates** each job against your resume: scores it 0–100, identifies gaps, decides apply / tailor / skip
3. **Tailors** your resume for jobs that need it — a planner agent writes a targeted edit plan, a tailor agent executes it, a critic reviews, and the loop revises until no issues remain
4. **Notifies** you via Telegram when high-match jobs are found or tailoring completes
5. **Exports** the tailored resume back to Google Docs

---

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Vite, TailwindCSS |
| Backend | Python, FastAPI |
| Orchestration | LangGraph (stateful multi-agent graph) |
| LLM | OpenRouter (configurable model) |
| Database | Supabase (PostgreSQL) |
| Observability | Langfuse |
| Scraping | Apify → LinkedIn |

---

## Agent pipeline

```
Scraper (Apify) → jobs table

JobEvaluatorAgent
  ├→ skip (low score)    → done
  ├→ apply (high score)  → Telegram notify
  └→ tailor              → JDParserAgent
                              └→ ChangePlannerAgent
                                   └→ ResumeTailorAgent → validate → ResumeCriticAgent
                                        ↑ revise if issues ─────────────────────────┘
                                        └→ save to DB → Telegram notify
```

All agents extend `BaseAgent`, which wraps the OpenAI SDK pointed at OpenRouter with Langfuse tracing. Graph state is checkpointed to Supabase so runs survive restarts.

---

## Running it

```bash
# Backend
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd glassresumatch-ai && npm install && npm run dev

# Observability (optional)
docker-compose -f docker-compose.langfuse.yml up -d
```

Key env vars in `.env`:
```
OPENROUTER_API_KEY, OPENROUTER_MODEL
SUPABASE_URL, SUPABASE_SERVICE_KEY
APIFY_TOKEN, LINKEDIN_SEARCH_URLS
GOOGLE_DRIVE_FOLDER_ID, BASE_RESUME
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
```

---

## Frontend

The UI shows your job pipeline sorted by actionability — apply-ready jobs at the top, skip-worthy at the bottom. Each job has a detail view with keyword gap analysis, resume edit suggestions, and a one-click tailoring trigger. Tailored resumes appear in a side-by-side comparison view with Google Docs export.

---

*Built by Abhijith Sivadas*
