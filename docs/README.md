# TailorAI Documentation Map

Welcome to the TailorAI technical documentation. We use a **Layered Documentation System** to separate Functional Logic from Architecture and Implementation.

---

## 🚀 Active Features

### Google Doc Base Resume Ingestion
Transitioning from static JSON storage to live Google Docs as the single source of truth.
- [Feature Documentation](features/gdoc_base_resume.md)

### LinkedIn Job Scraping
External cloud-based extraction of job data into the internal Lakehouse.
- [Feature Documentation](features/linkedin_scraping.md)

### Job Evaluation
The gatekeeper of the pipeline, providing match scores, strategic gaps, and routing decisions.
- [Feature Documentation](features/job_evaluation.md)

### Actor-Critic Tailoring Loop
The core iteration engine that drafts and refines the resume for maximum quality.
- [Feature Documentation](features/tailoring_loop.md)

---

## 🏛️ Core Architecture
- [System Overview](core/architecture.md)
- [API & Database Reference](core/api_and_db.md)

## 💡 Proposals & RFCs
- [JSON vs. Markdown Transition](proposals/json_vs_markdown.md)
- [GDoc Transition Plan](proposals/base_resume_arch.md)

## 📋 Backlog
- [Improvements & Tech Debt](backlog/improvements.md)
