# glassresumatch-ai/CLAUDE.md

Load me when: task touches frontend components, hooks, types, or apiClient.

---

## Directory layout

```
glassresumatch-ai/
  App.tsx             — shell: Sidebar + Routes + TailoringStrip
  index.tsx           — React entry point (BrowserRouter)
  index.css           — @tailwindcss import + @theme tokens + base styles
  types.ts            — ALL shared TypeScript types
  pages/              — full-page route components
    Dashboard.tsx     — feed pane (4 card formats: TailorCard, ApplyDirectCard, SkipCard + Borderline)
    JobDetail.tsx     — detail pane (verdict-conditional layout, typewriter, MatchBrief, CVDiff)
    TailoringReview.tsx — change-level review (Accept/Reject, cover letter, approve footer)
    ApplicationTracker.tsx — tracker cards with status chips and timeline dots
    SetupPage.tsx     — onboarding (isOnboarding=true) and settings (isOnboarding=false)
  components/         — shared/reusable components only
    Sidebar.tsx       — nav + logo + cron status indicator
    TailoringStrip.tsx — SSE-driven bottom strip during active tailoring (real stage progress + stop)
    TypewriterWaitState.tsx — animated wait state with sessionStorage skip
    MatchBrief.tsx    — strengths/gaps signal display in JobDetail
    Toast.tsx         — floating notification (error/success)
  hooks/              — custom React hooks (useJobs, useSSE, useResumeState, useJobSelection)
  lib/
    utils.ts          — cn() helper (clsx + tailwind-merge)
  services/
    apiClient.ts      — singleton API client
  utils/              — format helpers (formatTimeAgo, etc.)
```

## Component conventions

- Full-page routes go in `pages/`, shared pieces go in `components/`.
- One component per file, PascalCase filename.
- No `alert()` — use Toast component for user feedback.
- No shadows, blur, or gradients — spec §1.5.
- bg-accent buttons must use `text-[#0d0d0d]`, not `text-base`.
- Semantic colors: semantic-green, semantic-amber, semantic-red, semantic-slate (all -400 level).

## Shared types (`types.ts`)

All types live in `types.ts`. Add new types here — not inline in component files.
Key types already defined: `Job`, `JobDetail`, `JobStats`, `Evaluation`, `EvaluationStats`,
`ParseResult`, `TailoredResume`, `ResumeChange`, `TaskStatus`, `MessageResponse`.

`Job.tailoring_status` drives OotoCV button copy: `'not_started' | 'processing' | 'ready' | 'cancelled' | 'needs_review'`.
`Job.posted_at` is a UTC ISO-8601 string — always pass through `formatTimeAgo()` at render time, never pre-format server-side.

`ResumeChange` fields: `original_text` (immutable), `tailored_text` (AI output), `accepted_text` (user choice), `review_action`, `confidence` (sort ascending — lowest confidence first in review UI).

## apiClient.ts

Singleton `apiClient` instance exported as default and named export.
Base URL: `http://localhost:8000` (hardcoded — change via constructor if needed).

All API calls go through:
```ts
private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T>
```

- `Content-Type: application/json` is set automatically unless body is `FormData`.
- `FormData` body: do not set `Content-Type` manually — browser sets it with boundary.

## Reading response headers (pagination)

`apiClient.request<T>()` returns parsed JSON only — no access to headers.
For `X-Total-Count` (pagination total), use a manual `fetch()` call:
```ts
const response = await fetch(`${this.baseUrl}${url}`, { headers: {...} });
const total = parseInt(response.headers.get('X-Total-Count') || '0', 10);
```
See `getEvaluations()` in `apiClient.ts` for the pattern.

## Pagination params

Query params: `skip` (offset) and `limit`. Total count in `X-Total-Count` response header.

## Method naming in apiClient

Match resource names: `getJobs()`, `getJob(id)`, `evaluateJob(id)`, `tailorResume(id)`,
`deleteJobs(ids)`. Pattern: `getX()`, `postX()`, `deleteX()`.

OotoCV methods added: `getResumeChanges(resumeId)`, `applyChangeAction(resumeId, changeId, action)`,
`applyBulkChangeAction(resumeId, action, scope)`, `updateCoverLetter(resumeId, coverLetter)`,
`patchJobAction(jobId, cvVersion: 'base' | 'tailored')` — PATCH `/api/jobs/:id/action`, fire-and-forget
to record which CV version the user applied with (called from JobCard quick action).

`tailorResume(jobId)` — now returns `{ task_id: string; message: string }` (background task, not
the full tailored resume). Frontend tracks progress via SSE using the returned `task_id`.

`cancelTask(taskId)` — `POST /api/tasks/{taskId}/cancel`. Stops a running tailoring pipeline at
the next node boundary.

`getSchedulerStatus()` — `GET /api/scheduler`, returns `SchedulerStatus` with `scheduler_running: bool`,
`last_runs: Record<string, PipelineRun>`, `jobs: Array<{name, next_run_utc}>`. Used by Sidebar to poll
and display real cron/scraper status (active/sleeping/error).

## Sidebar brand & scheduler status (OotoCV phase 5 polish)

**Brand**: Sidebar logo text is "OotoCV" (not "TailorAI").

**Cron status**: Sidebar footer polls `getSchedulerStatus()` every 60s. Derives state from response:
- `scheduler_running || any run.status === 'running'` → `'active'` (green dot + pulse, message: "Running now…")
- `any run.status === 'failed'` → `'error'` (red dot, message: "Last run failed", hover → "View logs →" → navigate `/settings`)
- else → `'sleeping'` (amber dot, message: "Last run Xh ago", hover → next run time)

Uses `formatTimeAgo(last_run.finished_at)` to display "Last run" time. Gracefully degrades if backend unavailable.

## Dashboard feed: only evaluated jobs

`useJobs('all', filters)` passes `is_evaluated: true` to the jobs API. Unevaluated jobs are
excluded from the Dashboard feed — they have no verdict, score, or summary data, so rendering
them produces empty verdict blocks and misleading "borderline" grouping.

## Feed sort rule (OotoCV)

Within equal `matchScore`, APPLY DIRECT (`recommended_action === 'apply'`) sorts before TAILOR.
Implemented in `utils/sort.ts` smart sort tier. Less friction = more urgent.

## Dashboard card quick actions (OotoCV rebuild)

`Dashboard.tsx` renders four card formats. `TailorCard` and `ApplyDirectCard` both have hover-reveal
quick action buttons.

**TailorCard** (verdict: tailor or borderline) — two distinct props:
- `onTailorStart()` — primary button ("Tailor CV" / "Review & Send"). Wired
  to `handleTailorStart` in App.tsx, which checks `tailoring_status` first:
  - `'ready'` → `getTailoredVersions(jobId)` then `navigate('/tailoring/:id')` (existing review)
  - `'processing'` → toast "Already tailoring this job" (no duplicate run)
  - otherwise → `tailorResume(jobId)` returns `task_id` → sets `tailoringJob` + `tailoringTaskId` → TailoringStrip appears with SSE tracking
- `onSkip()` — ghost "Skip" button. Wired to `handleSkip` (marks actioned, no API call).
- `isTailoring?: boolean` — disables tailor button when another tailoring run is active.

Button label is conditional on `job.tailoring_status`:
- `'ready'` → `"Review & Send"` (don't re-run pipeline)
- otherwise → `"Tailor CV"` (for both tailor and borderline verdicts)

**Concurrency guard**: `handleTailorStart` checks `tailoringJob` state — only one tailoring run
at a time. Dashboard cards are disabled via `isTailoring` prop during active runs.

**Important**: `onTailorStart` and `onAction` (apply) are separate props — never conflate them.
Wiring "Tailor CV" to the apply handler silently applies the job without tailoring it.
See agent-lessons #16.

## useJobs actioned partitioning (OotoCV phase 2 + 4)

`useJobs.ts` tracks `actionedIds: Set<string>` and exposes:
- `markActioned(id)` — optimistic add; call when user clicks Apply in JobCard
- `unmarkActioned(id)` — rollback remove; call on API failure to revert optimistic update
- `activeJobs` — jobs not yet actioned; server-side filter pills apply to this partition
- `actionedJobs` — actioned jobs; render below filtered results, dimmed

The raw `jobs` array (all loaded) is also still returned for backwards compatibility.

Rollback pattern (Apply Direct):
```ts
markActioned(id);                    // optimistic
try { await patchJobAction(id, cv); }
catch { unmarkActioned(id); showToast({ onRetry: () => handleApply(id, cv) }); }
```

## SSE hook (`hooks/useSSE.ts`)

`useSSE(taskId: string | null, handlers)` — opens a single `EventSource` per `taskId`.

- Pass `null` to keep hook dormant (no connection opened).
- `handlers.onProgress(event)` — fired on `event: progress` SSE events.
- `handlers.onRunComplete(event)` — fired on `event: run_complete` (`completed` / `failed` / `cancelled`); hook closes the connection.
- `handlers.onError(err)` — fired on `es.onerror`; **do NOT close** — native auto-reconnect handles it.
- Handler refs are stable (`useRef`) — changing handlers never restarts the `EventSource`.
- `useEffect` depends only on `taskId`; cleans up (`es.close()`) on unmount or `taskId` change.

## TailoringStrip (SSE-driven progress + cancel)

`TailoringStrip.tsx` shows real pipeline progress via SSE and allows cancellation.

- Reads `progress.stage` from SSE `onProgress` events and maps to user-facing messages:
  `queued` → "Starting up…", `planning` → "Analyzing job requirements…",
  `drafting` → "Tailoring your CV…", `critiquing` → "Reviewing changes…",
  `revising` → "Refining edits…", `saving` → "Saving your tailored CV…"
- On `run_complete` with `status !== 'cancelled'`: extracts `progress.resume_id` and calls
  `onComplete(jobId, resumeId)` for direct navigation to review page.
- "Stop Tailoring" button calls `onCancel()` (which calls `apiClient.cancelTask(taskId)` in App.tsx).
  Shows "Stopping…" while cancel is in-flight.
- Animated green pulse dot indicates active processing.

## Toast rollback pattern

`Toast` accepts optional `onRetry?: () => void`. When set, renders an underlined "Retry" button
beside the dismiss `✕`. Use for any optimistic-update failure where the user should be able to
retry the action in-place.

## TailorReview (OotoCV phase 3)

Split layout: 420px left panel (change list + cover letter) + `flex-1` resume preview right.

`ChangeCard` sub-component renders one `ResumeChange` with:
- Accept / Reject / Keep original buttons (optimistic local state, syncs via `applyChangeAction`)
- Confidence % badge — sort changes ascending by confidence (lowest first — needs most attention)
- `action_type` badge, section location label, review-state badges

Bulk accept: calls `applyBulkChangeAction(resumeId, 'accept', 'remaining')` then refetches changes.

Cover letter `<textarea>` pre-filled from `tailoredResume.cover_letter`; saves on `onBlur` via
`updateCoverLetter`. No save button — blur is the save trigger.

Sticky footer: remaining unreviewed count + "Accept all remaining →" (disabled when 0).
Existing Approve/Reject/Download/Export header buttons are preserved above the split layout.

## TypewriterWaitState component

`TypewriterWaitState` animates through a messages array character-by-character.

- `sessionKey` prop → reads `sessionStorage.getItem(\`ootocv_tw_${sessionKey}\`)` on mount.
  If key exists, fires `onComplete` immediately (no animation on repeat visits in same session).
  Writes the key when the last message finishes animating.
- Use `sessionStorage` (not `localStorage`) — skip state is session-scoped by design.
- `onCompleteRef` is a stable ref internally — safe to pass inline arrow functions without extra deps.

## AutoSendModal component (ADR-0012)

Show `<AutoSendModal>` when `auto_send_threshold` slider is moved above 0. Slider alone is not
consent — modal forces deliberate confirmation before the value is saved.

Props: `threshold` (the new value 1–4), `onConfirm`, `onCancel`.
`onCancel` resets slider to 0. Clicking the backdrop also calls `onCancel`.

## Browser history / view mode sync

Use `pushState` / `popstate` for view mode navigation (job list ↔ job detail ↔ tailor review).
Avoids full page reloads. Implemented per ADR-0007.

## Sidebar badge (actionable count)

Sidebar Feed button shows a badge with count of jobs ready to action. **Source**: `stats.by_action['apply'] + stats.by_action['tailor']`
(NOT derived from paginated `activeJobs` list). This ensures the badge reflects all unactioned jobs,
not just loaded ones. See agent-lessons for this pattern.

## Job list tab navigation

The sidebar job list uses a 3-tab strip (Apply now / Tailor first / Skip) that sets
`filters.action`. Each tab triggers server-side filtering via `fetchEvaluations` in `useJobs` —
infinite scroll loads more jobs for the active tab only. Counts come from `stats.by_action`.
Default tab: `apply`. See ADR-0008.

`JobListPanel` props relevant to tabs:
- `showSectionHeaders` — pass `false` when a tab is active (avoids redundant section label)
- `activeAction` — scopes the recruiter contacts fetch to the current tab

## Don't derive stable UI state from paginated list state

UI elements showing complete/total data (counts, contact lists) must be fetched independently —
not derived from the `jobs` prop, which is partial until fully scrolled. Use a dedicated API
call scoped to the active filter. See agent-lessons #5.

## Infinite scroll: always reset totalJobs on filter change

When switching tabs/filters, reset `totalJobs` to `0` alongside `jobs` and `currentPage`.
`hasMore = jobs.length < totalJobs` — if `totalJobs` keeps the previous tab's value, `hasMore`
stays `true` throughout the switch and the `IntersectionObserver` effect (which depends on
`hasMore`) never re-runs. The sentinel mounts but is never observed. Infinite scroll silently
breaks on every tab except the first one loaded. See agent-lessons #6.

## Infinite scroll: use a ref for the observer callback, not the function itself

Don't put the `loadMore` function directly in the `IntersectionObserver` effect deps. `loadMore`
changes on every `loadingMore` flip, causing the observer to disconnect/reconnect mid-load. On
reconnect the sentinel may be below the viewport (new items just appended), leaving it unobserved
until the user scrolls — which they can't if they're already at the bottom.

Pattern:
```ts
const loadMoreRef = useRef(loadMore);
useEffect(() => { loadMoreRef.current = loadMore; }, [loadMore]);

useEffect(() => {
    if (!sentinelRef.current || !hasMore) return;
    const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) loadMoreRef.current(); },
        { root: feedRef.current, threshold: 0.1 }
    );
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
}, [hasMore]); // only re-creates when sentinel mounts/unmounts
```
See agent-lessons #7.

## Application tracker (OotoCV phase 5)

`ApplicationTracker.tsx` shows all recorded applications with timeline dots and inline status chips.

- Fetches `GET /api/applications` on mount (newest first).
- Each card: company initial, title, applied-at (via `formatTimeAgo`), `cv_version` badge,
  timeline dots (`applied · replied · interview · rejected`), status-advance chips.
- "View what you sent →" calls `onViewSent(app)` → App.tsx switches to jobs view with `sentMode=true`.
- `updateApplicationStatus(id, status)` reads-appends-writes on the server (ADR-0013).

`Application` type: `id, job_id, job_title, company_name, resume_id, cv_version, status, status_history, applied_at`.
Exported from `apiClient.ts` and re-exported from `types.ts`.

## JobDetailView sentMode (OotoCV phase 5)

`sentMode?: boolean` prop on `JobDetailView`. When `true`:
- Shows a "What you sent" banner above the sticky header with `cv_version` badge + `applied_at`.
- Auto-opens `TailorReview` on mount if a tailored resume exists for the job.
- `onBack` prop (optional) → back button navigates to tracker.
- All normal CTAs remain visible but context shifts to "what was sent" framing.

Pass alongside `sentApplication?: Application` so the banner can show the application details.

## Onboarding (OotoCV phase 5)

`Onboarding.tsx` is shown when `localStorage.getItem('onboarding_complete')` is `null`.

- **Step 0**: Animated mock feed (3 mock job cards stagger-fade in with CSS delay). CTA: "Let's set it up →".
- **Step 1**: File upload. `accept=".pdf,.docx"`. Polls `getMasterResume()` after upload; sets
  `onboarding_complete=true` in localStorage when parsing finishes, then calls `onComplete`.
- Progressive save: `onboarding_step` key written on step change so a refresh resumes at Step 1.
- "Skip for now" link sets `onboarding_complete=true` without uploading (user uploads later via My Resume tab).
- Gate in App.tsx: `useState(!localStorage.getItem('onboarding_complete'))`.

## JobDetail component (OotoCV phase 5 polish)

`JobDetail.tsx` displays a single job's evaluation, parsed JD, and tailored resume changes.

**Verdict typewriter**: Uses module-scoped `seenVerdicts: Set<string>` (not useRef) to persist replay state
across unmounts/remounts. When a job ID is already in the set, the typewriter skips animation and shows text immediately.

**Action loading state**: `actionInFlight` state tracks which button is busy ('tailor' | 'apply' | null).
All CTAs show loading text ("Tailoring…", "Applying…") and disable when in-flight.
For `handleTailor` (async): set before call, clear in finally.
For `handleApplyDirect`: set, call handler (opens tab), clear after ~1.5s timeout (parent is fire-and-forget).

**CVDiff loading/error**: CVDiff component accepts optional `loading` and `error` props. Shows
"Loading changes…" with animate-pulse when loading. Shows "Couldn't load changes" in red if error.
Prevents silent failures from swallowed `.catch(() => {})` error handlers.

**Section headings**: "How to strengthen your CV" (formerly "What you'd actually do") aligns with actual
data source: `resume_edits` from evaluation, not job requirements. See agent-lessons #1.

**Gaps to watch**: Renamed from "Red Flags" (was too dramatic) and changed from fragile string-filter
(almost always empty) to show all `evaluation.gaps.technical[]` entries in amber styling.

**Removed CompanyIntel**: Deleted component and all usages. Company/location/posted-at data was
duplicated from hero section. Added `eval_.summary` inline in verdict block (guarded against duplication with reason).

**Borderline hype copy**: Conditional message: if technical gaps exist, shows "Main gap: X. Tailoring can close it."
Else: "Could go either way. Tailoring tips the odds."

**Skip button dedup**: Hidden when verdict !== 'borderline' to prevent two skip buttons (borderline has its own contextual "Skip This One").

**Apply Direct button**: Removed flex-1 width. Added subtitle span: "Opens posting in new tab" in smaller text.

## ViewMode tracker

`ViewMode` includes `'tracker'`. `useJobs` returns empty for `tracker` (same early-return as `resume`).
`Header.tsx` shows a Tracker tab (ClipboardList icon). App.tsx renders `<ApplicationTracker>` when active.

## Environment variables
No `.env` file for frontend — base URL is hardcoded in `apiClient.ts`.
Change `API_BASE_URL` constant if backend port changes.

---

## Go deeper

- UI redesign decisions (wit_line, infinite scroll, recruiter modal) → `docs/decisions/ADR-0007`
- Resume comparison/export → `glassresumatch-ai/components/TailorReview.tsx`
- Job list rendering → `glassresumatch-ai/App.tsx`
