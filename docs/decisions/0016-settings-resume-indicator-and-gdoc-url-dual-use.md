# ADR-0016: Settings Resume Indicator and `gdoc_url` Dual-Use

**Date:** 2026-03-19
**Status:** Accepted

---

## Context

The Settings page showed an identical blank state whether or not a base CV had been uploaded.
Users returning to the page had no confirmation that their resume existed, who it belonged to,
when it was last updated, or whether the Google Doc they imported from was still the intended source.

Separately, the `gdoc_url` column on the `resumes` table was only used by the export-gdoc route
(to store the URL of an exported tailored resume). Master resume rows never had a `gdoc_url` value.

---

## Decision

### 1 — Settings resume indicator

`SetupPage.tsx` (settings mode) fetches `GET /api/resumes/master` on mount and displays a
one-line indicator above the import buttons:

```
✓ Abhijith Sivadas  · updated 2d ago  · open doc ↗
```

- `✓` in `text-semantic-green` — parse receipt (confirms CV was loaded and parsed)
- Name in `text-gray-300` — identity confirmation
- Timestamp in `text-gray-600 text-[11px]` — freshness signal via `formatTimeAgo()`
- `· open doc ↗` link — only rendered when `sourceGdocUrl` is non-null (GDoc imports only)
- Indicator refreshes after each successful upload/import without requiring a page reload

The indicator is absent (not a ghost/placeholder) when no resume exists.

### 2 — `gdoc_url` dual use by row type

Rather than adding a new column, `gdoc_url` is repurposed per row type:

| `status` value | `gdoc_url` meaning |
|---|---|
| `master` | Source Google Doc the base CV was *imported from* |
| tailored (`pending` / `approved` / etc.) | Google Doc the tailored resume was *exported to* |

This is safe because:
- The export route already filters out master rows (`status != 'master'`)
- Master rows are never exported, so the export path can never overwrite the source URL
- The distinction is documented and enforced at the DB helper level (see `agents/CLAUDE.md`)

### 3 — `get_master_resume()` return shape changed

Previously returned raw content dict (or `None`).
Now returns `{"content": dict, "updated_at": str | None, "gdoc_url": str | None}` or `None`.
All callers must unpack `row["content"]` before passing to `_to_frontend_format()`.

### 4 — `GET /api/resumes/master` response additions

Two new fields added to the response JSON:
- `updatedAt` — ISO timestamp of when the master row was last written
- `sourceGdocUrl` — source Google Doc URL; `null` for file uploads

---

## Consequences

- Settings page always reflects current CV state at a glance — no silent blank state
- GDoc importers can verify they're using the intended source document
- `gdoc_url` column semantics are now context-dependent; must consult ADR-0016 or
  `agents/CLAUDE.md` before adding new read/write paths on that column
- File-uploaded resumes never populate `sourceGdocUrl`; that field is GDoc-import only
