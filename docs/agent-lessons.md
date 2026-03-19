# Agent Lessons Log

When Claude makes a mistake seen before:
1. Add an entry here.
2. Update the relevant domain CLAUDE.md.
**This log must not be the only home** — entries without a "propagated to" are incomplete.

---

## 1. Temperature for extraction agents
**Source**: ADR-0006 (2025)

**Mistake**: `ResumeParserAgent` inherited `BaseAgent` default `temperature=0.7`. Parsing was
treated as a creative task — output summarised and truncated content instead of extracting verbatim.

**Correct pattern**: Any agent doing extraction or parsing must set `temperature=0.1` explicitly
in `__init__`. Never rely on the `BaseAgent` default of `0.7` for non-creative tasks.

```python
def __init__(self, model=None):
    super().__init__(model=model, temperature=0.1)  # extraction — verbatim fidelity
```

**Propagated to**: `agents/CLAUDE.md` (temperature table), `agent_prompts/CLAUDE.md` (temperature table)

---

## 2. ATS keyword field name mismatch
**Source**: ADR-0004 (2025)

**Mistake**: `api/routes/resumes.py` and `pipeline_graph.py` passed `keywords_to_include` to
`ResumeTailorAgent`. `JDParserAgent` outputs `ats_keywords`. The tailor received an empty keyword
list silently — no error, wrong output.

**Correct pattern**: When wiring one agent's output as input to the next, verify field names
end-to-end. Do not assume a name matches intent — check the actual output schema of the upstream agent.

```python
# Correct wiring in node_tailor():
"ats_keywords": parsed_jd.get("ats_keywords", []),   # matches JDParser output field
```

**Propagated to**: `agents/CLAUDE.md` (field name wiring section)

---

## 3. One-shot examples in user prompt, not system prompt
**Source**: ADR-0006 (2025)

**Mistake**: One-shot examples placed in the system prompt bloated every LLM call with static
content that only provides value when paired with real input data.

**Correct pattern**: Embed one-shot examples in `build_user_prompt()`. The system prompt stays
lean (role + instructions). The user prompt carries the example alongside the actual input,
giving the model a direct comparison target.

```python
def build_user_prompt(self, **kwargs) -> str:
    return f"""
    Example input: ...
    Example output: ...

    Now process this:
    {kwargs['actual_input']}
    """
```

**Propagated to**: `agent_prompts/CLAUDE.md` (one-shot examples section), `agents/CLAUDE.md`

---

## 5. Don't derive stable UI state from paginated list state

**Source**: ADR-0008 (2026-03-17)

**Mistake**: The recruiter contacts pill in `JobListPanel` built its contact list by filtering
the `jobs` prop. Because `jobs` grows incrementally as the user scrolls, the pill count
changed on every infinite-scroll trigger — visually unstable and incomplete until fully loaded.

**Correct pattern**: Any UI element that represents **complete** data (total counts, contact
lists, summary stats) must be fetched independently from the paginated list. Use a dedicated
API call scoped to the relevant filter, not a derivation from partial in-memory state.

```ts
// Wrong: derived from paginated jobs array — incomplete until fully scrolled
useEffect(() => {
    setRecruiterJobs(jobs.filter(j => j.evaluation?.recruiter_email));
}, [jobs]);

// Correct: independent fetch, scoped to active tab, runs on tab change only
useEffect(() => {
    fetchEvaluations(1, 500, activeAction).then(result => {
        setRecruiterJobs(result.data.filter(e => e.recruiter_email));
    });
}, [activeAction]);
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 6. Reset totalJobs when switching paginated filters

**Source**: 2026-03-17

**Mistake**: `useJobs` reset `jobs` and `currentPage` on filter change but not `totalJobs`.
`hasMore = jobs.length < totalJobs`. After `setJobs([])`, `jobs.length = 0` but `totalJobs`
still held the previous tab's value — so `hasMore` stayed `true` throughout the tab switch.
The `IntersectionObserver` effect had `[hasMore]` as its only dependency. Because `hasMore`
never changed (true → true), the effect never re-ran after the new data loaded, leaving the
sentinel unobserved. Infinite scroll silently stopped working on every tab except the first.

**Correct pattern**: Reset `totalJobs` to `0` alongside `jobs` and `currentPage` on filter
change. This forces `hasMore` to cycle `false → true` when new data loads, reliably
re-triggering the observer effect.

```ts
useEffect(() => {
    setCurrentPage(1);
    setJobs([]);
    setTotalJobs(0); // forces hasMore false→true so observer re-attaches on new data
    load(1, false, true);
}, [viewMode, filters.action, filters.verdict, filters.searchQuery]);
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 7. Use a ref for IntersectionObserver callbacks to avoid observer churn

**Source**: 2026-03-17

**Mistake**: The `IntersectionObserver` effect in `JobListPanel` had `[hasMore, loadMore]` as
deps. `loadMore` changed every time `loadingMore` flipped (it was in `loadMore`'s `useCallback`
deps). This caused the observer to disconnect and reconnect on every loading state change.
On reconnect, if the sentinel had just been pushed below the viewport by newly appended items,
the observer would set up and wait — but since the user was already at the bottom of the old
list, they couldn't scroll further to re-trigger it.

**Correct pattern**: Store `loadMore` in a ref so the observer callback is always current
without needing to be recreated. Only include `hasMore` in the effect deps — the observer
only needs to reconnect when the sentinel mounts or unmounts.

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

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 8. Migration INSERT without ON CONFLICT is not idempotent

**Source**: 2026-03-19

**Mistake**: `003_consolidate_resumes.sql` ran `INSERT INTO resumes ... FROM tailored_resumes` without `ON CONFLICT DO NOTHING`. If the migration failed mid-run or was re-applied, rows already copied to `resumes` on the first pass caused a `duplicate key value violates unique constraint "resumes_pkey"` error, blocking all subsequent re-runs.

**Correct pattern**: Any data migration INSERT that copies rows by primary key must include `ON CONFLICT (id) DO NOTHING` to make it idempotent and safe to re-run.

```sql
INSERT INTO resumes (id, ...)
SELECT id::uuid, ...
FROM tailored_resumes
ON CONFLICT (id) DO NOTHING;
```

**Propagated to**: `agents/CLAUDE.md` (DB section)

---

## 4. Force-saved resume status must differ from critic-approved
**Source**: ADR-0004 (2025)

**Mistake**: Resumes hitting the max revision limit (2) were saved with `status="pending"`,
identical to critic-approved resumes. Human review was impossible — no way to distinguish
clean approvals from force-saves with unresolved flaws.

**Correct pattern**: Check for unresolved critique before saving. Use `needs_review` for
force-saves, `pending` only for zero-flaw critic approval.

```python
is_force_save = bool(state.get("critique", []))
save_status = "needs_review" if is_force_save else "pending"
```

**Propagated to**: `agents/CLAUDE.md` (resume status semantics section)

---

## 9. Misleading section heading in JobDetail
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` section titled "What you'd actually do" displayed `resume_edits` from
the evaluation (AI suggestions for CV improvements). Users expected job responsibilities, not
resume tailoring tips. The mismatch caused confusion about what data was shown.

**Correct pattern**: Match heading to actual data source. Use "How to strengthen your CV" for
`resume_edits`. Track as separate follow-up: add `responsibilities` field to `ParseResult` schema
(requires agent prompt + migration) to restore "What you'd actually do" with real job duties.

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 10. Duplicate skip buttons on borderline verdict
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` rendered a generic "Skip" button in the CTA footer for all verdicts,
plus a contextual "Skip This One" button in the borderline verdict section. Users saw two skip
buttons, creating confusion about which one to click and duplicating UI real estate.

**Correct pattern**: Conditional render the generic skip button: show only when `verdict !== 'borderline'`.
The borderline section has its own "Skip This One" + "Tailor Anyway" pair. This unambiguously
separates decision patterns: other verdicts get single-CTA footer, borderline gets side-by-side choice.

```tsx
{verdict !== 'borderline' && (<button>Skip</button>)}
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 11. No feedback after CTA clicks
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` CTAs (`handleTailor`, `onAction`) had no loading states. Clicking
"Tailor & Approve" or "Apply Direct" appeared to do nothing — especially problematic on slow networks.

**Correct pattern**: Track action state (`actionInFlight: 'tailor' | 'apply' | null`). All buttons show
loading copy ("Tailoring…", "Applying…"), disable (`disabled={!!actionInFlight}`), and visually fade
(`opacity-50 cursor-not-allowed`). For async handlers, set before call, clear in finally.
For fire-and-forget (e.g., `onAction` opens a new tab), set before and clear via timeout (~1.5s).

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 12. Typewriter animation replays on remount
**Source**: 2026-03-19

**Mistake**: `VerdictTypewriter.tsx` used `useRef<Set<string>>(new Set())` inside the component.
On remount (navigating away and back to the same job), the ref was recreated, losing the previous
`seenVerdicts` set. Result: typewriter animated every time the user viewed the job, no caching.

**Correct pattern**: Move replay tracking outside the component to module scope. Use a module-level
`seenVerdicts: Set<string>` so state persists across unmounts and remounts.

```ts
// Module scope — survives component lifecycle
const seenVerdicts = new Set<string>();

const VerdictTypewriter: React.FC<{...}> = ({ text, jobId }) => {
    if (seenVerdicts.has(jobId)) {
        // Skip animation, show full text immediately
        setDisplayed(text);
        setDone(true);
        return;
    }
    // Animate, then add jobId to seenVerdicts when done
};
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 13. Red flags filter almost always empty
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` filtered `evaluation.gaps.technical` by string matching `'red flag'` or
`'concern'`. But the evaluation agent rarely includes these exact strings — they're incidental in prose,
not formatted as structured red flags. Result: section almost always empty, even when gaps existed.

**Correct pattern**: Show all technical gaps without filtering. Rename section from "Red Flags" (too
dramatic) to "Gaps to watch" (accurate, lower-stakes). Use amber styling instead of red to signal
"warnings" not "blockers."

```ts
const technicalGaps = evaluation.gaps?.technical || [];
// Show all, no string filter
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 14. CompanyIntel duplication
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` rendered a `CompanyIntel` component showing company name, location, posted
date. All three fields were already visible in the hero section at the top of the page. The duplication
wasted vertical space and violated the single-source-of-truth principle.

**Correct pattern**: Delete the `CompanyIntel` component entirely. Relocate the unique summary data
(`eval_.summary`) into the verdict block instead, guarded against duplication with the `wit_line`.
This preserves the summary insight while eliminating redundancy.

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 15. CVDiff silent failure (swallowed errors)
**Source**: 2026-03-19

**Mistake**: `JobDetail.tsx` fetched resume changes with `.catch(() => {})`, swallowing all errors.
The UI showed nothing — no loading indicator, no error message. Users didn't know if the data was
still loading, failed to fetch, or simply absent.

**Correct pattern**: Implement explicit loading and error states. Add `changesLoading` and
`changesError` state. Update useEffect to set/clear loading, and set error on catch. Pass both
to `CVDiff` component, which renders appropriate UI:
- Loading: "Loading changes…" with animate-pulse
- Error: "Couldn't load changes" in red
- Empty: nothing
- Data: full diff list

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 16. Feed card primary button wired to apply handler instead of tailor handler
**Source**: 2026-03-19

**Mistake**: `TailorCard` in `Dashboard.tsx` had `onAction: (cv: 'base' | 'tailored') => void` as its
primary button prop. The button labelled "Tailor & Approve" called `onAction(cv)`, which in App.tsx
was `handleAction` — the **apply** handler that opens the job URL, records a CV version, and creates
an application. Clicking "Tailor & Approve" silently opened the job posting in a new tab and recorded
an application, as though the user had already applied. `onTailorStart` was never added to `DashboardProps`
so there was no route to the tailoring pipeline from the feed card.

**Correct pattern**: Feed card CTAs that trigger distinct flows need distinct prop names wired to the
correct App-level handlers. "Tailor" and "Apply" are different actions; conflating them into a shared
`onAction` prop hides the mismatch. Additionally, `handleTailorStart` in App.tsx should check
`tailoring_status === 'ready'` first and navigate to the existing review instead of re-running the
pipeline — avoids redundant API calls when tailoring is already complete.

```tsx
// Dashboard: correct prop interface
interface DashboardProps {
  onTailorStart: (jobId: string) => void;  // triggers pipeline or navigates to review
  onAction: (jobId: string, cvVersion: 'base' | 'tailored') => void;  // apply only
}

// TailorCard: correct button handler
<button onClick={() => onTailorStart()}>
  {job.tailoring_status === 'ready' ? 'Review & Send' : 'Tailor & Approve'}
</button>

// App.tsx: handleTailorStart handles both states
if (job.tailoring_status === 'ready') {
  apiClient.getTailoredVersions(jobId).then(v => navigate(`/tailoring/${v[0].id}`));
  return;
}
// else trigger pipeline as normal
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

## 18. Unevaluated jobs leak into Dashboard feed as empty cards

**Source**: 2026-03-19

**Mistake**: `useJobs('all', filters)` passed `is_evaluated: undefined` to the jobs API. All jobs
were returned, including unevaluated ones. Unevaluated jobs have no evaluation data, so
`getVerdictType` defaulted to `'borderline'`, placing them in the "Your call" section with
empty verdict blocks (no wit_line, no summary, no gaps). The card rendered with blank text
areas and a generic "Review required" fallback.

**Correct pattern**: The Dashboard feed is designed for evaluated jobs. Pass `is_evaluated: true`
as the default for any viewMode that renders evaluation-dependent UI (verdict blocks, scores,
summaries). Only use `is_evaluated: false` for the explicit "pending" viewMode.

```ts
// Wrong: undefined lets unevaluated jobs through
const isEvaluatedFilter = viewMode === 'pending' ? false : undefined;

// Correct: default to true — feed cards need evaluation data
const isEvaluatedFilter = viewMode === 'pending' ? false : true;
```

**Propagated to**: `glassresumatch-ai/CLAUDE.md`

---

## 17. Synchronous tailoring endpoint wastes LLM credits on cancel

**Source**: 2026-03-19

**Mistake**: `POST /api/resumes/tailor/{job_id}` ran the full LangGraph pipeline synchronously.
The frontend "Cancel" button only cleared UI state — the backend kept running all 3-4 LLM calls
to completion. No concurrency guard meant clicking multiple cards fired parallel pipelines.
Dashboard card buttons had no `disabled` guard, enabling rapid-fire accidental clicks.

**Correct pattern**: Use the background task + SSE pattern (already proven for batch evaluation).
Endpoint returns `task_id` immediately, worker checks `get_task_status()` at each node boundary
for cancellation. Frontend tracks real progress via SSE. One tailoring run at a time via
App-level `tailoringJob` guard. Dashboard buttons disabled during active tailoring.

**Propagated to**: `api/CLAUDE.md`, `glassresumatch-ai/CLAUDE.md`, `docs/decisions/ADR-0014`
