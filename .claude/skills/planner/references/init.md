# Mode: init

Creates or updates `CLAUDE.md` — auto-loaded by Claude Code every session.

**CRITICAL for TailorAI**: CLAUDE.md has custom sections (Commands, Ports, Context map)
that must NEVER be overwritten by a generic template. Show a diff before changing anything
outside these two sections:
- `## Active tasks` — list new docs/active/ files
- `## Architecture decisions` — update ADR count

For all other sections, read first and only suggest changes if something is clearly wrong.

If creating from scratch (new project), use this template:

```markdown
# <ProjectName> — Claude Code Anchor

> Read automatically every session. Keep it current.

## Stack
<!-- One line per layer: what + why -->

## Design System
<!-- Fonts, colours, component rules, key constraints -->

## Critical Rules
<!-- Decisions that must never be reversed. Be blunt. -->
- <Rule>: <Why>

## Known Landmines
<!-- Things that look good but were tried and killed -->
- <Thing>: <Why we killed it>

## Active Feature Work
→ See docs/active/

## Architecture Decisions
→ See docs/decisions/
```
