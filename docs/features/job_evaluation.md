# Feature: job_evaluation

> Load me when: task touches JobEvaluatorAgent, evaluation scoring, recommended_action routing,
> wit_line, gaps, improvement_suggestions, or the evaluation DB schema.

## 1. Logic (The Mental Model)

Job Evaluation acts as the **Harsh Gatekeeper** of the tailoring pipeline. Instead of wasting computational resources (and the user's focus) on every job, the system performs a high-speed "sanity check" to determine if a job is worth pursuing. 

The mental model is: **Strategic Alignment**. The system doesn't just look for keyword matches; it acts as a cynical recruiter, weighing the candidate's actual years of experience and core skills against the job's "Must-Haves" to determine the probability of success.

### System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | A Job Description (JD) and the Candidate's Master Resume are available in the system context. |
| **Process** | The "Evaluator" cross-references experience years, tech stack, and soft skills, calculating a weighted score based on proximity to the JD requirements. |
| **Post-Condition** | The system produces a definitive "Verdict" (Strong/Moderate/Weak Match) and a "Recommended Action" (Apply/Tailor/Skip), effectively branching the workflow. |

### Workflow Chain
1. **Context Loading**: The Candidate's professional history (Master Resume) and Approved Skills are injected into the evaluator's working memory.
2. **Cynical Screening**: The evaluator compares the JD's requirements (e.g., "5+ years experienced") against the candidate's reality, applying penalties for significant gaps.
3. **Gap Analysis**: Beyond a simple score, the system identifies explicit "Strategic Gaps" (Technical, Domain, Soft Skills) that will later inform the tailoring strategist.
4. **Workflow Routing**: The evaluation result acts as a traffic controller, either stopping the process (Skip), proceeding immediately (Apply), or triggering a rewrite (Tailor).


## 2. Architecture & Contracts

### Component Boundaries
The evaluation system is encapsulated within a dedicated "Actor" pattern, allowing the core matching logic to remain isolated from the data persistence and orchestration layers.

1.  **The Evaluator Agent (Core Actor)**
    - *Responsibility:* Interpreting the semantic relationship between a resume and a JD.
    - *Boundary:* Consumes a `Resume` (JSON) and `Job Details` (String). Produces a structured `Evaluation Schema`.

2.  **The Pipeline Orchestrator (State Machine)**
    - *Responsibility:* Triggering the evaluation and branching the system state based on the result.
    - *Boundary:* Invokes the Evaluator and routes based on the `recommended_action` field.

3.  **The Persistent Store (Database)**
    - *Responsibility:* Storing the rich evaluation results (gaps, tips, scores) for retrieval by the Frontend and downstream agents.
    - *Boundary:* Interfaced via a `save_evaluation` contract.

### Data Contracts

#### 1. The Evaluation Schema (Output Contract)
The Evaluator produces a strictly typed JSON object containing:
- **Match Metrics:** `job_match_score` (10-100), `Verdict` (Strong/Moderate/Weak).
- **Control Flags:** `recommended_action` (apply/tailor/skip).
- **Semantic Feedback:** `gaps` (Technical/Domain/Soft), `improvement_suggestions` (Resume edits).
- **Interview Intelligence:** `interview_tips` (Topics/Prep/Strengths).

#### 2. Orchestration State
The internal state machine tracks the evaluation progress:
```json
{
  "status": "evaluated",
  "evaluation": { ... },
  "errors": []
}
```

### System State Transition
- **Before:** The system has a specific `job_id` and a `description_text`. The candidate's background is loaded into memory as a static Master Resume.
- **After:** The system state is updated with a rich evaluation payload, and the `recommended_action` is utilized to determine either immediate termination (Skip) or further refinement (Parse/Tailor).

## 3. Implementation Details

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
This worker handles the batch execution of evaluations.

Checks `is_service_enabled("openrouter")` at startup — if the OpenRouter service is disabled in Settings, the worker logs a warning and returns immediately without processing any jobs (ADR-0019).

> [!NOTE]
> **Production Status:** **Active**. Used for processing jobs in the background outside of immediate user-facing request/response cycles.

### System State Transition
- **Before:** The system invokes `agent.run()` with the raw Job and Resume data.
- **After:** The system receives a validated JSON payload. `agents/database.py::save_evaluation()` is called to persist the results to the Supabase `job_evaluations` table.
