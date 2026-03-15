# Architecture Decision Records (ADRs)

This directory captures significant architecture and design decisions made during the evolution of TailorAI.

## Why ADRs?

Git commits capture *what* changed, but not *why*. ADRs preserve the reasoning behind decisions — what alternatives were considered, what data drove the choice, and what trade-offs were accepted — so future developers and coding agents can understand past decisions without re-analyzing from scratch.

## Format

Each ADR is a numbered markdown file: `NNNN-short-title.md`

```markdown
# ADR-NNNN: Title

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded | Deprecated

## Problem

What issue was identified and why it matters.

## Analysis

Key findings from investigation. What data drove the decision.

## Decision

What we chose to do and why.

## Consequences

What changed (files, deps, architecture). Any trade-offs accepted.
```

## Adding a new ADR

1. Pick the next available number
2. Create `NNNN-short-title.md` using the template above
3. Add a link to the Decision Log section in `CLAUDE.md`
