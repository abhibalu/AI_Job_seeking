# TailorAI Documentation Map

Welcome to the TailorAI technical documentation. We use a **Layered Documentation System** to separate Functional Logic from Architecture and Implementation.

---

## 🚀 Active Features

### Google Doc Base Resume Ingestion
Transitioning from static JSON storage to live Google Docs as the single source of truth.
- [Level 1: Logic & Mental Model](features/gdoc_base_resume/logic.md)
- [Level 2: Architecture & Contracts](features/gdoc_base_resume/architecture.md)
- [Level 3: Implementation Detail](features/gdoc_base_resume/implementation.md)

### LinkedIn Job Scraping
External cloud-based extraction of job data into the internal Lakehouse.
- [Level 1: Logic & Mental Model](features/linkedin_scraping/logic.md)
- [Level 2: Architecture & Contracts](features/linkedin_scraping/architecture.md)
- [Level 3: Implementation Detail](features/linkedin_scraping/implementation.md)

### Job Evaluation
The gatekeeper of the pipeline, providing match scores, strategic gaps, and routing decisions.
- [Level 1: Logic & Mental Model](features/job_evaluation/logic.md)
- [Level 2: Architecture & Contracts](features/job_evaluation/architecture.md)
- [Level 3: Implementation Detail](features/job_evaluation/implementation.md)

### Actor-Critic Tailoring Loop
The core iteration engine that drafts and refines the resume for maximum quality.
- [Level 1: Logic & Mental Model](features/tailoring_loop/logic.md)
- [Level 2: Architecture & Contracts](features/tailoring_loop/architecture.md)
- [Level 3: Implementation Detail](features/tailoring_loop/implementation.md)

---

## 🏛️ Core Architecture
- [System Overview](core/architecture.md)
- [API & Database Reference](core/api_and_db.md)

## 💡 Proposals & RFCs
- [JSON vs. Markdown Transition](proposals/json_vs_markdown.md)
- [GDoc Transition Plan](proposals/base_resume_arch.md)

## 📋 Backlog
- [Improvements & Tech Debt](backlog/improvements.md)
