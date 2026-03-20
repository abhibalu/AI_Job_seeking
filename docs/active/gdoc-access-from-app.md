# Plan: GDoc Access from App

**Status:** ✅ Complete
**Created:** 2026-03-19
**Branch:** feature/ootocv-build

## Goal

After a tailored resume is exported to Google Docs, the app should show a persistent
"Open in GDoc ↗" link on the TailoringReview page — visible on every visit, not just
the current session. Currently the `gdoc_url` is saved to the DB and returned by the API
but the TypeScript type doesn't include it, so the UI can't surface it.

Done looks like: open TailoringReview for any previously-exported resume → see "Open in GDoc ↗"
link that navigates directly to the live document, without re-exporting.

## Decisions Made

- **No backend change needed**: `get_tailored_resume()` uses `select("*")`, so `gdoc_url` is
  already in the API response — it's a frontend-only fix.
- **Single source of truth**: derive the GDoc link from `resume.gdoc_url` (DB-persisted), not
  from a session-only `gdocExported` boolean. After a new export, update local state with `result.url`.
- **Link placement**: sticky footer bar in TailoringReview, left of the action buttons. Small, non-intrusive.
- **"Re-export" button stays**: keep the re-export flow. Show the "Open in GDoc ↗" link whenever
  a URL exists (pre-loaded or just exported); show "Re-export" alongside it.

## Open Questions

- [ ] Should the GDoc link also appear on Dashboard TailorCards for jobs with `tailoring_status = 'ready'`?
      (scope it there only if the TailoringReview link proves insufficient)

## Out of Scope

- Surfacing GDoc links in ApplicationTracker (separate feature)
- Embedding a GDoc iframe or preview inside the app
- Per-field export status display in the footer

---

## Implementation Checklist

### Frontend (glassresumatch-ai/)

- [x] **1a. Add `gdoc_url` to `TailoredResume` type** (`services/apiClient.ts`, line ~412)
  - Add `gdoc_url?: string | null` to the `TailoredResume` interface

- [x] **1b. Rewrite GDoc URL state in `TailoringReview.tsx`**
  - Remove `gdocExported: boolean` state
  - Add `gdocUrl: string | null` state, initialized from `resume.gdoc_url` in the `useEffect` load handler
  - After successful export (`handleApprove`) or re-export (`handleReexport`): `setGdocUrl(result.url)` on `success | partial | no_changes` statuses
  - Replace all `gdocExported` references with `!!gdocUrl`

- [x] **1c. Add "Open in GDoc ↗" link to sticky footer**
  - Render when `gdocUrl` is truthy (alongside existing re-export button)
  - Use `<a href={gdocUrl} target="_blank" rel="noopener noreferrer">` styled as a ghost link button
  - Label: `"Open in GDoc ↗"` (consistent with existing GDoc language in the app)
  - Placement: left of "Re-export to GDoc" button in the footer

### Backend (agents/, api/)

- No changes needed.

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: All 3 steps done. `gdoc_url` added to `TailoredResume` type; `gdocExported` boolean replaced with `gdocUrl` string state (seeded from DB on load); "Open in GDoc ↗" link added to sticky footer left of re-export button; both GDoc buttons gated on `gdocUrl` truthy.
