# Level 3 (Implementation): Job Evaluation

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

### 1. The Core Agent (`agents/job_evaluator.py`)
The `JobEvaluatorAgent` inherits from `BaseAgent` and manages the synchronous LLM call for matching.

**Key Implementation Details:**
- **Resume Normalization:** The `_normalize_resume` method ensures that resumes from the Frontend (UI-centric layout) and standard JSON Resume formats are unified before being passed to the LLM.
- **Experience Logic:** The system prompt dynamically injects `settings.CANDIDATE_EXPERIENCE_YEARS` to force a strict years-of-experience comparison.
- **Prompt Engineering:** The `get_system_prompt` enforces a very specific JSON schema and a structured scoring algorithm (starting from 50, adding/subtracting 10).

> [!NOTE]
> **Production Status:** **Active**. This is the critical first stage of the LangGraph pipeline used in the production environment.

### 2. Orchestration Integration (`agents/pipeline_graph.py`)
The `node_evaluate` function wraps the agent call within the LangGraph orchestrator.

**Implementation Details:**
- **Error Handling:** If the LLM fails to return a valid JSON object, the graph state is updated with a `status: "error"`, which triggers an immediate termination (`END`) via conditional edges.
- **Routing:** The `route_after_evaluation` function implements the triple-branch logic (Skip/Apply/Tailor) by inspecting the `recommended_action` key in the LLM's response.

> [!NOTE]
> **Production Status:** **Active**. This node is the entry point for all asynchronous job processing tasks.

### 3. Async Background Worker (`services/eval_worker.py`)
(Planned/Legacy) This worker handles the batch execution of evaluations.

> [!NOTE]
> **Production Status:** **Active (Experimental)**. Used for processing jobs in the background outside of immediate user-facing request/response cycles.

## System State Transition
- **Before:** The system invokes `agent.run()` with the raw Job and Resume data.
- **After:** The system receives a validated JSON payload. `agents/database.py::save_evaluation()` is called to persist the results to the Supabase `job_evaluations` table.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
