# Level 2 (Architecture): Google Doc Base Resume Ingestion

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries
The feature is divided into three distinct functional boundaries to isolate external dependency risks from the internal processing logic.

1.  **The Resource Provider (External)**
    - *Responsibility:* Provides the raw document stream.
    - *Boundary:* Interfaced via OAuth2 and specific Document Identifiers.

2.  **The Extraction Service (Internal Orchestrator)**
    - *Responsibility:* Handles the bridge between the Resource Provider and the Domain Logic.
    - *Boundary:* Consumes a `Document ID`. Produces a `Normalized Text Block`.

3.  **The Consumer Agent (Domain Logic)**
    - *Responsibility:* Interprets the text for decision making.
    - *Boundary:* Agnostic to the source; expects a high-fidelity Markdown string.

## Data Contracts

### 1. Request Contract (Extraction)
The system expects a valid reference to trigger the ingestion:
```json
{
  "resource_url": "string",
  "auth_token_key": "string"
}
```

### 2. Response Contract (Normalization)
The successful extraction produces a structural payload:
```json
{
  "raw_content": "string (Markdown)",
  "metadata": {
    "last_synced": "timestamp",
    "version_id": "string"
  }
}
```

## System State Transition
- **Before:** The system identifies a `BASE_RESUME_DOC_URL` in the environment configuration but has no local record of the professional context.
- **After:** The system populates a "Context Buffer" containing the Markdown-formatted history, allowing all downstream subagents to execute without requiring database-resident JSON clusters.

## Drill Down
- [Level 3 (Implementation): Technical Deep-Dive](./implementation.md)
