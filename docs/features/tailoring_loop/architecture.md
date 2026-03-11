# Level 2 (Architecture): Actor-Critic Tailoring Loop

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries
The tailoring process is encapsulated in a dedicated **Sub-Graph** (`tailoring_subgraph.py`) to manage its internal recursion and state isolation.

1.  **The Actor (ResumeTailorAgent)**
    - *Responsibility:* Semantic editing and ATS optimization.
    - *Boundary:* Consumes the `base_resume` and `jd_context`. Produces a draft JSON object.

2.  **The Critic (ResumeCriticAgent)**
    - *Responsibility:* Quality assurance and hallucination detection.
    - *Boundary:* Consumes the `draft_resume` vs. the `approved_skills` truth. Produces an array of `critique` strings.

3.  **The Router (Logic Engine)**
    - *Responsibility:* Control flow (Save vs. Retry).
    - *Boundary:* Inspects the `critique` count and the `revision_count` to decide the next graph state.

## Data Contracts

### 1. The Tailoring State (`TailoringState`)
The LangGraph state carries the working draft across nodes:
```python
class TailoringState(TypedDict):
    job_id: str
    base_resume: dict         # The source of truth
    jd_context: dict          # Extracted keywords and gaps
    approved_skills: str      # The boundary of what the LLM is allowed to claim
    draft_resume: dict        # The current working mutation
    critique: list[str]       # Array of flaws identified by the Critic
    revision_count: int       # Iteration tracker
    final_resume_id: str      # output ID
```

### 2. The Critique Contract
The Critic communicates via a structured JSON array of strings:
```json
["The resume mentions leadership of 10 people, but the base resume says 3.", "Missing the 'Kubernetes' keyword identified in JD Parser."]
```

## System State Transition
- **Before:** The system state contains the `base_resume` and pre-calculated `jd_context`. No tailored draft exists yet.
- **After:** The `draft_resume` has been approved (or stabilized), saved to the `tailored_resumes` table, and the `final_resume_id` is updated in the state for the parent graph to acknowledge.

## Drill Down
- [Level 3 (Implementation): LangGraph Integration and Agent Prompting](./implementation.md)
