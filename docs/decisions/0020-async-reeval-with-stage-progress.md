# ADR-0020: Async Re-evaluation with Stage-by-Stage Progress

## Status
Accepted

## Context

Re-evaluation ran the full LangGraph pipeline synchronously via `POST /api/evaluations/{job_id}`.
For tailor-path jobs (~175s), the user stared at a spinning icon with zero progress indication.
A job can also change paths between runs (apply → tailor), which was disorienting without feedback.

## Decision

**Approach A — Wrapper Worker**: New background worker (`services/reeval_worker.py`) that manually
steps through pipeline node functions, emitting `save_task_status()` at each boundary. This reuses
the same SSE infrastructure from ADR-0009 and ADR-0014 (tailoring background task).

### New endpoint
`POST /api/evaluations/{job_id}/async` — creates a background task, returns `{ task_id, job_id }`.
The existing sync endpoint (`POST /api/evaluations/{job_id}`) is preserved for the batch worker.

### Stage map
| # | Stage | Path |
|---|-------|------|
| 0 | evaluating | all |
| 1 | routing (sets total + evaluation_snapshot) | all |
| 2 | parsing | tailor |
| 3 | planning | tailor |
| 4 | drafting | tailor |
| 5 | critiquing | tailor |
| 6 | saving | tailor |

Skip/apply: total=2. Tailor: total=7.

### Extended SSE progress payload
`evaluation_snapshot` (recommended_action, job_match_score, wit_line, verdict) included from
stage 1 onward. `path` included from stage 1 onward. Frontend uses these for verdict block
crossfade without waiting for full completion.

### Frontend state machine (verdict block)
1. **idle** → normal
2. **evaluating** → verdict block content at opacity-40, overlay "Evaluating fit…"; all sections below + footer at opacity-30 with pointer-events-none
3. **verdict-revealed** → snapshot crossfades into badge/dots/wit_line
4. **tailoring** → inline 5-dot progress track below verdict
5. **complete** → tailor path shows "CV tailored ✓" for 2s, then data refetch
6. **failed** → error toast, state clears

### TailoringStrip fallback
When user navigates away during tailor-path re-eval, a floating TailoringStrip with
`mode="reeval"` shows the progress. Hidden when viewing the re-eval job (verdict block handles it).

### Concurrency guards
- Re-eval blocked while another re-eval is running
- Re-eval blocked while tailoring the same job
- Tailor-start blocked while re-eval is running for the same job

## Alternatives considered

**Approach B — LangGraph interrupt/stream**: Use LangGraph's native streaming to emit events.
Rejected because the existing SSE infrastructure (task table + polling endpoint) is proven and
the wrapper worker gives explicit control over progress granularity.

## Consequences
- Re-evaluation is no longer blocking — user sees real-time progress
- Path changes between runs are visible (verdict crossfade shows new badge immediately)
- Existing sync endpoint preserved for batch worker compatibility
- `SSEProgressEvent` type extended with `stage`, `path`, `evaluation_snapshot`, `resume_id`
