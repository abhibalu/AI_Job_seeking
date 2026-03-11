# Architecture Decision: JSON Resume vs. Markdown

This document evaluates the necessity of the current *JSON Resume* schema and proposes transitioning the entire application payload to **Markdown**.

## 1. Why We Currently Use JSON
1. **Frontend Rendering:** `TailorReview.tsx` maps JSON arrays (`experience`, `education`) to distinct React components for structured rendering.
2. **Standardization:** The *JSON Resume* schema is an open-source standard, making initial PDF parsing structurally predictable for the database.
3. **Diff Checking:** It theoretically allows targeting specific JSON keys (e.g., `work[0].highlights[2]`) for exact modifications.

## 2. Why JSON is Holding Us Back
As TailorAI shifts toward Google Docs as the final output destination and primary editing interface, the friction of JSON becomes apparent:

1. **LLM Hallucinations & Syntax Errors:**
   - Forcing an LLM to output a massive 150-line JSON object is the #1 cause of tailoring failures. A single missing comma breaks the entire pipeline.
   - We had to implement complex fallback parsers (`_parse_json_response`) just to handle LLMs wrapping JSON in ````markdown```` tags.
2. **Google Docs Translation Friction:**
   - In `services/google_docs.py`, we have an entire function (`_build_resume_text`) just to translate the structured JSON back into a flat text string so Google Docs can read it.
   - JSON cannot natively store styling (bolding, italics, links). Markdown can.
3. **The "Pre-Flight" Strategist Complexity:**
   - If the Strategist Agent targets JSON nodes (`"target_area": "work[2].highlights[0]"`), the Executor Agent *still* has to reconstruct the entire JSON payload perfectly without breaking the schema.

---

## 3. The Markdown Transition Proposal
We should abandon the strict JSON Resume object entirely and treat the resume as a **Raw Markdown String** throughout the entire backend pipeline.

### 3.1 The New Pipeline
1. **Google Doc Base Resume:** Extracted directly as Markdown.
   ```markdown
   # Work Experience
   ## Software Engineer at Acme Corp (2020 - Present)
   * Led migration to Azure Data Factory.
   ```
2. **The Strategist Agent:** Reads the Markdown text. Outputs semantic instructions.
   ```json
   {
      "action": "rewrite",
      "target_section": "Software Engineer at Acme Corp",
      "instruction": "Rewrite the bullet about Azure Data Factory to include 'Python' and emphasize optimization."
   }
   ```
3. **The Executor Agent:** Receives the Markdown and the instruction. Because it is just editing text (not fighting JSON schemas), it can use a simple tool-calling pattern (or just rewrite the specific section) flawlessly.
4. **Google Docs Export (Final Output):** We are left with a beautifully formatted Markdown string. We can use a lightweight library to translate this Markdown directly into Google Docs formatting (bolding headers, bulleting lists) rather than writing a custom JSON-to-Text builder!

### 3.2 Impact on the Frontend
- **The "Diff View":** The frontend will no longer render distinct React components for "Experience" and "Education". 
- Instead, `TailorReview.tsx` will utilize a Markdown Renderer (like `react-markdown`).
- To show the "Before/After", we simply use a standard Text Diff component (like `react-diff-viewer`) comparing the Base Markdown block to the Tailored Markdown block. It is infinitely cleaner and eliminates the "Diff View Stability" bug listed in `improvements.md`.

## 4. Conclusion
If we are relying on Google Docs as the single source of truth for the Candidate's master resume, **Markdown is the most natural medium for the LLM to read, edit, and write.** 

Dropping JSON eliminates API parsing errors, simplifies the backend logic, and allows the LLMs to write more naturally formatted resumes.
