---
name: planner
description: >
  Manages persistent planning docs that keep Claude Code on track across long sessions and context
  resets. Use whenever the user wants to plan a feature, checkpoint progress, resume a session,
  record an architecture decision, or scaffold a CLAUDE.md anchor. Trigger on: "plan this",
  "let's plan", "checkpoint", "where were we", "resume", "what's left", "record this decision",
  "add ADR", "set up CLAUDE.md". Also trigger proactively before a large implementation begins
  or after a major section completes.
---

# Planner

Five modes. Detect from user intent, then load the matching reference file.

| Intent | Mode | Reference |
|---|---|---|
| "plan X", "new feature", start of implementation | **plan** | `references/plan.md` |
| "checkpoint", "mark done", finishing a section | **checkpoint** | `references/checkpoint.md` |
| "resume", "where were we", "what's left" | **resume** | `references/resume.md` |
| "record decision", "add ADR", "why did we..." | **adr** | `references/adr.md` |
| "set up CLAUDE.md", "init", "project anchor" | **init** | `references/init.md` |

Load only the reference file for the active mode. Do not load others.

## File Layout
```
repo/
├── CLAUDE.md
└── docs/
    ├── active/<slug>.md
    └── decisions/<NNN>-<slug>.md
```

## Guardrails
- Progress log entries are append-only — never delete them
- Never overwrite CLAUDE.md without showing a diff first
- Checklist tasks = one sitting of focused work (not too coarse, not too fine)
- Decisions Made is for settled things only — debates go in Open Questions
