# Mode: plan

Creates `docs/active/<slug>.md` — a living checklist for a feature sprint.

1. Derive a kebab-case slug (≤5 words) from the feature name
2. Infer what you can from context; ask only for what's missing
3. Write the file:

```markdown
# Plan: <Feature Name>

**Status:** 🟡 In Progress
**Created:** <YYYY-MM-DD>
**Branch:** <branch if known>

## Goal
<!-- One paragraph. What does done look like? -->

## Decisions Made
- <Decision>: <Reason>

## Open Questions
- [ ] <Unresolved thing>

## Out of Scope
- <Explicit non-goal>

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [ ] <Task — enough detail for a fresh Claude to understand>

### Frontend (glassresumatch-ai/)
- [ ] <Task>

### Agent Prompts (agent_prompts/)
- [ ] <Task>

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
```

4. Tell the user: "Start each session with: `Read CLAUDE.md and docs/active/<slug>.md`"
