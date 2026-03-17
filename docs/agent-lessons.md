# Agent Lessons Log

When Claude makes a mistake seen before:
1. Add an entry here.
2. Update the relevant domain CLAUDE.md.
**This log must not be the only home** — entries without a "propagated to" are incomplete.

---

## 1. Temperature for extraction agents
**Source**: ADR-0006 (2025)

**Mistake**: `ResumeParserAgent` inherited `BaseAgent` default `temperature=0.7`. Parsing was
treated as a creative task — output summarised and truncated content instead of extracting verbatim.

**Correct pattern**: Any agent doing extraction or parsing must set `temperature=0.1` explicitly
in `__init__`. Never rely on the `BaseAgent` default of `0.7` for non-creative tasks.

```python
def __init__(self, model=None):
    super().__init__(model=model, temperature=0.1)  # extraction — verbatim fidelity
```

**Propagated to**: `agents/CLAUDE.md` (temperature table), `agent_prompts/CLAUDE.md` (temperature table)

---

## 2. ATS keyword field name mismatch
**Source**: ADR-0004 (2025)

**Mistake**: `api/routes/resumes.py` and `pipeline_graph.py` passed `keywords_to_include` to
`ResumeTailorAgent`. `JDParserAgent` outputs `ats_keywords`. The tailor received an empty keyword
list silently — no error, wrong output.

**Correct pattern**: When wiring one agent's output as input to the next, verify field names
end-to-end. Do not assume a name matches intent — check the actual output schema of the upstream agent.

```python
# Correct wiring in node_tailor():
"ats_keywords": parsed_jd.get("ats_keywords", []),   # matches JDParser output field
```

**Propagated to**: `agents/CLAUDE.md` (field name wiring section)

---

## 3. One-shot examples in user prompt, not system prompt
**Source**: ADR-0006 (2025)

**Mistake**: One-shot examples placed in the system prompt bloated every LLM call with static
content that only provides value when paired with real input data.

**Correct pattern**: Embed one-shot examples in `build_user_prompt()`. The system prompt stays
lean (role + instructions). The user prompt carries the example alongside the actual input,
giving the model a direct comparison target.

```python
def build_user_prompt(self, **kwargs) -> str:
    return f"""
    Example input: ...
    Example output: ...

    Now process this:
    {kwargs['actual_input']}
    """
```

**Propagated to**: `agent_prompts/CLAUDE.md` (one-shot examples section), `agents/CLAUDE.md`

---

## 4. Force-saved resume status must differ from critic-approved
**Source**: ADR-0004 (2025)

**Mistake**: Resumes hitting the max revision limit (2) were saved with `status="pending"`,
identical to critic-approved resumes. Human review was impossible — no way to distinguish
clean approvals from force-saves with unresolved flaws.

**Correct pattern**: Check for unresolved critique before saving. Use `needs_review` for
force-saves, `pending` only for zero-flaw critic approval.

```python
is_force_save = bool(state.get("critique", []))
save_status = "needs_review" if is_force_save else "pending"
```

**Propagated to**: `agents/CLAUDE.md` (resume status semantics section)
