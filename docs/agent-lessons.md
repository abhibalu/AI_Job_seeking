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
