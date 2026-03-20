# ADR-0008 — Action Tab Navigation for Job List

**Date**: 2026-03-17
**Status**: Accepted

---

## Context

The job list sidebar grouped evaluated jobs into Apply / Tailor / Skip / Evaluating sections
within a single scrollable feed. Jobs were fetched 9 at a time in insertion order from the
database, then sorted client-side into sections.

This caused a significant usability problem: with 60+ "Apply now" jobs, the first page load
would return a mixed batch (e.g. 3 apply + 2 tailor + 4 skip). Each section appeared to have
only 3–5 jobs. The global infinite-scroll sentinel sat at the bottom of all sections — to load
more "Apply now" jobs, users had to scroll past Tailor and Skip sections entirely. Most users
never did, and assumed the section was complete.

A second problem: the recruiter contacts pill was derived from the `jobs` array in component
state. The count incremented with every scroll-triggered page load, making it visually unstable.

---

## Decision

Replace the single-scroll sectioned list with a **3-tab strip** (Apply now / Tailor first / Skip)
at the top of the sidebar.

- Each tab maps directly to `filters.action`, which already routes to `fetchEvaluations` with
  a server-side action filter in `useJobs`.
- Infinite scroll operates on the active tab's jobs only — scrolling loads more "Apply now" jobs,
  not a mixed batch.
- Tab counts are sourced from `stats.by_action` (fetched at startup), not from loaded jobs.
- Default tab on load is **Apply now**.
- Section headers inside `JobListPanel` are hidden when a specific tab is active
  (`showSectionHeaders={filters.action === 'all'}`), removing redundant labelling.
- The recruiter contacts pill is fetched independently via `fetchEvaluations(1, 500, action)`
  on tab change — complete and stable regardless of scroll position.

---

## Alternatives considered

**Per-section infinite scroll (sectioned feed)**: Each section would independently paginate using
its own IntersectionObserver. Rejected — requires parallel state management for 4 sections,
complicates the `JobListPanel` interface, and provides no UX advantage over tabs.

**Larger page size (e.g. 100)**: Loading 100 jobs per page would fill most sections on first
load. Rejected — doesn't solve the fundamental UX problem (users still had to scroll past lower
sections to trigger load), and wastes bandwidth for the common case where the user only works
the Apply tab.

---

## Consequences

- `filters.action` defaults to `'apply'` instead of `'all'`.
- The FilterBar action dropdown still works and composes with the tab strip (both mutate
  `filters.action`).
- The "all" view (showing all sections together) remains accessible via FilterBar.
- `JobListPanel` gains two new optional props: `showSectionHeaders` and `activeAction`.
