# Level 2 (Architecture): Plan-then-Execute Tailoring Loop

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries
The tailoring process is encapsulated in a dedicated **Sub-Graph** (`tailoring_subgraph.py`) with five nodes managing planning, execution, validation, review, and persistence.

1.  **The Planner (ChangePlannerAgent)**
    - *Responsibility:* Analyze JD gaps and produce a structured edit plan.
    - *Boundary:* Consumes `base_resume`, `jd_context`, `approved_skills`. Produces `edit_plan` dict.
    - *Temperature:* 0.2 (deterministic planning).

2.  **The Editor (ResumeTailorAgent)**
    - *Responsibility:* Apply the edit plan to the base resume.
    - *Boundary:* Consumes `base_resume`, `edit_plan`, `approved_skills`. Produces `draft_resume` JSON. Does NOT see `jd_context` — the plan already distilled it.
    - *Temperature:* 0.3 (conservative editing).

3.  **The Validator (Pure Python)**
    - *Responsibility:* Structural integrity and plan compliance.
    - *Boundary:* Consumes `base_resume`, `draft_resume`, `edit_plan`. Produces violation strings.
    - *No LLM call* — pure deterministic checks.

4.  **The Critic (ResumeCriticAgent)**
    - *Responsibility:* Content quality review (naturalness, authenticity, AI patterns).
    - *Boundary:* Consumes `draft_resume`, `base_resume`, `edit_plan`, `approved_skills`. Produces critique strings.
    - *Temperature:* 0.2 (strict reviewing).

5.  **The Router (Logic Engine)**
    - *Responsibility:* Control flow (Save vs. Retry vs. Error).
    - *Boundary:* Inspects `critique` count and `revision_count` to decide next state.

## Subgraph Flow

```
START → plan → draft → validate ─┬→ critique ─┬→ save → END
                  ↑               │             │
                  └── revise ─────┘             │
                  ↑                             │
                  └──────── revise ─────────────┘
```

## Data Contracts

### 1. The Tailoring State (`TailoringState`)
```python
class TailoringState(TypedDict):
    job_id: str
    base_resume: dict         # The source of truth
    jd_context: dict          # Extracted keywords and gaps (consumed by planner only)
    approved_skills: str      # Boundary of what the LLM may claim
    edit_plan: dict           # Structured plan from ChangePlanner
    draft_resume: dict        # Current working draft
    critique: list[str]       # Feedback from Validator or Critic
    revision_count: int       # Iteration tracker (max 2)
    final_resume_id: str      # Supabase UUID of saved resume
    status: str               # Current pipeline stage
    errors: list[str]         # Error accumulator
```

### 2. The Edit Plan Contract
The Planner produces a structured JSON object:
```json
{
  "edits": [
    {
      "location": "work[0].highlights[4]",
      "action": "rephrase",
      "current_text": "Built Cloud Functions API...",
      "target_text": "Built serverless data ingestion pipelines...",
      "reason": "JD requires AWS Lambda; Cloud Functions is closest equivalent",
      "approved_source": "Notable Projects: BNPL Launch"
    },
    {
      "location": "skills",
      "action": "add",
      "items": ["dbt", "Apache Airflow"],
      "reason": "ATS keywords present in approved skills but missing"
    }
  ],
  "preserve": ["work[0].highlights[0-3]", "education.*"],
  "summary": "3 bullet edits, 2 skill additions."
}
```

### 3. The Critique Contract
The Critic returns a JSON array of strings focused on content quality:
```json
["Bullet 4 in Metro role uses 'Orchestrated' — same verb as bullet 2. Use 'Built' instead.", "Summary sounds generic. Keep original tone."]
```

## System State Transition
- **Before:** The system holds `base_resume`, `jd_context`, and `approved_skills`. No edit plan or draft exists.
- **After:** The `draft_resume` has been planned, executed, validated, and reviewed. Both the resume and its `edit_plan` are saved to the `resumes` table.

## Drill Down
- [Level 3 (Implementation): LangGraph Integration and Agent Prompting](./implementation.md)
