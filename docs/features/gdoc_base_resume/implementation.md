# Level 3 (Implementation): Google Docs Resume Integration

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

### 1. Document Reading (`services/google_docs.py::read_google_doc`)
Uses the Google Docs API v1 to read document content.

**Key Implementation Details:**
- **Authentication:** Reuses existing OAuth2 flow via `get_credentials()`. Scopes already include `documents` and `drive`.
- **Text Extraction:** Traverses `doc.body.content[].paragraph.elements[].textRun.content` and concatenates all text runs. Returns plain text (no formatting preserved — the LLM parser handles structure detection).
- **Credential Caching:** Token cached in `google-token.json`, auto-refreshes on expiry.

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
- **Folder Structure:** `OtooCV / <Company Name> / <Resume Doc>`
- **Replace Logic:** If a doc with the same title exists in the company folder, its content is cleared and replaced (not duplicated)
- **Content Format:** Plain text via `_build_resume_text()` — sections, bullets, contact info

### 5. Frontend Integration (`App.tsx`)
- "Import Google Doc" button in the resume toolbar opens a modal
- Modal accepts URL or raw document ID
- On submit: calls `apiClient.importFromGoogleDoc(documentId)`
- Polls `apiClient.getMasterResume()` every 2s until status changes
- 60s timeout on polling

## System State Transition
- **Before:** `services/google_docs.py` only had export functions (`create_tailored_resume_doc`, `_build_resume_text`).
- **After:** Added `read_google_doc()` for import. Bidirectional Google Docs integration complete.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
