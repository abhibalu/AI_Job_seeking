# Level 2 (Architecture): Job Evaluation

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries
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

## Data Contracts

### 1. The Evaluation Schema (Output Contract)
The Evaluator produces a strictly typed JSON object containing:
- **Match Metrics:** `job_match_score` (10-100), `Verdict` (Strong/Moderate/Weak).
- **Control Flags:** `recommended_action` (apply/tailor/skip).
- **Semantic Feedback:** `gaps` (Technical/Domain/Soft), `improvement_suggestions` (Resume edits).
- **Interview Intelligence:** `interview_tips` (Topics/Prep/Strengths).

### 2. Orchestration State
The internal state machine tracks the evaluation progress:
```json
{
  "status": "evaluated",
  "evaluation": { ... },
  "errors": []
}
```

## System State Transition
- **Before:** The system has a specific `job_id` and a `description_text`. The candidate's background is loaded into memory as a static Master Resume.
- **After:** The system state is updated with a rich evaluation payload, and the `recommended_action` is utilized to determine either immediate termination (Skip) or further refinement (Parse/Tailor).

## Drill Down
- [Level 3 (Implementation): JobEvaluatorAgent and Prompt Logic](./implementation.md)
