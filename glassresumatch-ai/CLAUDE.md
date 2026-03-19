# glassresumatch-ai/CLAUDE.md

Load me when: task touches frontend components, hooks, types, or apiClient.

---

## Directory layout

```
glassresumatch-ai/
  App.tsx             — main app, job list rendering, view mode routing
  types.ts            — ALL shared TypeScript types
  components/         — one component per file, PascalCase
  hooks/              — custom React hooks
  services/
    apiClient.ts      — singleton API client
  utils/
```

## Component conventions

- One component per file, PascalCase filename.
- Place in `components/`.
- No `alert()` — use Toast component for user feedback.

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

## Feed sort rule (OotoCV)

Within equal `matchScore`, APPLY DIRECT (`recommended_action === 'apply'`) sorts before TAILOR.
Implemented in `utils/sort.ts` smart sort tier. Less friction = more urgent.

## JobCard quick actions (OotoCV phase 2)

`JobCard.tsx` carries a permanent `⋯` (`MoreHorizontal`) icon at `opacity-30` on the card's
top-right, always discoverable. On desktop hover (`group-hover`): icon goes full opacity and the
apply button slides in via `translate-x` + `opacity` transition. On touch: tapping `⋯` toggles
`showActions` local state, revealing buttons inline (no hover required).

Apply button copy is conditional on `Job.tailoring_status`:
- `'ready'` → `"Apply with tailored CV →"` (`cv_version: 'tailored'`)
- anything else → `"Apply with base CV →"` (`cv_version: 'base'`)

Clicking the button: opens `job_url` in a new tab + calls `onAction(jobId, cvVersion)` (passed as
prop). The parent wires `onAction` to `markActioned` + `patchJobAction`.

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
- `handlers.onRunComplete(event)` — fired on `event: run_complete`; hook closes the connection.
- `handlers.onError(err)` — fired on `es.onerror`; **do NOT close** — native auto-reconnect handles it.
- Handler refs are stable (`useRef`) — changing handlers never restarts the `EventSource`.
- `useEffect` depends only on `taskId`; cleans up (`es.close()`) on unmount or `taskId` change.

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

## Environment variables
No `.env` file for frontend — base URL is hardcoded in `apiClient.ts`.
Change `API_BASE_URL` constant if backend port changes.

---

## Go deeper

- UI redesign decisions (wit_line, infinite scroll, recruiter modal) → `docs/decisions/ADR-0007`
- Resume comparison/export → `glassresumatch-ai/components/TailorReview.tsx`
- Job list rendering → `glassresumatch-ai/App.tsx`
