# Base Resume Architecture: Transitioning to Google Docs

## 1. The Legacy Pipeline (Supabase JSON)
Currently, TailorAI relies on a structured JSON format to process the candidate's Base Resume.
- **Ingestion:** A PDF is uploaded, parsed (via `resume_parser.py` using LLM), and converted into a strict JSON schema (`{"basics": {}, "work": [], "education": [], "skills": []}`).
- **Storage:** This JSON is saved to the `resumes` table in Supabase with `status='master'`.
- **Retrieval:** `agents/database.py::get_master_resume()` fetches this exact JSON blob.
- **Consumption:** Every subagent (`JobEvaluatorAgent`, `ResumeTailorAgent`) expects this structured JSON as input.

**The Problem:** Editing the Base Resume requires building a complex frontend UI to manipulate the JSON. This is high-friction compared to just typing in a Word processor.

---

## 2. The Proposed Pipeline (Google Docs URL)
We want to rely on a single source of truth: A Google Doc owned and easily editable by the user.

### 2.1 Configuration
The user provides the URL to their master resume in the `.env` file:
```env
BASE_RESUME_DOC_URL="https://docs.google.com/document/d/1XyZ..."
```

### 2.2 Extraction Service (`services/google_docs.py`)
We already have OAuth authentication configured in `services/google_docs.py` (via `google-authentication.json` and `google-token.json`). We will add a new read method:

```python
def read_base_resume(doc_url: str) -> str:
    """Extracts raw text from the provided Google Doc URL."""
    # 1. Parse Document ID from URL
    doc_id = parse_google_doc_id(doc_url)
    
    # 2. Authenticate
    creds = get_credentials()
    docs_service = build('docs', 'v1', credentials=creds)
    
    # 3. Fetch Document
    document = docs_service.documents().get(documentId=doc_id).execute()
    
    # 4. Extract raw text from document structure
    return extract_text_from_elements(document.get('body').get('content'))
```

### 2.3 Context Injection & The Markdown Format
The Google Docs API returns a complex structural JSON (Paragraphs, TextRuns, List elements). The `read_base_resume()` function will be responsible for parsing this hierarchy and compiling it into **Markdown Format**.
- **Why Markdown?:** Markdown preserves critical structure (bullet points, headers, bold text) while remaining a flat, easily injected text format that LLMs understand perfectly. 
- The output will look exactly like a standard `.md` file (e.g., `# Header`, `* Bullet`).

### 2.4 Required Codebase Changes (Impact Analysis)
Transitioning from a strict JSON schema (`{"basics": {}, "work": []}`) to a flat Markdown string requires updates across the pipeline. This is a comprehensive list of what must change:

1. **`agents/job_evaluator.py`**
   - *Change:* Update `_load_resume()` to stop calling the database/JSON file and instead call the new `read_base_resume(<url>)`. Remove the `_normalize_resume` dict-mapping logic.
   - *Change:* Update the `build_user_prompt()` to accept the markdown string instead of dumping `json.dumps(resume, indent=2)`.

2. **`api/routes/resumes.py` (The Routing Engine)**
   - *Change:* In `tailor_resume()`, remove the database call for `get_db_master_resume()`. Replace it with fetching the markdown text.
   - *Change:* Update the `initial_state` dictionary injected into the LangGraph to pass `base_resume: str` (the markdown text) instead of a dictionary.
   - *Deprecation:* You could potentially deprecate `/master` and `/upload` endpoints entirely, as ingestion happens via Google Docs now.

3. **`agents/resume_tailor.py` & `resume_critic.py` (The Subagents)**
   - *Change:* Their system prompts currently assume `.work` and `.basics` objects exist. The prompts must be updated to expect unstructured Markdown text as the `Candidate Background`.
   - *Change:* If the Strategist Agent (Pre-Flight Plan) is implemented, it will return action plans based on Markdown Line Numbers or Headers (e.g., "Edit the second bullet under Work Experience -> Eviden") rather than JSON Array indices.

4. **`glassresumatch-ai/components/TailorReview.tsx` (The Frontend)**
   - *Change:* The UI's `ResumePreview` component currently assumes `baseResume` is a strictly typed JSON object. If you still want to show a Before/After diff view in the UI, you will either need to render Markdown diffs directly, or have the Tailoring backend cast the final markdown back into UI-consumable JSON.

## 3. Testing the Google Doc Integration
Before deploying this, we will write a script to locally verify the OAuth token can read the file:
1.  **Unit Test Auth:** Create a Python script `tests/test_gdoc_read.py` that calls `read_base_resume(<url>)`.
2.  **Verify Permissions:** Ensure the service account / OAuth token actually has read access to that specific document (it might need to be shared with the app, or the app logs in as the user).
3.  **Inspect Text Quality:** Print the extracted text to ensure bullet points and headers don't mash together into a single unreadable paragraph. Google Docs API returns a complex hierarchy (`paragraphElement`, `textRun`), so the extractor must handle newlines (`\n`) carefully.
