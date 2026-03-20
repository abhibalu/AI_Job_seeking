# ADR-0011 — Cover letter editable from day one (not read-only in v1)

**Date**: 2026-03-19
**Status**: Accepted

## Context
The OotoCV spec describes the cover letter preview as read-only in v1, with editing deferred to a future version. An independent critique flagged this as a product regression: an AI-generated cover letter that cannot be edited is strictly worse than writing your own, because the user is stuck with output they may not agree with and cannot submit it with confidence.

## Decision
Cover letter generation ships with an editable `<textarea>` pre-filled with the AI output, not a read-only preview. Users can edit before saving. The textarea saves on blur via `PATCH /jobs/:id/cover_letter`. Read-only CL is not a valid v1 state.

## Reasoning
The cover letter is the most visible output to employers. If users cannot edit it, they face a binary choice: submit AI text they don't fully own, or do the whole thing manually outside the app — defeating the purpose of the feature. An editable textarea is a simpler component than a read-only preview with an "edit in v2" promise, so this decision actually reduces scope. Cover letter quality will improve over time with the voice system; editability is the safety net that makes it usable before quality is perfect.

## Alternatives Considered
- **Read-only in v1 (original spec decision)**: Rejected because it forces users to accept AI output or abandon the feature. Trust-breaking for a high-stakes document.
- **Optional edit mode (toggle)**: Rejected as unnecessary complexity. Editable by default is simpler and always more capable.
- **No cover letter in v1**: Rejected because it was already in scope. Removing it would be a larger cut than making it editable.

## Consequences
**Positive**:
- Users can refine output → better applications → retention signal
- Simpler component (textarea) vs read-only preview
- Builds trust in AI output when users can verify and correct

**Negative / Trade-offs**:
- Adds LLM costs (new agent or temperature-controlled call from ResumeTailorAgent)
- New agent prompt to maintain (`agent_prompts/cover_letter.md`)
- New DB field + API endpoint (`cover_letter` on tailoring output, `PATCH /jobs/:id/cover_letter`)

## Do Not Revisit Unless
CL quality is measurably so good that editing is statistically never used (A/B test with edit rate near zero). Even then, editability is cheap to keep.
