# Feature: gdoc_base_resume

> Load me when: task touches Google Docs import/export, google_docs.py, GDrive folder
> structure, or the base resume ingestion flow.

## 1. Logic (The Mental Model)

The "Base Resume" is the single source of truth for the candidate's professional identity. This feature provides bidirectional integration with Google Docs:

- **Import**: Pull a resume from Google Docs, parse it via LLM, and save as the master resume
- **Export**: Push a tailored resume to Google Docs for final editing and sharing

Instead of treating the resume as a static file requiring a specialized editor, the system treats Google Docs as a **Collaborative Workspace** — the user maintains their resume in a familiar word processor, and the system can read from and write to it.

### System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition (Import)** | User has a resume in Google Docs. OAuth credentials are configured. |
| **Process (Import)** | The Extractor reads plain text from the doc, the ResumeParserAgent converts it to JSON Resume format, and it's saved as the master resume. |
| **Post-Condition (Import)** | A new master resume is available for the tailoring pipeline. |
| **Pre-Condition (Export)** | A tailored resume exists for a specific job. |
| **Process (Export)** | The system creates/updates a Google Doc in the configured Drive folder with the formatted resume content. |
| **Post-Condition (Export)** | A shareable Google Doc URL is available for the user. |

### Workflow Chain

#### Import Flow
1. **URL/ID Input**: User provides a Google Doc URL or document ID via the frontend.
2. **Text Extraction**: `read_google_doc()` traverses the document body, concatenating `textRun` content.
3. **AI Parsing**: `process_resume_background()` runs `ResumeParserAgent` to convert plain text to JSON Resume format.
4. **Master Save**: Parsed resume is saved as the new master resume in Supabase.

#### Export Flow
1. **Trigger**: User clicks "Export to Google Docs" on a tailored resume.
2. **Folder Resolution**: System finds/creates a company subfolder in the configured Drive folder.
3. **Doc Creation**: Resume content is formatted as plain text and inserted into a new/existing Google Doc.
4. **URL Return**: The Google Doc URL is returned to the frontend.

## 2. Architecture & Contracts

### Component Boundaries

#### Import Path

1.  **The Frontend (React)**
    - *Responsibility:* Collect Google Doc URL/ID from user, trigger import, poll for completion.
    - *Boundary:* Sends `document_id` to API. Polls `GET /api/resumes/master` until status changes from `processing`.

2.  **The API Endpoint (`POST /api/resumes/import-gdoc`)**
    - *Responsibility:* Validate request, extract text from Google Doc, trigger background parsing.
    - *Boundary:* Receives `GDocImportRequest`, calls `read_google_doc()`, delegates to `process_resume_background()`.

3.  **The Extraction Service (`services/google_docs.py`)**
    - *Responsibility:* Read plain text from a Google Doc via the Docs API.
    - *Boundary:* Takes a `document_id`, returns a string. Handles OAuth credential refresh.

4.  **The Parser (`ResumeParserAgent`)**
    - *Responsibility:* Convert plain text to JSON Resume format.
    - *Boundary:* Same agent used for PDF uploads — format-agnostic text-to-JSON conversion.

#### Export Path

1.  **The API Endpoint (`POST /api/resumes/export-gdoc/{job_id}`)**
    - *Responsibility:* Fetch latest tailored resume, format it, create/update Google Doc, return
      structured result with per-field tracking.
    - *Returns:* `ExportResultResponse` with status (success/partial/failed/no_changes), URL, path,
      summary (total/applied/skipped counts), and list of skipped fields with failure reasons.

2.  **The Doc Builder (`services/google_docs.py`)**
    - *Responsibility:* Create Google Docs with formatted resume content in company subfolders.
      Returns `ExportResult` with per-field tracking and verification status.

### Data Contracts

#### Import Request
```json
{
  "document_id": "1abc..."  // Google Doc ID extracted from URL
}
```

#### Import Response
```json
{
  "status": "processing",
  "message": "Parsing Google Doc content..."
}
```

The frontend polls `GET /api/resumes/master` until the response has `fullName` (indicating parsing is complete) or `status: "error"`.

### System State Transition
- **Before (Import):** No master resume, or an outdated one from a previous PDF upload.
- **After (Import):** Fresh master resume parsed from Google Doc, ready for tailoring.
- **Before (Export):** Tailored resume exists only in Supabase.
- **After (Export):** Tailored resume is also available as a shareable Google Doc.

## 3. Implementation Details

### 1. Document Reading (`services/google_docs.py::read_google_doc`)
Uses the Google Docs API v1 to read document content.

**Key Implementation Details:**
- **Authentication:** Reuses existing OAuth2 flow via `get_credentials()`. Scopes already include `documents` and `drive`.
- **Text Extraction:** Traverses `doc.body.content[].paragraph.elements[].textRun.content` and concatenates all text runs. Returns plain text (no formatting preserved — the LLM parser handles structure detection).
- **Credential Caching:** Token cached in `google-token.json`, auto-refreshes on expiry. If refresh fails (revoked/expired grant), `get_credentials()` deletes the stale token and raises `ValueError` — caller must re-authenticate via terminal OAuth flow.

### 2. Document ID Extraction (Frontend)
The frontend extracts the document ID from a pasted URL using regex:
```typescript
function extractGoogleDocId(input: string): string {
    const match = input.match(/\/d\/([a-zA-Z0-9_-]+)/);
    return match ? match[1] : input; // If no match, assume raw ID
}
```

### 3. API Endpoint (`api/routes/resumes.py::import_from_google_doc`)
- Accepts `GDocImportRequest` (Pydantic model with `document_id: str`)
- Calls `read_google_doc()` to extract text
- Saves immediate `{"status": "processing"}` to DB so frontend can start polling
- Delegates to `process_resume_background()` as a FastAPI `BackgroundTask`
- Same downstream path as PDF upload — `ResumeParserAgent` → `save_resume(is_master=True)`

### 4. Document Export (`services/google_docs.py::create_tailored_resume_doc`)

Two export paths (selected via presence of `GOOGLE_BASE_RESUME_DOC_ID`):

#### Path A: Copy-and-Fill (Formatting Preserved) — When `GOOGLE_BASE_RESUME_DOC_ID` is set

Three-stage pipeline with per-field tracking and verification (ADR-0018 + Lesson #18):

**Stage 1 — Build & Pre-flight Gate:**
- `_build_gdoc_replacements(gdoc_paragraphs, base_data, tailored_data)` returns `(replacements, insertions, field_results)`.
  - Improved matching: normalize text (strip bullets, collapse whitespace, normalize smart quotes),
    try exact prefix match (first 40 chars) before fuzzy overlap, consumed tracking (prevents
    double-matching), threshold raised to 0.6 with 2x length guard.
  - Each field tracked in `ExportFieldResult` with section path, action, status, and failure reason.
- Pre-flight gate: if `matched / total_changed < 0.5`, delete the copy and skip to Path B (Tier 3).

**Stage 2 — Apply Mutations:**
- `_build_replace_requests(replacements)` converts to Docs API `replaceAllText` requests.
- `_apply_insertions()` inserts new paragraphs bottom-to-top (after fresh doc read for indices).
- Free verification: `_check_occurrences_changed()` parses batchUpdate response, marks fields with
  `occurrencesChanged: 0` as `api_no_match` (API returned 200 OK but didn't find the text).

**Stage 3 — Dual Verification & Fallback:**
- `_verify_export()` re-reads doc and confirms each "applied" field is present (exact substring or
  word overlap ≥ 0.8). Updates failed fields to `verification_failed`.
- If verification < 80% applied: Tier 2 fallback — `_append_missed_changes()` appends a
  demarcated "--- Changes not auto-applied ---" section at doc bottom listing missed fields with
  section labels so user can manually place them.

**Safety Guards:**
- Skills format compatibility: if base uses structured categories but tailored uses bare keywords,
  skills replacement is skipped.
- Apostrophe escaping: single quotes in folder/doc names are escaped in Drive API queries.
- Smart quote normalization: `'` → `'`, `"` → `"` (Lesson #18).

**Folder Structure:** `OtooCV / <Company Name> / <Resume Doc>`

**Replace Logic:** If a doc with the same title already exists, delete it and create a fresh copy.

**Benefit:** Exported doc inherits all formatting from the base GDoc — fonts, styles, layout preserved.

**Return Type:** `ExportResult` with status (`success | partial | failed | no_changes`), summary counts,
and list of skipped fields with reasons. API returns structured `ExportResultResponse` to frontend.

#### Path B: Plain-Text Insert (Default) — When `GOOGLE_BASE_RESUME_DOC_ID` is not set
- **Mechanism:** Create a blank Google Doc and insert resume content as plain text via `insertText` batchUpdate.
- **Content Format:** Plain text via `_build_resume_text()` — sections, bullets, contact info
- **Folder Structure:** `OtooCV / <Company Name> / <Resume Doc>`
- **Replace Logic:** If a doc with the same title exists in the company folder, its content is cleared and replaced (not duplicated)
- **Limitation:** No formatting inheritance — all docs look the same regardless of base template.

### 5. Frontend Integration (`glassresumatch-ai/pages/SetupPage.tsx`)

**Onboarding Mode** (isOnboarding=true):
- Two equal tiles: "Upload file" (PDF/DOCX) and "Google Doc" (paste URL)
- Clicking "Google Doc" tile expands an input panel below
- User pastes Google Docs URL; regex validates format (`extractDocId()`)
- On error: inline red text "That doesn't look like a Google Docs URL"
- On success: transition to uploading block (spinner + "Pulling your doc…")
- Polling: calls `apiClient.getMasterResume()` every 2s until status changes / timeout (60s)
- On complete: navigate to `/` (or call `onComplete` callback)

**Settings Mode** (isOnboarding=false):
- Two compact pill buttons: "Upload file" and "Google Doc"
- Same expand/input/import flow as onboarding
- On complete: show Toast "CV updated. You're good to go." + revert to idle state
- Settings persist locally (no page reload needed)

### System State Transition
- **Before:** `services/google_docs.py` only had export functions (`create_tailored_resume_doc`, `_build_resume_text`).
- **After:** Added `read_google_doc()` for import. Bidirectional Google Docs integration complete.
