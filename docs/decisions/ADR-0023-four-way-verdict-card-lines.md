# ADR-0023: 4-way verdict with pre-computed card lines

**Status:** Accepted (2026-06-11)

## Context

The OotoCV redesign (`references/ootocv_src 2/`) requires four verdicts —
TAILOR / BORDERLINE / APPLY_DIRECT / SKIP — each rendering a structurally
different Job Detail layout and a single one-line card summary in the feed:

| Verdict      | Card line          | Detail page emphasis            |
|--------------|--------------------|---------------------------------|
| TAILOR       | `top_strength`     | Your Brief → JD → Tailoring CTA |
| BORDERLINE   | `deciding_factor`  | Deciding Factor (prominent)     |
| APPLY_DIRECT | (none — direct CTA)| JD condensed → Apply CTA        |
| SKIP         | `kill_shot`        | Kill Shot (red) → JD muted      |

The current schema has a 3-value `recommended_action` (`apply | tailor | skip`)
and no card-summary columns. Synthesizing the one-liner from `gaps[]` +
`summary` on the frontend is unreliable and wastes payload.

## Decision

Extend `job_evaluations.recommended_action` to four values
(`tailor | borderline | apply_direct | skip`) while retaining `'apply'` in the
CHECK constraint so historical rows stay valid. Add four pre-computed columns:
`top_strength`, `deciding_factor`, `kill_shot`, `red_flags`. The evaluator
populates exactly one of `{top_strength, deciding_factor, kill_shot}` matching
the chosen verdict, plus `red_flags` whenever risks are present.

`red_flags` is a JSONB string array where each entry uses the format
`"Label — explanation"`. The em-dash separator is load-bearing — the
frontend splits on ` — `. The evaluator writer normalizes plain hyphens and
en-dashes to em-dash on read (R6).

## Consequences

- Evaluator prompt change (`agent_prompts/evaluator.md`).
- Historical 3-value rows keep their legacy enum. Re-evaluation is on-demand
  via the existing reeval worker — no mass re-eval cost runaway.
- Card render is one column read on the feed query; no array unpacking in the
  client.
- BORDERLINE can coexist with high `match_score` (culture / red-flag-driven
  borderlines), unlike a derived-from-score approach.

## Alternatives rejected

- **Derive BORDERLINE from `match_score` band (55–70 → borderline)** — loses
  the agent's narrative deciding factor; cannot express "high score but
  borderline because of culture".
- **Client-side line synthesis from `gaps[]`** — wastes payload and forces
  the frontend to make editorial choices the agent should be making.
- **Drop legacy `'apply'` from the CHECK** — would invalidate all historical
  rows; backfill is expensive and pointless.

## See also

- ADR-0010 (per-change records, the related approve-flow data model)
- Migration `022_evaluations_verdict_extension.sql`
- `docs/superpowers/plans/2026-06-11-ootocv-schema-adaptation.md`
