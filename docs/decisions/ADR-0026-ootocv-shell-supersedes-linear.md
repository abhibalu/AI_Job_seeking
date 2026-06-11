# ADR-0026: Adopt OotoCV reference shell (supersedes ADR-0007)

**Status:** Accepted (2026-06-11)
**Supersedes:** ADR-0007 (Linear-style two-pane layout)

## Context

ADR-0007 settled the frontend on a Linear-style two-pane layout: a 320px
job-list sidebar pane on the left, a JobDetail pane on the right, with
infinite scroll + tabs + verdict filter pills as the primary navigation
affordance. Over Phases 1–5 we layered more features into that shell
(MatchBrief collapsibles, TailoringStrip with SSE, AutoSendModal,
service kill switches, application tracker).

The OotoCV reference design (`references/ootocv_src 2/`) reframes the
product as an **agentic monitor**. Its visual language is fundamentally
different:

- Single-column fat-card feed (`max-w-3xl`), not a dense sidebar
- Sections by verdict (Primary → Borderline → collapsed Skip), no filter pills
- JobDetail is its own route (`/job/:id`) with a verdict-conditional
  layout, not a right pane
- Sidebar uses rotating cron messages (5s interval) instead of a single
  state line
- Dedicated `/roast` page for the resume critique utility
- 5-step Onboarding wizard (Intro → OpenRouter → Apify → Gmail → Resume)
- Application tracker has Interview / Ghosting expansion rows with
  specific copy and follow-up template flows

When the OotoCV schema work (Phase 2–5, ADRs 0023/0024/0025) was
merged, the live frontend was still wearing the Linear shell. Bolting
the new fields onto the old layout produced a hybrid that satisfied
neither design. The user reviewed the result and asked for the
reference design verbatim.

## Decision

Replace the entire frontend shell with the OotoCV reference layout,
file-by-file, while wiring every page to the live backend rather than
the reference's mock data.

Concrete swaps:

| Page / component        | Source                                                       |
|-------------------------|--------------------------------------------------------------|
| `App.tsx` routes        | Reference route table (`/`, `/job/:id`, `/tailoring/:id`,    |
|                         | `/roast`, `/tracker`, `/settings`, `/onboarding`)            |
| `Dashboard`             | Reference single-column feed; reads `getJobs` + `getRuns`    |
|                         | through `services/jobAdapter.toReferenceJob`                 |
| `JobDetail`             | Reference verdict-conditional layout; reads `getJob` +       |
|                         | `getEvaluation`; standalone `/job/:id` route                 |
| `TailoringReview`       | Reference 2-pane diff + Request Changes / Approve flow;      |
|                         | preserved cover letter editing + GDoc export                 |
| `ApplicationTracker`    | Reference card list + Interview / Ghosting expansion         |
| `Onboarding`            | Reference 5-step wizard; resume upload wired to              |
|                         | `apiClient.uploadResume`                                     |
| `Settings`              | Reference layout + folded service kill switches (ADR-0019)   |
|                         | + current resume indicator                                   |
| `ResumeRoast`           | Reference 3-state (upload → roasting → results);             |
|                         | wired to `apiClient.roastResume`                             |
| `Sidebar`               | Reference with wordmark + rotating cron messages;            |
|                         | wired to `apiClient.getSystemStatus`                         |
| `TailoringStrip`        | Reference bottom strip visual + preserved `useSSE` /         |
|                         | `cancelTask` wiring                                          |
| `JobCard`, `MatchBrief`,| Reference verbatim, typed against `ReferenceJob` from the    |
| `TypewriterWaitState`   | adapter                                                      |

A new module `services/jobAdapter.ts` collapses the backend's split
(`Job` + `Evaluation` + `ParseResult`) into the flat `ReferenceJob`
shape the reference components consume — `role`, `verdict` (uppercase
4-way), `verdictReason`, `redFlags[]`, `strengths[]` (with `req met` /
`evidence` / `signal` types), `gaps[]` (with `severity` + `strategy`),
and `matchScore` 0–4. The reference's `top_strength` / `deciding_factor`
/ `kill_shot` are not used directly — the adapter composes equivalent
one-liners from existing backend fields plus the OotoCV-added columns.

Files deleted as superseded: `pages/SetupPage.tsx`,
`components/ApplicationTracker.tsx` (duplicate), `hooks/useJobs.ts`,
`hooks/useJobSelection.ts`, `hooks/useResumeState.ts`.

Files preserved across the swap: `components/Toast.tsx`, `hooks/useSSE.ts`,
`services/apiClient.ts` (extended in Phase-6 work), `services/jobService.ts`
(provides `fetchJobsWithEvaluations` that the new Dashboard reuses).

## Consequences

- **Information density drops.** The dense 320px sidebar held more jobs
  per viewport. The reference's fat cards trade density for clarity.
  Mitigated by the verdict sectioning: TAILOR/APPLY DIRECT at the top,
  BORDERLINE below, SKIP collapsed.
- **Per-change accept/reject UI is no longer surfaced.** The reference's
  TailoringReview uses a single global "Request Changes" textarea
  instead. The backend `resume_changes` rows are still written and read
  (so a future per-change UI can be reintroduced as a power-user view),
  but the default flow is coarse-grained: approve everything or
  request a rewrite.
- **Pipeline mode pills + run-grouped feed are not part of the
  reference layout.** They were prototyped on the old shell but
  superseded by this ADR. The backend endpoints (`/api/pipeline/config`,
  `/api/runs`) remain — they can be reintroduced under the reference
  shell when needed.
- **Cover letter editing preserved.** Reference shows a static block;
  we kept the autosave-on-blur textarea (ADR-0011).
- **GDoc export preserved.** The reference's "Approve & Send" copy
  implies "pushing to Google Drive" — we call `exportToGoogleDocs` and
  surface the structured `ExportResult` status in the success line.
- **5-step Onboarding replaces the previous 2-step upload flow.**
  Returning users with `onboarding_complete=true` skip the wizard.
- **`useJobs` infinite scroll + actioned partitioning is gone.** The
  reference uses a flat per-session fetch. Tracker holds historical
  applications; the feed shows the current day's run.

## Alternatives rejected

- **Hybrid — keep two-pane mechanics, adopt reference visuals.** Loses
  the discoverability the reference design gains from the single-
  column flow; users still scan a sidebar list rather than seeing each
  verdict reason in full.
- **Keep ADR-0007 layout, upgrade typography only.** Doesn't honor the
  design intent. The reference is structurally different, not just
  styled differently.
- **Build into `references/ootocv_src 2/` as a separate app.** Throws
  away the live app's SSE, kill-switch, GDoc-export, AutoSendModal
  wiring, all of which we want to keep.

## See also

- ADR-0007 (superseded — Linear-style layout)
- ADR-0023 (4-way verdict + card lines)
- ADR-0025 (run as first-class entity)
- ADR-0010 (per-change review records — backend kept, UI not surfaced)
- ADR-0011 (cover letter editable from day one — preserved)
- ADR-0019 (service kill switches — preserved in Settings)
- `references/ootocv_src 2/` (reference design source)
