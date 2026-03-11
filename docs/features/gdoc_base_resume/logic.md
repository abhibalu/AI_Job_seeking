# Level 1 (Logic): Google Doc Base Resume Ingestion

[Go Up to README](../../README.md)

## The Mental Model
The "Base Resume" is the single source of truth for the candidate's professional identity. Historically, this was a static file requiring a specialized editor. This feature shifts that ownership to a live, external document. 

Instead of treating the resume as a database record, the system treats it as a **Dynamic Stream**. We disconnect the storage of the resume from the transformation logic, allowing the user to iterate on their professional history in a native word-processing environment while the system consumes the latest snapshot in real-time for tailoring.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | System has a globally configured pointer (External Reference) to a valid user-owned document. |
| **Process** | The "Extractor" fetches the raw contents, normalizes the structure into a universal text format, and prepares the "Professional Context" buffer. |
| **Post-Condition** | The internal Agent Pipeline receives a fresh, unstructured markdown payload representing the candidate's history, replacing the legacy structured JSON requirement. |

## Workflow Chain
1. **The External Reference**: The system identifies the remote location of the document.
2. **The Extraction Bridge**: A bridge is established using the user's identity to pull the raw document structure.
3. **The Semantic Normalization**: The complex document hierarchy (headers, lists, tables) is compressed into a simplified Markdown format to ensure semantic intent is preserved for the AI.
4. **Context Provision**: The resulting text is fed into the downstream Tailoring orchestrators.

## Drill Down
- [Level 2 (Architecture): Component Boundaries and Extraction Contracts](./architecture.md)
- [Level 3 (Implementation): Google API & Markdown Compilers](./implementation.md)
