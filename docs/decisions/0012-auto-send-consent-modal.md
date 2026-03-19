# ADR-0012 — auto_send requires an explicit consent modal

**Date**: 2026-03-19
**Status**: Accepted

## Context
The OotoCV spec includes an `auto_send_threshold` slider (0–4) that, when set above 0, enables the system to submit CVs to employers without explicit user review. The slider alone is not a sufficient consent mechanism: a user could accidentally drag it, not fully read the label, or forget they enabled it. This directly contradicts the product's core promise — "nothing leaves the system without an explicit user action."

## Decision
Moving the `auto_send_threshold` slider above 0 triggers a modal requiring explicit confirmation before the setting is saved. The slider alone is not consent. After confirmation, a persistent amber indicator in the feed header displays the active mode ("Auto-send ON · 3+") for the lifetime of the setting.

## Reasoning
Auto-send is the highest-trust action in the system — it submits job applications on behalf of the user. Consent for this must be unambiguous and deliberate. A slider is a continuous control designed for gradual adjustment, not a confirmation gesture. The modal forces a deliberate read-and-confirm moment. The persistent header indicator ensures users are never surprised that auto-send is active in a later session.

## Alternatives Considered
- **Slider only with confirmation tooltip**: Rejected because tooltips are easily missed and don't require acknowledgment.
- **Checkbox consent at onboarding**: Rejected because users configure this in Settings after onboarding; the consent moment must be co-located with the action.
- **Slider with debounced save (no modal)**: Rejected because it provides no explicit confirmation moment and fails the "deliberate action" test.

## Consequences
**Positive**:
- Users cannot accidentally enable auto-send
- Persistent indicator prevents "I forgot I turned that on" support cases
- Matches the product's explicit trust architecture

**Negative / Trade-offs**:
- Additional friction in Settings for users who deliberately want to enable auto-send (one extra click)
- Modal must be written with clear, non-alarming copy that explains the feature without scaring users away from it

## Do Not Revisit Unless
User research (A/B test) shows the modal is causing measurable abandonment of the auto-send feature specifically — not just friction in Settings generally.
