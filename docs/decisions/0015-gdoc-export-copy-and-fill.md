# ADR-0015: Google Docs Export — Copy-and-Fill Path

**Status:** Accepted
**Date:** 2026-03-19

## Context

The original Google Docs export built resume content as plain text and inserted it into a blank
new document (`insertText` batchUpdate). This produced correctly structured output but lost all
formatting — font choices, heading styles, spacing — from the user's original resume template.

Users maintain their base resume in a specific Google Doc with their preferred formatting. The
export pipeline should produce a tailored doc that looks identical to the base, with only the
changed content replaced.

## Decision

When `GOOGLE_BASE_RESUME_DOC_ID` is set in the environment, `create_tailored_resume_doc()` uses a
**copy-and-fill** path instead of the plain-text insert path:

1. Copy the base resume GDoc (`drive.files().copy()`), placing it in the company subfolder.
2. Apply a `replaceAllText` batchUpdate for each string that changed between the base and
   tailored resume (`_build_replacement_map()` in `api/routes/resumes.py`).

When `GOOGLE_BASE_RESUME_DOC_ID` is not set, the old plain-text insert path is used unchanged
(backwards compatible).

## Replacement Map

`_build_replacement_map(base, tailored)` diffs the two resume dicts (frontend format) and
returns `{old_text: new_text}` for summary, experience bullets, and skills. Only non-empty,
changed strings are included. Position-based matching (`zip`) is used for list fields.

## Consequences

- **Formatting preserved:** The exported doc inherits paragraph styles, fonts, and layout from
  the base doc — no more blank-formatted output.
- **New env var required:** `GOOGLE_BASE_RESUME_DOC_ID` (optional — leave unset to keep old
  plain-text path).
- **Limitation:** `replaceAllText` is case-sensitive and matches literal strings. Edits that
  change only casing or punctuation may not match. Additions of entirely new bullets (no
  corresponding base text) are not currently inserted into the copy.
- **Old path preserved:** Plain-text insert path remains for users without a base GDoc or for
  resume structures that differ too much for string-level replacement.
