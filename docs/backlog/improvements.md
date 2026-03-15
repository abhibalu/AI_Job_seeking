# TailorAI - Technical Review & Proposed Improvements

*Note: These are logical questions and potential improvements for the multi-agent tailoring and Google Docs export features. No code has been modified.*

## 1. Multi-Agent Tailoring Subgraph
### Implementation Analysis & Questions
- **Context Handling**: The `jd_context` safely structures "must-haves", "ats_keywords", and "strategic_gaps". This is excellent for keeping the LLM focused.
- **JSON Parsing**: The Critic model might struggle to return pure JSON arrays. You implemented a fallback `_parse_json_response` which handles strings wrapped in markdown, which is a great failsafe.
- **Concurrency**: `subgraph.invoke` is called inside `run_in_threadpool`. For very large LLM generation steps, this might consume thread pool capacity on the backend if under high load.

### Proposed Improvements
- [ ] **Dynamic MAX_REVISIONS**: Instead of hardcoding `MAX_REVISIONS = 2`, this could be a configuration variable or dynamic based on the user's tier. 
- [ ] **Streaming Status**: Currently, the UI just shows a generic loading state. Because LangGraph is stateful, we could expose a WebSocket or long-polling endpoint to emit events ("Drafting...", "Critiquing...", "Revising...") to make the UI feel faster.
- [ ] **JSON Mode Enforcement**: You noted that `BaseAgent` relies entirely on prompt engineering ("Return VALID JSON"). If adopting a model that supports strict structured outputs (like `gpt-4o` or `gpt-4o-mini`), configuring `response_format={ "type": "json_object" }` natively via the provider API will prevent breaking JSON parsing downstream.
- [ ] **Cost / Langfuse Tracking**: Since `ResumeTailorAgent` is now looping, a single "Tailor" click could trigger 3+ LLM API calls. Ensure Langfuse trace wrappers are properly nesting these Subgraph calls so cost tracking is accurate.

## 2. Google Docs Export
### Implementation Analysis & Questions
- **OAuth Scope**: Using `https://www.googleapis.com/auth/documents` and `https://www.googleapis.com/auth/drive` is correct for reading/writing docs.
- **Replace Logic**: The replacement logic (`deleteContentRange`) deletes indexing from 1 to `endIndex`. This elegantly avoids Google Drive clutter without losing the user's previously shared URL!

### Proposed Improvements
- [ ] **HTML to Google Docs Formatting**: Currently, `_build_resume_text` dumps plain, unstyled text. We could leverage the Google Docs markup requests (`updateTextStyle`, `updateParagraphStyle`) to bold headers ("WORK EXPERIENCE"), italicize roles, or inject standard resume margins.
- [ ] **Token Expiration Handling**: If the API throws a `RefreshError` mid-request, it currently fails out to HTTP 500. A retry-wrap with an explicit token refresh call might make it more resilient.
- [ ] **Template Cloning instead of Scratch Generation**: Instead of injecting raw text, another powerful approach is copying a stylized "Master Template" Doc (`drive_service.files().copy(...)`) and then using `replaceAllText` requests to swap `{{FULL_NAME}}`, `{{EXPERIENCE}}`, etc. This allows non-developers to edit the resume's visual layout in Google Docs without touching Python code!

## 3. Frontend (TailorReview)
### Proposed Improvements
- [ ] **Diff View Stability**: In `TailorReview.tsx`, `skills` are normalized back to strings before being sent to `ResumePreview`. If `baseResume` skills are structured differently than `tailoredResume`, the diff checker might flag every line as changed. Ensuring uniform schemas across both endpoints prevents visual diff clutter.

## 4. Proposed Architecture: The "Pre-flight" Tailoring Pipeline
The current resume tailoring process suffers from a "black box" effect. Relying on a single "Conservative Editor" prompt to decide *what* to change and *how* to write it simultaneously leads to unpredictable reliability.

We propose a multi-step approach to solve this:

### 4.1 Step 1: The Strategist Agent (New Subagent)
Instead of jumping straight into editing JSON, we introduce a **Strategist Subagent**. We will heavily leverage the outputs from your **existing subagents**:
- **Input 1 (Base Data):** Base Resume and `approved_skills`.
- **Input 2 (From `JDParserAgent`):** `ats_keywords`, `must_haves`.
- **Input 3 (From `JobEvaluatorAgent`):** `missing_keywords`, `gaps`.
- **Task:** Create an explicit action plan. It cross-references the missing keywords identified by the Evaluator with the Approved Skills, and decides exactly which nodes/bullets to target.
- **Output (`tailoring_plan.json`):**
  ```json
  [
    {
      "target_section": "work",
      "target_id": "exp-123",
      "action": "rewrite_bullet",
      "bullet_index": 2,
      "reason": "Missing required keyword 'Python'. Current bullet mentions 'Java'.",
      "instruction": "Rewrite to emphasize the Python migration handled in Q3."
    }
  ]
  ```

### 4.2 Step 2: The Executor Agent (Refactored `ResumeTailorAgent`)
- **Input:** Base Resume, `tailoring_plan.json`.
- **Task:** Act as a precise executor. It takes the array of planned changes and applies them EXACTly as instructed. 
- **Output:** The mutated Resume JSON, plus the mapped `changes` array (saving the "Before" text, "After" text, and the "Reason").

### 4.3 Step 3: Frontend Data Model Shift (The "Explainable Diff")
Instead of the frontend trying to compute a text diff between `baseResume` and `tailoredResume`, the backend will explicitly send the `changes` array alongside the final resume.
- **UI Impact:** A dedicated UI panel can state exactly why a section changed (e.g., *"Changed Bullet 3 Because: Added ATS Keyword 'Azure Data Factory'."*). This solves the explainability problem instantly.

### 4.4 Prompt Management (Langfuse)
- **Action:** Migrate `agent_prompts/resume_tailor.md` and the new Strategist prompt into Langfuse Prompt Management.
- **Benefit:** Iterate on the prompt via the Langfuse Dashboard in production without deploying code, immediately seeing the impact on tailoring reliability.
