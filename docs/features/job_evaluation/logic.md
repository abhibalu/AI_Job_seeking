# Level 1 (Logic): Job Evaluation

[Go Up to README](../../README.md)

## The Mental Model
Job Evaluation acts as the **Harsh Gatekeeper** of the tailoring pipeline. Instead of wasting computational resources (and the user's focus) on every job, the system performs a high-speed "sanity check" to determine if a job is worth pursuing. 

The mental model is: **Strategic Alignment**. The system doesn't just look for keyword matches; it acts as a cynical recruiter, weighing the candidate's actual years of experience and core skills against the job's "Must-Haves" to determine the probability of success.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | A Job Description (JD) and the Candidate's Master Resume are available in the system context. |
| **Process** | The "Evaluator" cross-references experience years, tech stack, and soft skills, calculating a weighted score based on proximity to the JD requirements. |
| **Post-Condition** | The system produces a definitive "Verdict" (Strong/Moderate/Weak Match) and a "Recommended Action" (Apply/Tailor/Skip), effectively branching the workflow. |

## Workflow Chain
1. **Context Loading**: The Candidate's professional history (Master Resume) and Approved Skills are injected into the evaluator's working memory.
2. **Cynical Screening**: The evaluator compares the JD's requirements (e.g., "5+ years experienced") against the candidate's reality, applying penalties for significant gaps.
3. **Gap Analysis**: Beyond a simple score, the system identifies explicit "Strategic Gaps" (Technical, Domain, Soft Skills) that will later inform the tailoring strategist.
4. **Workflow Routing**: The evaluation result acts as a traffic controller, either stopping the process (Skip), proceeding immediately (Apply), or triggering a rewrite (Tailor).

## Drill Down
- [Level 2 (Architecture): Evaluation Contracts and Orchestration Logic](./architecture.md)
- [Level 3 (Implementation): JobEvaluatorAgent and Prompt Logic](./implementation.md)
