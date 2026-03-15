# Level 3 (Implementation): Plan-then-Execute Tailoring Loop

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

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

## System State Transition
- **Before:** `build_tailoring_subgraph().compile()` creates the 5-node graph.
- **After:** `node_save` executes `save_tailored_resume()` with both the resume content and edit plan, returning the `record_id` (UUID) to the parent graph.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
