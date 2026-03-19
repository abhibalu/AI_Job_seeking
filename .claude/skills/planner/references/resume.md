# Mode: resume

Reconstructs session context from the plan doc.

1. Read `CLAUDE.md`
2. Read `docs/active/<slug>.md` (ask if ambiguous which plan)
3. Output:

```
## Resume: <Feature Name>

**Where we are:** <one sentence>

**Done:** <ticked items>
**Up next:** <first unticked items>
**Watch out for:** <blockers / open questions from log>
**Decisions in force:** <key decisions>
```

4. Ask: "Ready to continue?"
