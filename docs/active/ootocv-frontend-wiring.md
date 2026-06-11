# Plan: OotoCV Frontend Rebuild

**Status:** 🟡 Code complete; awaiting browser smoke
**Created:** 2026-06-11
**Branch:** `feature/ootocv-frontend-wiring`
**Reference:** `references/ootocv_src 2/`
**ADR:** `docs/decisions/ADR-0026-ootocv-shell-supersedes-linear.md` (supersedes ADR-0007)

## Goal

Replace the live frontend shell with the OotoCV reference design verbatim,
wiring each page to the existing backend (the Phase 2–5 schema/API
adaptation is already deployed). Make the live app match
`references/OotoCV.zip` exactly while preserving the working tailoring
SSE flow, GDoc export, service kill switches, AutoSendModal, and cover
letter autosave.

## Decisions Made

- **Wholesale page replacement.** The OotoCV reference's single-column
  fat-card feed + dedicated `/job/:id` route conflicts structurally
  with ADR-0007's two-pane Linear layout. ADR-0026 documents the
  supersession.
- **`services/jobAdapter.ts` collapses the backend split** (`Job` +
  `Evaluation` + `ParseResult`) into the reference's flat `ReferenceJob`
  shape with `role`, `verdict` (uppercase 4-way), `verdictReason`,
  `redFlags[]`, `strengths[]` (typed), `gaps[]` (with severity +
  strategy), `matchScore` 0–4. The Phase-6 card-line fields
  (`top_strength` / `deciding_factor` / `kill_shot`) are not consumed
  by the reference; the adapter composes equivalent one-liners
  locally.
- **Per-change accept/reject UI is removed** for now in favor of the
  reference's "Request Changes" textarea + global Approve. The
  backend `resume_changes` rows are still written/read so the UI can
  be reintroduced as a power-user view later.
- **Pipeline mode pills + run-grouped feed are not part of this port.**
  Built backend stays available; can be layered onto the reference
  shell when needed.
- **Service kill switches (ADR-0019) folded into Settings** as a
  dedicated "External Services" section. Stays distinct from the
  pipeline modes conceptually.
- **5-step Onboarding** replaces the previous 2-step. Returning
  users with `onboarding_complete=true` skip.
- **GDoc export wired into "Approve & Send"** so the reference's
  copy ("Pushing to Google Drive…") is functionally true.

## What landed

| File | Change |
|---|---|
| `services/apiClient.ts` | Phase-6 types + 7 new methods (kept from earlier in this session) |
| `services/jobAdapter.ts` | new — backend → reference shape |
| `App.tsx` | reference routes; new TailoringStrip flow |
| `components/Sidebar.tsx` | reference verbatim, wired to `getSystemStatus` |
| `components/TypewriterWaitState.tsx` | reference port (three-leak-fix retained) |
| `components/JobCard.tsx` | new — reference fat 2-column card |
| `components/MatchBrief.tsx` | reference port; consumes `ReferenceStrength` / `ReferenceGap` |
| `components/TailoringStrip.tsx` | reference visual + preserved `useSSE` / `cancelTask` |
| `pages/Dashboard.tsx` | reference single-column feed, wired to real backend |
| `pages/JobDetail.tsx` | reference verdict-conditional layout, real data |
| `pages/TailoringReview.tsx` | reference 2-pane + cover letter autosave + GDoc export |
| `pages/ApplicationTracker.tsx` | reference cards + Interview / Ghosting expansion |
| `pages/Onboarding.tsx` | new — reference 5-step wizard |
| `pages/Settings.tsx` | new — reference + folded service kill switches + resume indicator |
| `pages/ResumeRoast.tsx` | new — reference 3-state, wired to `roastResume` |
| `index.css` | DM Sans / DM Mono font import added; `semantic-amber` token aligned |
| `docs/decisions/ADR-0026` | new — supersedes ADR-0007 |
| `pages/SetupPage.tsx` | **deleted** (replaced by Onboarding + Settings) |
| `components/ApplicationTracker.tsx` | **deleted** (duplicate of pages/ version) |
| `hooks/useJobs.ts`, `useJobSelection.ts`, `useResumeState.ts` | **deleted** (dense-sidebar plumbing no longer used) |

## Open items

- **Browser smoke.** TypeScript clean (`tsc --noEmit` 0 errors) but the
  app hasn't been opened in a browser yet. Once the dev server is up,
  spot-check: Dashboard load + section split, JobCard verdict styling,
  JobDetail per-verdict order, TailoringReview SSE during a real
  tailoring run, ApplicationTracker `ghost_commentary` rendering,
  Settings toggle round-trips, ResumeRoast end-to-end.
- **Onboarding API-key inputs are display-only.** The reference shows
  text fields; we treat them as informational because the live app's
  keys live in `.env`. If we want client-side key storage later,
  thread `inputValue` through a new endpoint.
- **Gmail OAuth in Onboarding is a placeholder.** The real OAuth lives
  outside the SPA today; the wizard advances without performing it.
- **The reference uses `mockJobs` for App badge counts.** We replace
  this with the Dashboard reporting its actionable count up via the
  `onActionableCountChange` prop.
- **`top_strength` / `deciding_factor` / `kill_shot` not wired into
  the reference card layout.** They remain in the API client and the
  evaluator continues to emit them; if we want to surface them as
  a hover/title affordance on the JobCard, that's a follow-up.
- **Pipeline mode pills + run grouping** can be reintroduced under
  the reference shell when needed (e.g., as a header above the feed
  or a Settings subsection).

## How to verify

1. `cd glassresumatch-ai && npm run dev` (default port 3000).
2. Hit `http://localhost:3000/`; expect:
   - Reference sidebar with rotating "Hunting while you sleep…" copy
   - Single-column fat-card feed
   - Cards grouped by Primary / Borderline / collapsed Skip
3. Click a card → `/job/:id` opens with the reference detail layout.
4. Click "Tailor & Approve" → home page shows the bottom TailoringStrip
   running through real SSE stages; cancel works.
5. Once tailoring completes, `/tailoring/:resumeId` shows the 2-pane
   review.
6. `/tracker` lists prior applications with server `ghost_commentary`.
7. `/settings` toggles round-trip via PATCH; `/roast` shows the 3-state
   page; `/onboarding` (with `ootocv_configured=false` in localStorage)
   shows the 5-step wizard.

(Test plan scoped to UI smoke per global feedback memory — no automated
frontend tests in this batch; backend regression covered by Phase 2–5.)
