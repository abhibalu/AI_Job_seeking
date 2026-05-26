# ADR-0021: Re-evaluation is Read-Only (No Tailoring)

## Status
Accepted

## Context

ADR-0020 designed `reeval_worker.py` as a full 7-stage pipeline: after evaluating a job, it would
also run JD parsing, change planning, drafting, critiquing, and saving — silently re-tailoring the
resume without any user confirmation.

This violated the UX principle that tailoring (a destructive overwrite of the tailored CV) should
require deliberate user consent. A re-evaluation that automatically re-tailors in the background
would also prevent the user from seeing the new verdict before deciding what to do.

## Decision

**Re-evaluation stops after JD parsing (stage 2).** The worker never enters the tailoring subgraph.

### New stage map

| # | Stage | Path |
|---|-------|------|
| 0 | evaluating | all |
| 1 | routing (sets total + evaluation_snapshot) | all |
| 2 | parsing | tailor only — provides ATS keywords for fresh verdict context |

Skip/apply: total=2. Tailor: total=3 (was 7).

### Frontend consequence

After re-eval completes, the verdict block shows a CTA strip:
- **"Re-tailor →"** — triggers `onTailorStart(jobId, { force: true })`, bypasses the "already ready"
  guard and starts a fresh tailoring run.
- **"Later"** — dismisses the CTA (`reEvalCtaDismissed = true`), keeps the `reEvalFresh` badge and
  force-tailor behavior via verdict block click.

State lifecycle:
1. Re-eval starts → `isReEvaling = true` → overlay shows stage progression
2. Re-eval completes → `reEvalDone = true` (2s) → "Assessment updated ✓"
3. After pulse → `reEvalFresh = true`, `reEvalCtaDismissed = false` → inline CTA strip appears
4. User clicks "Re-tailor →" → fresh tailoring run starts
5. User clicks "Later" → `reEvalCtaDismissed = true` → CTA hidden, "Retouch?" badge remains

### TailoringStrip reeval mode removed

`TailoringStrip` no longer has a `reeval` mode or `REEVAL_STAGES`. The floating strip only appears
during tailoring runs. Re-evaluation progress is handled entirely by the verdict block overlay.

The App.tsx "reeval TailoringStrip fallback" (shown when user navigated away during a tailor-path
reeval) is also removed — since reeval never runs tailoring, there is nothing to fall back to.

## Alternatives considered

**Keep full pipeline**: Re-evaluation automatically re-tailors. Rejected — overwrites the user's
tailored CV without consent and hides the new verdict behind a tailoring run the user didn't request.

**Separate "re-eval + re-tailor" button**: Two distinct buttons. Rejected — adds surface area. The
CTA strip achieves the same result with one click from the verdict block.

## Consequences

- Re-evaluation is always fast (3 stages max vs up to 7)
- User sees the new verdict immediately and decides whether to re-tailor
- `reeval_worker.py` no longer imports tailoring subgraph nodes
- `TailoringStrip` props simplified: `mode` prop removed
- `App.tsx` simplified: `reEvalPath` state removed, reeval TailoringStrip fallback removed
- `handleTailorStart` accepts `opts?: { force?: boolean }` to bypass "already ready" guard
