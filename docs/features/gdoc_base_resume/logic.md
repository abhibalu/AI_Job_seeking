# Level 1 (Logic): Google Docs Resume Integration

[Go Up to README](../../README.md)

## The Mental Model
The "Base Resume" is the single source of truth for the candidate's professional identity. This feature provides bidirectional integration with Google Docs:

- **Import**: Pull a resume from Google Docs, parse it via LLM, and save as the master resume
- **Export**: Push a tailored resume to Google Docs for final editing and sharing

Instead of treating the resume as a static file requiring a specialized editor, the system treats Google Docs as a **Collaborative Workspace** — the user maintains their resume in a familiar word processor, and the system can read from and write to it.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition (Import)** | User has a resume in Google Docs. OAuth credentials are configured. |
| **Process (Import)** | The Extractor reads plain text from the doc, the ResumeParserAgent converts it to JSON Resume format, and it's saved as the master resume. |
| **Post-Condition (Import)** | A new master resume is available for the tailoring pipeline. |
| **Pre-Condition (Export)** | A tailored resume exists for a specific job. |
| **Process (Export)** | The system creates/updates a Google Doc in the configured Drive folder with the formatted resume content. |
| **Post-Condition (Export)** | A shareable Google Doc URL is available for the user. |

## Workflow Chain

### Import Flow
1. **URL/ID Input**: User provides a Google Doc URL or document ID via the frontend.
2. **Text Extraction**: `read_google_doc()` traverses the document body, concatenating `textRun` content.
3. **AI Parsing**: `process_resume_background()` runs `ResumeParserAgent` to convert plain text to JSON Resume format.
4. **Master Save**: Parsed resume is saved as the new master resume in Supabase.

### Export Flow
1. **Trigger**: User clicks "Export to Google Docs" on a tailored resume.
2. **Folder Resolution**: System finds/creates a company subfolder in the configured Drive folder.
3. **Doc Creation**: Resume content is formatted as plain text and inserted into a new/existing Google Doc.
4. **URL Return**: The Google Doc URL is returned to the frontend.

## Drill Down
- [Level 2 (Architecture): Component Boundaries and Contracts](./architecture.md)
- [Level 3 (Implementation): Google API Integration](./implementation.md)
