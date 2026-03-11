# Level 3 (Implementation): Google Doc Base Resume Ingestion

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

### 1. Document Extraction (`services/google_docs.py`)
Implementation utilizes the Google APIs Client Library (`googleapiclient.discovery`). The extraction logic must traverse the `body.content` array recursively to concatenate `textRun` objects.

**Key Implementation Points:**
- **ID Extraction:** Regex is used to pull the `doc_id` from the full URL.
- **Structural Mapping:** 
    - `paragraph.elements` -> `textRun.content`
    - `listItem.vignette` -> Markdown bullet `*`
    - `textStyle.bold` -> Wrapped in `**`

### 2. Pipeline Integration
The implementation replaces the `get_master_resume()` call within `agents/database.py` with a call to the extraction service.

**Pseudo-logic:**
```python
def load_professional_context():
    doc_url = os.environ.get("BASE_RESUME_DOC_URL")
    if doc_url:
        return gdoc_service.read_base_resume(doc_url)
    return db.get_master_resume()
```

## System State Transition
- **Before:** The system is dependent on `pdfplumber` for ingestion and Supabase `jsonb` columns for retrieval.
- **After:** The system is dependent on `google-api-python-client` and executes a "Fetch-on-Demand" strategy during the initial phase of the LangGraph orchestrator.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
