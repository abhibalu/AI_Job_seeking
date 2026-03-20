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
    Dashboard.tsx     — feed pane (3 card formats: TailorCard, ApplyDirectCard, SkipCard)
    JobDetail.tsx     — detail pane (verdict-conditional layout, typewriter, MatchBrief, CVDiff)
    TailoringReview.tsx — change-level review (Accept/Reject, cover letter, approve footer). Sticky footer: progress bar (reviewed/total fraction, replaces colored stat counters) + "Accept all remaining →" + "Skip" + "GDoc ▾" dropdown (groups Open + Re-export) + "Approve & Send →" primary CTA. GDoc dropdown has click-outside-to-close via mousedown listener.
    ApplicationTracker.tsx — tracker cards with status chips and timeline dots
    SetupPage.tsx     — onboarding (isOnboarding=true) and settings (isOnboarding=false); two-tile flow for PDF/DOCX upload and Google Doc import. Settings mode fetches `getMasterResume()` on mount to show a "current resume" indicator (✓ name · updated timestamp · open doc ↗). `sourceGdocUrl` link only appears when resume was imported from Google Docs. Settings also renders the External Services kill-switch panel (openrouter/apify/google_docs toggles) when `toggles` are loaded. `onTogglesChanged?: () => void` prop triggers `refreshToggles` in App.tsx so service guards re-apply app-wide after a toggle change. GDoc import tile and button are disabled (opacity-40) when `google_docs` toggle is off.
  components/         — shared/reusable components only
    Sidebar.tsx       — nav + logo + cron status indicator
    TailoringStrip.tsx — floating process card during active tailoring (6-stage pipeline track + typewriter + stop)
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

`formatTimeAgo()` output by age: `just now` (< 1m) → `Xm ago` → `Xh ago` → `Xd ago` (up to 7d) → `Mar 12` (same year, > 7d) → `Mar 12, 2023` (different year). Timestamps older than 7 days always render as a calendar date, not a relative string.

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

`exportToGoogleDocs(jobId)` — `POST /api/resumes/export-gdoc/{jobId}`, returns structured
`ExportResultResponse` with `status` (success/partial/failed/no_changes), `url`, `path`,
`summary` (total/applied/skipped), and `skipped_fields` list with failure reasons. Frontend
shows toast variants per status (green/amber/red/info) and opens doc on success/partial/no_changes.

`getServiceToggles()` — `GET /api/settings/services`, returns `ServiceToggles` (openrouter/apify/google_docs booleans).
`updateServiceToggle(service, enabled)` — `PATCH /api/settings/services`, returns updated `ServiceToggles`.
Both used by App.tsx (fetches on mount, exposes `refreshToggles`) and SetupPage (renders kill-switch UI).
`ServiceToggles` interface exported from `apiClient.ts`; passed as prop to Dashboard, JobDetail, TailoringReview.

`TailoredResume` type now includes `gdoc_url: string | null` — the GDoc URL set after first export.

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
them produces empty verdict blocks and misleading grouping.

## Feed sort rule (OotoCV)

Within equal `matchScore`, APPLY DIRECT (`recommended_action === 'apply'`) sorts before TAILOR.
Implemented in `utils/sort.ts` smart sort tier. Less friction = more urgent.

## Dashboard card quick actions (OotoCV rebuild)

`Dashboard.tsx` renders four card formats. `TailorCard` and `ApplyDirectCard` both have hover-reveal
quick action buttons.

**TailorCard** (verdict: tailor) — two distinct props:
- `onTailorStart()` — primary button ("Tailor CV" / "Review & Send"). Wired
  to `handleTailorStart` in App.tsx, which checks `tailoring_status` first:
  - `'ready'` → `getTailoredVersions(jobId)` then `navigate('/tailoring/:id')` (existing review)
  - `'processing'` → toast "Already tailoring this job" (no duplicate run)
  - otherwise → `tailorResume(jobId)` returns `task_id` → sets `tailoringJob` + `tailoringTaskId` → TailoringStrip appears with SSE tracking
- `onSkip()` — ghost "Skip" button. Wired to `handleSkip` (marks actioned, no API call).
- `isTailoring?: boolean` — disables tailor button when another tailoring run is active.

Button label is conditional on `job.tailoring_status`:
- `'ready'` → `"Review & Send"` (don't re-run pipeline)
- otherwise → `"Tailor CV"`

**Concurrency guard**: `handleTailorStart` checks `tailoringJob` state — only one tailoring run
at a time. Dashboard cards are disabled via `isTailoring` prop during active runs.

**Important**: `onTailorStart` and `onAction` (apply) are separate props — never conflate them.
Wiring "Tailor CV" to the apply handler silently applies the job without tailoring it.
See agent-lessons #16.

**Dashboard freshness signal** (Theme B): Both `TailorCard` and `ApplyDirectCard` now append `formatTimeAgo(job.posted_at)`
to the company row. Example: "Google · San Francisco · 2d ago". Reduces information density gap between list and detail view;
provides quick job-age signal without clicking into detail. Uses existing `posted_at` field from job list response.

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

**In-place evaluation updates:**
- `updateJobEvaluation(jobId, evaluation)` — patches a single job's evaluation in the `jobs` array without clearing/reloading the list
- Use when the backend evaluates a single job (e.g., on-demand re-evaluation) and the UI needs to reflect the new verdict immediately
- Sets `job.evaluation` and `isEvaluated = true` atomically

## SSE hook (`hooks/useSSE.ts`)

`useSSE(taskId: string | null, handlers)` — opens a single `EventSource` per `taskId`.

- Pass `null` to keep hook dormant (no connection opened).
- `handlers.onProgress(event)` — fired on `event: progress` SSE events.
- `handlers.onRunComplete(event)` — fired on `event: run_complete` (`completed` / `failed` / `cancelled`); hook closes the connection.
- `handlers.onError(err)` — fired on `es.onerror`; **do NOT close** — native auto-reconnect handles it.
- Handler refs are stable (`useRef`) — changing handlers never restarts the `EventSource`.
- `useEffect` depends only on `taskId`; cleans up (`es.close()`) on unmount or `taskId` change.

## TailoringStrip (floating process card + SSE tracking)

`TailoringStrip.tsx` is a floating process card that displays real pipeline progress via SSE and allows cancellation.

**Layout**: Fixed positioned `bottom-6 left-1/2 -translate-x-1/2 z-50 w-[420px]` — floats centered above all content, no layout disruption.

**Visual design**:
- Top accent border: `border-t-2 border-accent` — draws the eye immediately.
- Container: `bg-surface border border-white/10` — matches surface styling, no shadows/blur.
- Job context line (top): `job.title · job.company_name` in `text-xs gray-500`, with "Stop Tailoring" button in top-right.
- Pipeline stage track (middle): 6 dots (`queued` → `planning` → `drafting` → `critiquing` → `revising` → `saving`):
  - Past stages: small filled accent dot
  - Current stage: larger pulsing accent dot (`animate-pulse`)
  - Future stages: dim `bg-white/15` dot
- Stage message (bottom): Uses `TypewriterWaitState` with `key={stage}` to reset animation on each stage advance.
  After animation completes within a stage, displays static text until next stage transition.
  Maps `progress.stage` to user-facing messages:
  `queued` → "Starting up…", `planning` → "Analyzing job requirements…",
  `drafting` → "Tailoring your CV…", `critiquing` → "Reviewing changes…",
  `revising` → "Refining edits…", `saving` → "Saving your tailored CV…"

**Behavior**:
- Reads `progress.stage` from SSE `onProgress` events; updates dot track and resets typewriter.
- On `run_complete` with `status !== 'cancelled'`: extracts `progress.resume_id` and calls
  `onComplete(jobId, resumeId)` for direct navigation to review page.
- "Stop Tailoring" button calls `onCancel()` (which calls `apiClient.cancelTask(taskId)` in App.tsx).
  Shows "Stopping…" while cancel is in-flight.

## Toast rollback pattern

`Toast` accepts optional `onRetry?: () => void`. When set, renders an underlined "Retry" button
beside the dismiss `✕`. Use for any optimistic-update failure where the user should be able to
retry the action in-place.

**Error detail in toasts**: Never show generic "X failed" — always extract `err.message` (or
`err.detail`) and include it so the user knows *why*. See agent-lessons #20.

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

**Approve & Send Button** (`handleApprove`):
- Calls `updateTailoredStatus(id, 'approved')` first.
- Exports to Google Docs via `apiClient.exportToGoogleDocs(jobId)`.
- Returns structured `ExportResultResponse` with `status` (success/partial/failed/no_changes), summary counts, and skipped fields.
- Toast feedback per status:
  - `success`: green toast, opens doc
  - `partial`: amber toast "Exported with N of M changes skipped", opens doc
  - `failed`: red toast with failure reasons, does not open
  - `no_changes`: info toast, opens doc
- Sets `gdocExported = true` after export attempt.

**Re-export Button** (appears after first export):
- Visible only when `gdocExported === true`.
- Same toast feedback as `handleApprove` on retry.
- Allows user to re-attempt export if first attempt had failures or they made manual edits to the doc.

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

## JobDetail component (OotoCV phase 5 + density overhaul)

`JobDetail.tsx` displays a single job's evaluation, parsed JD, and tailored resume changes.

### UI Density Overhaul (ADR-0015 candidate)

Content area spacing tightened per UI Info Density Guidelines:
- Hero content: `p-8 space-y-6` → `p-6 space-y-4` (16px + 32px total savings)
- Job section columns: `gap-14` → `gap-6` (32px savings, maintains visual separation)
- Footer padding: `px-8` → `px-6` (symmetry with content area)
- Hype copy footer text removed entirely (0 IU, verdict block is the canonical signal)
- Empty states compacted: removed centered icon, kept minimal inline text

### Metadata Row (New — Theme B)

Horizontal metadata row between tags and verdict block displays:
```
[Clock] 2d ago  ·  [Users] 47 applicants  ·  [DollarSign] $120-150k  ·  [Mail] recruiter@co.com
```

Uses `job.posted_at` (via `formatTimeAgo()`), `job.applicants_count`, `job.salary_info`, `eval_.recruiter_email`.
All fields null-safe with gap-3 separators. Metadata row only renders if at least one field is truthy.

### MatchBrief Progressive Disclosure (Theme C)

- Default: shows first 3 strengths + 3 gaps (was 5+5 = 10 items)
- If more items exist: shows "+N more" toggle to expand to full list (up to 5 each)
- Removed signal dots section from MatchBrief (hero verdict block is the canonical signal; ADR-0007 already settled this)
- Saves ~200px on average detail view, recovery button visible if expansion needed

### Apply Verdict Full Layout (Theme E)

Apply verdict layout changed from `JobSection` only to full layout:
```tsx
<MatchBrief /> + <JobSection /> + <CVDiff />
```

APPLY jobs now show decision-supporting data (strengths/gaps from eval + job requirements + CV changes if ready).
Gains ~400px of high-IU content; matches TAILOR layout schema.

### Layer 3 — Collapsible Deep-Dive Sections (Theme D)

Collapsible component (inline in JobDetail.tsx) provides progressive disclosure for lower-priority details.
Shows only for non-SKIP verdicts. Sections:

1. **Interview Prep** — `high_priority_topics` (topic + why + prep) and `questions_to_ask` from `eval_.interview_tips`
   - Topics rendered in bordered boxes; questions as bullet list
2. **ATS Keywords** — `ats_keywords` from parsed JD as inline pill badges
   - Tailor only (Apply Direct skips ATS signal)
3. **Company** — Shows `applicants_count` when > 0
   - Future: company_employees_count, company_description (needs JobDetail fetch per ADR-0015)

Each collapsible is a lightweight header line (no rounded bg, no border, just a divider line) with ChevronDown icon for rotation animation.

### Tag Redundancy Cleanup (Theme F)

Location removed from tags — already shown in company row. Saves a badge slot, prevents duplication.

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

**Skip button**: Always visible in footer for all verdicts.

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
