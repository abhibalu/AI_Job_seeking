# agent_prompts/CLAUDE.md

Load me when: task creates or edits any file in `agent_prompts/`.

---

## File naming

Class `FooBarAgent` → file `agent_prompts/foo_bar.md`.

Current files:
- `job_evaluator.md` → `JobEvaluatorAgent`
- `jd_parser.md` → `JDParserAgent`
- `change_planner.md` → `ChangePlannerAgent`
- `resume_tailor.md` → `ResumeTailorAgent`
- `resume_critic.md` → `ResumeCriticAgent`
- `approved_skills.md` → skill truthfulness reference (not an agent prompt)

## Prompt structure

```
# Role
[single sentence — what this agent is and what it does]

# Instructions
[ordered list of what the agent must do]

# Input format
[describe kwargs passed via build_user_prompt()]

# Output format
[JSON schema with exact field names and types]

# Rules / DO NOT
[explicit prohibitions — especially for extraction fidelity]
```

## Output format requirement

Every agent prompt **must** specify a JSON-only response with exact field definitions.
The agent must return nothing but a JSON object — no prose, no markdown wrapper.

## One-shot examples

Embed one-shot examples in `build_user_prompt()`, **not** in the system prompt.
- System prompt: role + instructions (static, lean, loaded every call)
- User prompt: input data + one-shot example (dynamic, per-call)

Rationale: system prompt bloat inflates cost on every call with static content. One-shot in
user prompt gives the model fidelity guidance exactly when it has the real input to compare against.
See ADR-0006.

## DO NOT rules

Include explicit `DO NOT` rules when extraction fidelity matters. Examples:
- `DO NOT summarise, paraphrase, or truncate content`
- `DO NOT invent skills or experience not present in the source`
- `DO NOT add keywords not explicitly mentioned in the job description`

## Temperature table (mirror agents/CLAUDE.md)

| Agent              | Temperature |
|--------------------|-------------|
| ResumeParserAgent  | 0.1         |
| JDParserAgent      | 0.2         |
| ChangePlannerAgent | 0.2         |
| ResumeCriticAgent  | 0.2         |
| JobEvaluatorAgent  | 0.3         |
| ResumeTailorAgent  | 0.3         |

Set in the agent `__init__`, not in the prompt file itself.

## approved_skills.md

Source of truth for skill truthfulness. `ChangePlannerAgent` references it when planning edits —
it constrains what skills can be added to the resume. Do not remove entries without understanding
downstream impact on tailoring quality.

---

## Go deeper

- One-shot pattern rationale → `docs/decisions/ADR-0006`
- Temperature decisions → `docs/decisions/ADR-0004`
- BaseAgent contract (how prompts are loaded) → `agents/CLAUDE.md`
