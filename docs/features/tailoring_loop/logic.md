# Level 1 (Logic): Plan-then-Execute Tailoring Loop

[Go Up to README](../../README.md)

## The Mental Model
Generating a tailored resume is not a one-shot process. It requires a balance between **Strategic Promotion** (adding keywords and emphasizing relevant experience) and **Authenticity** (sticking to the candidate's actual background).

The mental model is: **The Surgical Team**.
1. The **Planner** (The Surgeon) analyzes the patient (resume vs JD gaps) and writes a precise surgical plan — what to change, where, and why.
2. The **Editor** (The Surgical Resident) executes the plan, making only the specified changes while leaving everything else untouched.
3. The **Validator** (The Instrument Nurse) counts the sponges — programmatically verifies structural integrity and plan compliance.
4. The **Critic** (The Attending Physician) reviews the result for quality — does it look natural? Does it read authentically?

They loop until the Critic is satisfied or a maximum revision limit is reached.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | JD signals (keywords, gaps, improvement suggestions) and the Master Resume are loaded into the system state. |
| **Planning** | The Planner analyzes gaps, cross-references with approved skills, and produces a structured edit plan with specific locations and actions. |
| **Execution** | The Editor applies the plan to the base resume, modifying only planned locations. |
| **Validation** | Structural integrity is verified programmatically. Plan compliance is checked (only planned locations modified). |
| **Review** | The Critic checks for naturalness, authenticity, and AI patterns — structural checks are already handled. |
| **Post-Condition** | A finalized tailored resume JSON is persisted alongside its edit plan (audit trail) to the database. |

## Workflow Chain
1. **Edit Planning**: The Planner distills JD gaps and improvement suggestions into a surgical list of edits with exact locations, target text, and approved-skills references.
2. **Precision Editing**: The Editor applies the edit plan, copying everything else verbatim. No creative decisions — just plan execution.
3. **Structural Validation**: Pure Python checks verify bullet counts, ID preservation, section integrity, change ratio, and plan compliance.
4. **Content Review**: The Critic evaluates naturalness, voice consistency, and catches AI writing patterns.
5. **Iterative Revision**: If issues found, the Editor is sent back with specific feedback. Max 2 revision cycles.
6. **Final Stabilization**: Approved drafts save as `pending`; force-saved drafts save as `needs_review` with edit plan attached.

## Drill Down
- [Level 2 (Architecture): Sub-Graph Nodes and Control Flow](./architecture.md)
- [Level 3 (Implementation): LangGraph Integration and Agent Prompting](./implementation.md)
