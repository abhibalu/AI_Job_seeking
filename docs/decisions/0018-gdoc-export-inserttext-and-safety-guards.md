# ADR-0018: GDoc Export — insertText for Additions + Safety Guards

**Status:** Accepted
**Date:** 2026-03-19

## Context

ADR-0015 introduced copy-and-fill GDoc export using `replaceAllText`. This works for
**rewording** existing content but silently drops **additions** — e.g. a new skills line
or extra experience bullet that the tailoring pipeline adds. `replaceAllText` can only
match existing text; it cannot insert new paragraphs.

Two additional bugs were discovered:
1. Company names containing apostrophes (e.g. "Europe's Favourite Airline") broke the
   Drive API query syntax in `_get_or_create_folder` / `_find_existing_doc`.
2. When the tailoring pipeline outputs skills as bare keywords (`["Python", "SQL"]`)
   but the base resume has structured category lines (`["Programming: Python, SQL"]`),
   the positional `zip` replaces each structured line with a single keyword, destroying
   the GDoc's formatting.

## Decision

### 1. Two-phase export: replaceAllText + insertText

After the existing `replaceAllText` batch, a new `_apply_insertions` phase handles additions:
- `_build_gdoc_replacements` now returns `(replacements, insertions)`.
- Insertions are detected when `tailored_data` has more skills or experience bullets than
  `base_data` (items beyond the `zip` range).
- `_apply_insertions` re-reads the doc structure for fresh indices, finds each sibling
  paragraph by fuzzy word overlap, and inserts `\n{new_text}` at `endIndex - 1`.
- Insertions are processed bottom-to-top so earlier inserts don't shift later indices.
- The new paragraph inherits the sibling's paragraph style (font, spacing, indent, bullet
  style) because `insertText` with `\n` splits the paragraph and copies the style.

### 2. Apostrophe escaping in Drive API queries

Single quotes in folder/doc names are escaped (`'` → `\'`) before interpolation into the
Drive API `q` parameter. Affects `_get_or_create_folder` and `_find_existing_doc`.

### 3. Skills format compatibility guard

Before processing skills, the function checks whether both base and tailored skills use
the same format (both have `:` separators or neither does). On mismatch, skills
replacement and insertion are skipped entirely — preserving the base GDoc's formatted
skills section is better than breaking it.

## Consequences

- **Additions now exported:** New skills lines and extra experience bullets appear in the
  GDoc at the correct position with inherited formatting.
- **Apostrophe-safe:** Company names with quotes no longer break the export.
- **Format-safe:** Incompatible skills formats are detected and skipped with a warning
  log, rather than silently destroying the GDoc.
- **Extra API call:** `_apply_insertions` makes one additional `documents().get()` call
  to re-read indices after replacements. Acceptable for single-user export.
