# TailorAI: Autonomous Job Seeking Agent

TailorAI is a full-stack AI agent designed to revolutionize the job application process. It acts as a tireless personal recruiter, autonomously discovering, analyzing, and tailoring your resume for the perfect job fit.

## 🏗️ Core Architecture
TailorAI is built on a modern, event-driven **Data Lakehouse** pattern tailored for AI workloads.

### 1. 🧬 Data Architecture (Medallion Pattern)
The system implements a robust **Medallion Architecture** (`lakehouse/`) to manage data quality:
*   **Bronze Layer** (`bronze.py`): Ingests raw job descriptions and resume PDFs. Handles unstructured data capture from Apify and file uploads.
*   **Silver Layer** (`silver.py`): Performs enrichment and schema validation. Normalizes varying job formats into a unified `Job` entity.
*   **Gold Layer** (`gold.py`): The analytical "One Big Table" (OBT). Aggregates clean data and syncs it to the application database (Supabase) to power the frontend and agent context.

### 2. 🤖 Agentic Core (`/agents`)
The intelligence layer is composed of specialized AI agents:
*   **Job Evaluator**: Analyzes JDs against user constraints to score relevance (0-100) and perform **Gap Analysis** (identifying missing skills/keywords).
*   **Resume Tailor**: A "Compliance Editor" agent that rewrites specific resume sections (Summary, Experience) to strictly align with target keywords without hallucinating facts.
*   **JD Parser**: Extracts structured signals (Must-haves, Tech Stack, Seniority) from unstructured job descriptions to standardize evaluation.

### 3. 🔌 Core Services
*   **Scraper Service** (`services/scraper_service.py`): Integrating **Apify** to reliably fetch real-time job listings from **LinkedIn**, bypassing advanced bot detection.
*   **API Backend** (`/api`): Built with **FastAPI**, serving RESTful endpoints for the React frontend (`GET /jobs`, `POST /resumes/tailor`).

### 4. 🔭 Observability
Native integration with **Langfuse** provides complete traceability of Agent reasoning:
*   **Trace Tracing**: Every decision (Score: 85/100) is backed by a trace showing *why* the AI made that choice.
*   **Cost Management**: Token usage tracking per-model (Openrouter Models) to optimize operational costs.

## 💻 Tech Stack
*   **Frontend**: React, TypeScript, TailwindCSS (Glassmorphism UI).
*   **Backend**: Python, FastAPI, Supabase (PostgreSQL).
*   **LLM Orchestration**: OpenRouter (Any Openrouter Models), Langfuse.
*   **Infrastructure**: Docker, Apify Cloud.

## 🚀 Key Features
*   **AI Resume Tailoring**: Context-aware rewriting of Summary and Experience sections to align with specific JD keywords (`agents/resume_tailor.py`).
*   **Advanced Search**: Full-text search and filtering over job descriptions.
*   **Dynamic Layout Engine**: Parametric resume styling (Margins, Spacing) via CSS variables.
*   **Resume Normalization**: Robust parsing of complex PDF layouts to JSON Resume standard.
*   **Automated Gap Analysis**: Visual diff of what your resume is missing vs. what the job description requires.

---
*Built with ❤️ by Abhijith Sivadas* and Agentic Coding Expert
