# Feature: tailoring_loop

> Load me when: task touches the tailoring subgraph, ChangePlannerAgent, ResumeTailorAgent,
> ResumeCriticAgent, resume_validator.py, or the Plan-then-Execute loop logic.

## 1. Logic (The Mental Model)

Generating a tailored resume is not a one-shot process. It requires a balance between **Strategic Promotion** (adding keywords and emphasizing relevant experience) and **Authenticity** (sticking to the candidate's actual background).

The mental model is: **The Surgical Team**.
1. The **Planner** (The Surgeon) analyzes the patient (resume vs JD gaps) and writes a precise surgical plan — what to change, where, and why.
2. The **Editor** (The Surgical Resident) executes the plan, making only the specified changes while leaving everything else untouched.
3. The **Validator** (The Instrument Nurse) counts the sponges — programmatically verifies structural integrity and plan compliance.
4. The **Critic** (The Attending Physician) reviews the result for quality — does it look natural? Does it read authentically?

They loop until the Critic is satisfied or a maximum revision limit is reached.

### System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | JD signals (keywords, gaps, improvement suggestions) and the Master Resume are loaded into the system state. |
| **Planning** | The Planner analyzes gaps, cross-references with approved skills, and produces a structured edit plan with specific locations and actions. |
| **Execution** | The Editor applies the plan to the base resume, modifying only planned locations. |
| **Validation** | Structural integrity is verified programmatically. Plan compliance is checked (only planned locations modified). |
| **Review** | The Critic checks for naturalness, authenticity, and AI patterns — structural checks are already handled. |
| **Post-Condition** | A finalized tailored resume JSON is persisted alongside its edit plan (audit trail) to the database. |

### Workflow Chain
1. **Edit Planning**: The Planner distills JD gaps and improvement suggestions into a surgical list of edits with exact locations, target text, and approved-skills references.
2. **Precision Editing**: The Editor applies the edit plan, copying everything else verbatim. No creative decisions — just plan execution.
3. **Structural Validation**: Pure Python checks verify bullet counts, ID preservation, section integrity, change ratio, and plan compliance.
4. **Content Review**: The Critic evaluates naturalness, voice consistency, and catches AI writing patterns.
5. **Iterative Revision**: If issues found, the Editor is sent back with specific feedback. Max 2 revision cycles.
6. **Final Stabilization**: Approved drafts save as `pending`; force-saved drafts save as `needs_review` with edit plan attached.


## 2. Architecture & Contracts

### Component Boundaries
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

### Subgraph Flow

```
START → plan → draft → validate ─┬→ critique ─┬→ save → END
                  ↑               │             │
                  └── revise ─────┘             │
                  ↑                             │
                  └──────── revise ─────────────┘
```

### Data Contracts

#### 1. The Tailoring State (`TailoringState`)
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

#### 2. The Edit Plan Contract
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

#### 3. The Critique Contract
The Critic returns a JSON array of strings focused on content quality:
```json
["Bullet 4 in Metro role uses 'Orchestrated' — same verb as bullet 2. Use 'Built' instead.", "Summary sounds generic. Keep original tone."]
```

### System State Transition
- **Before:** The system holds `base_resume`, `jd_context`, and `approved_skills`. No edit plan or draft exists.
- **After:** The `draft_resume` has been planned, executed, validated, and reviewed. Both the resume and its `edit_plan` are saved to the `resumes` table.

## 3. Implementation Details

### 1. The Orchestrator (`agents/tailoring_subgraph.py`)
The sub-graph utilizes **LangGraph** to manage a 5-node state machine: `plan → draft → validate → critique → save`.

**Key Implementation Details:**
- **Plan node:** Invokes `ChangePlannerAgent` once at the start. The edit plan is reused across revision cycles — the planner does NOT re-run on revisions.
- **State Partitioning:** The `node_save` filters keys starting with `_` and stores the `edit_plan` alongside the resume for audit trail.
- **Safety Cap:** `route_critique` enforces `MAX_REVISIONS = 2`. At max revisions, force-saves with `status='needs_review'`.
- **Validation short-circuit:** If `node_validate` finds structural violations, it routes directly back to `draft` (skipping the critic LLM call).

### 2. The Planner (`agents/change_planner.py`)
The `ChangePlannerAgent` (temperature 0.2) produces a structured edit plan from the system prompt in `agent_prompts/change_planner.md`.

**Key Implementation Details:**
- **Input:** Full `jd_context` (gaps, improvement_suggestions, ats_keywords) + `base_resume` + `approved_skills`
- **Output:** JSON with `edits[]`, `preserve[]`, and `summary`
- **Constraint:** Every edit must reference an approved skill or existing resume content

### 3. The Editor (`agents/resume_tailor.py`)
The `ResumeTailorAgent` (temperature 0.3) implements a "Precision Editor" strategy through `agent_prompts/resume_tailor.md`.

**Key Implementation Details:**
- **Prompt receives `edit_plan`** instead of `jd_context` — the plan already distilled the context
- **Critique injection:** Previous critique is appended under `### CRITIQUE TO ADDRESS (URGENT)` for revision passes
- **Legacy path:** `run_tailoring()` method internally creates a `ChangePlannerAgent` and chains plan → execute for backward compatibility

### 4. The Validator (`agents/resume_validator.py`)
Pure Python structural checks — no LLM call.

**Two validation functions:**
- `validate_structure()`: Bullet counts, ID preservation, section integrity, change ratio (max 55%)
- `validate_planned_edits()`: Verifies only locations in `edit_plan.edits` were actually modified. Compares base vs draft highlights and summary, flagging unplanned changes.

### 5. The Critic (`agents/resume_critic.py`)
The `ResumeCriticAgent` (temperature 0.2) reviews content quality only — structural checks are handled by the validator.

**Key Implementation Details:**
- **Receives `base_resume` and `edit_plan`** for comparison context
- **Focused scope:** Naturalness, authenticity, AI patterns, hallucination check
- **Does NOT check:** Bullet counts, ID preservation, section structure, change ratio

### 6. Change Tracking (`agents/database.py`)
The `save_tailored_resume()` function accepts an optional `edit_plan` parameter and stores it in the `resumes.edit_plan` JSONB column (migration 007).

**Audit trail:** Every tailored resume has a companion record of exactly what was changed and why, queryable via Supabase.

### System State Transition
- **Before:** `build_tailoring_subgraph().compile()` creates the 5-node graph.
- **After:** `node_save` executes `save_tailored_resume()` with both the resume content and edit plan, returning the `record_id` (UUID) to the parent graph.
