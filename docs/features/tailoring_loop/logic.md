# Level 1 (Logic): Actor-Critic Tailoring Loop

[Go Up to README](../../README.md)

## The Mental Model
Generating a tailored resume is not a one-shot process. It requires a balance between **Strategic Promotion** (adding keywords and emphasizing relevant experience) and **Authenticity** (sticking to the candidate's actual background). 

The mental model is: **The Editorial Desk**. 
1. The **Actor** (The Editor) drafts the changes, trying to be helpful and ATS-optimized. 
2. The **Critic** (The Senior Hiring Manager) reviews that draft with a cynical eye, checking for hallucinations or over-exaggeration. 
They loop until the Critic is satisfied or a maximum revision limit is reached, ensuring the final output is high-quality and reliable.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | JD signals (keywords, gaps) and the Master Resume are loaded into the system state. |
| **Process** | An iterative Actor-Critic loop where drafts are produced and then critiqued for quality and accuracy. |
| **Post-Condition** | A finalized, "clean" tailored resume JSON is persisted to the database and ready for export. |

## Workflow Chain
1. **Initial Drafting**: The "Conservative Editor" (Actor) makes a first pass, attempting to integrate JD signals while preserving ~60% of the original content.
2. **Strict Critique**: The "Hiring Manager" (Critic) compares the draft against the source of truth (the Master Resume and Approved Skills).
3. **Iterative Revision**: If the Critic finds flaws (hallucinations, missing keywords), the Actor is sent back to fix them, receiving the explicit critique as part of the new prompt context.
4. **Final Stabilization**: Once approved (or after the safety revision limit), the resume is stripped of internal metadata and saved.

## Drill Down
- [Level 2 (Architecture): Sub-Graph Nodes and Control Flow](./architecture.md)
- [Level 3 (Implementation): LangGraph Integration and Agent Prompting](./implementation.md)
