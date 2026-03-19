# Mode: adr

Creates `docs/decisions/<NNN>-<slug>.md`.

1. List `docs/decisions/` to find next number (current max is 0012, so next is 0013)
2. Write the file using TailorAI's ADR format:

```markdown
# ADR-<NNN> — <Title>

**Date**: YYYY-MM-DD
**Status**: Accepted

## Context
<!-- What situation or problem prompted this decision? -->

## Decision
<!-- What we decided in one clear sentence. -->

## Reasoning
<!-- Why this is the right call. -->

## Alternatives Considered
- **<Alternative>**: Rejected because <reason>

## Consequences
**Positive**:
-

**Negative / Trade-offs**:
-

## Do Not Revisit Unless
<!-- Under what conditions would this be worth reconsidering? -->
```

3. Add a one-liner to `CLAUDE.md` under `## Architecture decisions`:
   `ADR-0001 through ADR-<NNN> cover all major architectural shifts.`
