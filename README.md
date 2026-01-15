# TailorAI: AI-Powered Job Application Assistant

**TailorAI** is an advanced agentic system designed to supercharge your job search. It uses a rigorous "Triangle of Power" architecture to Evaluate, Parse, and Tailor your resume for specific job descriptions, ensuring every application is truthful, targeted, and ATS-optimized.

![Frontend UI](glassresumatch-ai/public/og-image.png)

## 🚀 Key Features

### 1. 🧠 AI Job Evaluator
- **Strategic Analysis**: Acts as a senior career coach.
- **Scoring**: Provides a 1-100 Match Score based on Experience, Skills, and hard requirements from the JD.
- **Gap Analysis**: Identifies Technical, Domain, and Soft Skill gaps.
- **Interview Prep**: Generates custom interview questions and study topics.

### 2. ✂️ Resume Tailoring System ("The Editor")
- **Conservative Strategy**: Applying the "40% Rule" — it edits ~40% of the content to align with the JD while strictly preserving truth and structure.
- **Diff View**: Visual side-by-side comparison of your Base and Tailored resume (Yellow highlights changes).
- **Control**: You Approve or Reject every tailored version.
- **ATS Optimization**: Injects keywords found by the JD Parser.

### 3. 🔍 JD Parser ("The Dictionary")
- **Signal Extraction**: Extracts "Must Haves", "Nice to Haves", and "ATS Keywords" from noisy JD text.
- **Normalization**: Standardizes skills taxonomy.

### 4. 🗄️ Single Source of Truth
- **Database-First**: Your Master Resume lives in the Database (`resumes` table).
- **Editor Tools**: Any manual edits you make are saved and immediately recognized by the Agents for future tailoring.

## 🏗️ Architecture

### Tech Stack
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS (Glassmorphism UI).
- **Backend**: FastAPI (Python), Async implementation.
- **AI/LLM**: OpenRouter (Gemini Pro/Flash, GLM-4) for agent reasoning.
- **Database**: Supabase (PostgreSQL) is the primary cloud store. SQLite is available as a local fallback.
- **Data Lake**: Delta Lake (local) for raw/processed job data text mining.

### Folder Structure
```
TailorAI/
├── agents/             # The brain (Evaluator, Parser, Tailor)
├── agent_prompts/      # System prompts (Markdown)
├── api/                # FastAPI routes
├── glassresumatch-ai/  # Next.js Frontend
│   ├── components/     # UI Components (JobModal, ResumePreview...)
│   └── services/       # API Client which talks to Backend
├── lakehouse/          # Delta Lake logic (Bronze/Silver/Gold)
└── scripts/            # Admin tools & migration scripts
```

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Supabase account (or use local SQLite)
- OpenRouter API Key

### 2. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Environment
cp .env.example .env
# Edit .env with your keys:
# OPENROUTER_API_KEY=sk-...
# SUPABASE_URL=...
# SUPABASE_SERVICE_KEY=...

# Run Server
uvicorn main:app --reload
```

### 3. Frontend Setup
```bash
cd glassresumatch-ai
npm install
npm run dev
```
Access the UI at `http://localhost:3000`.

### 4. Database Migration (Supabase)
Run the following SQL in your Supabase SQL Editor to initialize the `tailored_resumes` table:

```sql
CREATE TABLE IF NOT EXISTS tailored_resumes (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES job_evaluations(job_id),
    version INTEGER,
    content JSONB,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure other tables exist (jobs, resumes, job_evaluations)
```

## 📝 Usage

1.  **Upload Master Resume**: Upload your main PDF resume via the UI or push `base_resume.json` to DB.
2.  **Evaluate a Job**: Paste a Job URL or Description. The **Evaluator Agent** will analyze fit.
3.  **Tailor**: If the recommendation is "Tailor", click the **"Tailor Resume"** button.
4.  **Review**: Use the **Diff View** overlay to see changes.
5.  **Approve & Download**: Once satisfied, approve the version and download the tailored PDF.

## 🤝 Contributing
1.  Fork the repo.
2.  Create your feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

## 📄 License
MIT License.
