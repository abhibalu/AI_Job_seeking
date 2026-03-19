# agents/CLAUDE.md

Load me when: task touches `agents/`, `pipeline_graph.py`, `tailoring_subgraph.py`,
`supabase_db/` migrations, or the DB schema layer.

---

## BaseAgent contract (`agents/base.py`)

```python
class FooAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(model, temperature=0.X)   # set explicit temperature — never rely on default 0.7

    def get_system_prompt(self) -> str: ...         # required abstract
    def build_user_prompt(self, **kwargs) -> str: ...  # required abstract
    # run(**kwargs) -> dict  is provided by BaseAgent; do not override unless essential
```

- Instantiate fresh in each graph node — never reuse an agent across calls.
- `run()` calls `get_system_prompt()`, `build_user_prompt()`, `_call_llm()`, `_parse_json_response()`.
- Result dict gets `_model_used` and `_agent` metadata keys injected automatically.

## Langfuse tracing

- Env vars (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) **must be set before**
  `from langfuse.decorators import observe` — done in `agents/base.py` top-of-file.
- `@observe(as_type="generation")` on `_call_llm()`, `@observe()` on `run()`.
- `extra_body={"usage": {"include": True}}` in every SDK call — **required for OpenRouter cost
  tracking**. Missing this silently drops cost data from Langfuse.

## Temperature table (exact values)

| Agent              | Temperature |
|--------------------|-------------|
| ResumeParserAgent  | 0.1         |
| JDParserAgent      | 0.2         |
| ChangePlannerAgent | 0.2         |
| ResumeCriticAgent  | 0.2         |
| JobEvaluatorAgent  | 0.3         |
| ResumeTailorAgent  | 0.3         |

Rule: extraction/parsing agents use 0.1. Analytical agents use 0.2. Creative/drafting agents use 0.3.

## Adding a new agent

1. Create `agents/my_agent.py` — extend `BaseAgent`, implement `get_system_prompt` + `build_user_prompt`.
2. Create `agent_prompts/my_agent.md` — see `agent_prompts/CLAUDE.md` for prompt structure.
3. Instantiate fresh inside the graph node function (not at module level).
4. Add the node to the appropriate graph (`pipeline_graph.py` or `tailoring_subgraph.py`).

## LangGraph node pattern

```python
def node_x(state: MyState) -> dict:
    logger.info(f"[Graph] <action> for job {state['job_id']}")
    agent = MyAgent()
    try:
        result = agent.run(...)
        return {"my_field": result, "status": "done"}
    except Exception as e:
        logger.error(f"[Graph] <action> failed: {e}")
        return {"errors": [f"<action> failed: {str(e)}"], "status": "error"}
```

- Always return **partial dicts** — LangGraph merges them into state.
- Routing functions check `state.get("errors")` first before inspecting other fields.
- Logging prefix: `[Graph]` in `pipeline_graph.py`, `[SubGraph]` in `tailoring_subgraph.py`.

## State schema rules

- Use `TypedDict`.
- Every state must have `status: str` and `errors: list[str]`.
- Routing functions pattern: `if state.get("errors"): return "error"`.

## Pipeline graph flow

```
START → evaluate (JobEvaluatorAgent)
        ├→ skip: END
        ├→ apply: notify_apply → END
        └→ tailor: parse (JDParserAgent) → tailor (subgraph) → notify_tailored → END
```

`route_after_evaluation` reads `state["evaluation"]["recommended_action"]`.

## Tailoring subgraph flow

```
START → plan (ChangePlannerAgent)
        → draft (ResumeTailorAgent)
        → validate (Python, no LLM)
        ├→ structural violations + revisions left: back to draft
        └→ critique (ResumeCriticAgent)
           ├→ no issues: save → END
           ├→ issues + revisions left: back to draft
           └→ MAX_REVISIONS (2) reached: force save → END
```

## Resume status semantics

Two orthogonal status fields on the `resumes` table:

**`status`** — user review decision:
- `master` = base resume row (not a tailored version)
- `pending` = critic-approved (zero flaws). Safe to present to user.
- `needs_review` = force-saved at max revisions (unresolved flaws). **Do not save as `pending`.**
  These become indistinguishable from approved resumes and human review is impossible.
- `approved` / `rejected` = user has acted on the tailored resume.

**`tailoring_status`** — OotoCV pipeline state (ADR-0010):
- `not_started` → `processing` → `ready` (or `cancelled` / `needs_review`)
- Set automatically by `save_tailored_resume()` based on the `status` value at save time.
- Drives button copy and card verdict in the OotoCV feed UI.

## resume_changes table (ADR-0010)

Normalised per-change records written by `_save_resume_changes()` inside `save_tailored_resume()`.
Each row = one planned edit from `edit_plan.edits[]`.

Key fields: `original_text` (immutable pre-AI text from `current_text`), `tailored_text` (AI output from `target_text`), `accepted_text` (set by user action), `review_action` (`accept | reject | keep_original`).

`keep_original` sets `accepted_text = original_text` immediately — no regeneration loop.

Helper functions: `get_resume_changes(resume_id)`, `apply_change_action(change_id, action)`, `apply_bulk_change_action(resume_id, action, scope)`.

## applications table (OotoCV phase 5)

Application tracker. Each row = one job the user applied to.

Key fields: `job_id`, `job_title` + `company_name` (denormalized for display), `cv_version` (`base | tailored`),
`status` (`applied | replied | interview | rejected | ghosting`), `status_history JSONB` (append-only
`[{status, timestamp}]` log). See ADR-0013 for why JSONB was chosen over a separate events table.

No backend agent writes to this table — rows are created by the API when the user clicks Apply.
`PATCH /api/applications/:id/status` reads history, appends new entry, writes back (single-user,
no concurrency concern).

## system_config table

Key-value store for user-level settings. Keys: `cron_time` (HH:MM), `cron_tz` (IANA, e.g. `Europe/Dublin`), `auto_send_threshold` (integer 0–4).
Functions: `get_system_config(key)`, `set_system_config(key, value)`.

## DB migration idempotency rule

Any INSERT that copies rows by primary key **must** include `ON CONFLICT (id) DO NOTHING`.
Without it, re-running a partially-applied migration causes a duplicate key error that blocks all further runs. See agent-lessons #8.

## DB cleanup before persist

Strip backend metadata before saving resume JSON:
```python
clean_resume = {k: v for k, v in final_resume.items() if not k.startswith('_')}
```

## Field name wiring (critical)

JDParser outputs `ats_keywords`. ChangePlanner/ResumeTailor consume `ats_keywords`.
**Never rename or alias** without updating all downstream consumers end-to-end.

## Checkpointer

`SupabaseSaver` in `agents/supabase_checkpointer.py`. Config dict shape:
```python
{"configurable": {"thread_id": "...", "checkpoint_ns": "...", "checkpoint_id": "..."}}
```
Subgraph uses the parent graph's checkpointer — no nested checkpointing.

## agent_prompts naming convention

Class `FooBarAgent` → file `agent_prompts/foo_bar.md`.

## Environment variables for agents
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_MODEL_BACKUP` — LLM routing
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` — tracing
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — DB (required)

---

## Go deeper

- Full architecture map (dependency rules, data flow) → `docs/core/architecture.md`
- Tailoring quality decisions → `docs/decisions/ADR-0004`, `ADR-0006`
- Plan-then-Execute architecture → `docs/decisions/ADR-0005`
- Full graph inline comments → `agents/pipeline_graph.py`, `agents/tailoring_subgraph.py`
- Eval filter latency (DB view) → `docs/decisions/ADR-0003`
