# Level 2 (Architecture): Google Docs Resume Integration

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries

### Import Path

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

### Export Path

1.  **The API Endpoint (`POST /api/resumes/export-gdoc/{job_id}`)**
    - *Responsibility:* Fetch latest tailored resume, format it, create/update Google Doc.

2.  **The Doc Builder (`services/google_docs.py`)**
    - *Responsibility:* Create Google Docs with formatted resume content in company subfolders.

## Data Contracts

### Import Request
```json
{
  "document_id": "1abc..."  // Google Doc ID extracted from URL
}
```

### Import Response
```json
{
  "status": "processing",
  "message": "Parsing Google Doc content..."
}
```

The frontend polls `GET /api/resumes/master` until the response has `fullName` (indicating parsing is complete) or `status: "error"`.

## System State Transition
- **Before (Import):** No master resume, or an outdated one from a previous PDF upload.
- **After (Import):** Fresh master resume parsed from Google Doc, ready for tailoring.
- **Before (Export):** Tailored resume exists only in Supabase.
- **After (Export):** Tailored resume is also available as a shareable Google Doc.

## Drill Down
- [Level 3 (Implementation): Technical Deep-Dive](./implementation.md)
