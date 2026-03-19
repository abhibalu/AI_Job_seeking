# ADR-0009 — SSE over WebSocket + polling consolidation

**Date**: 2026-03-19
**Status**: Accepted

## Context
The OotoCV spec uses SSE for run progress streaming and WebSocket for cron completion notifications — two different protocols for the same communication direction (server → client). The current TailorAI system uses neither: it relies on `BackgroundTasks` + polling via `GET /api/tasks/{task_id}`. Both the split-protocol spec design and the existing polling approach need to be resolved before any real-time UI is built.

## Decision
Use SSE exclusively for all server→client push (run progress + cron completion). Retire BackgroundTask polling entirely. Single endpoint: `GET /events/stream`, session-scoped, with typed event names (`event: progress`, `event: run_complete`).

## Reasoning
SSE is unidirectional (server→client only), which is all this product needs. WebSocket is bidirectional — adding it for one-way messages introduces unnecessary complexity, a more involved handshake, and additional proxy/firewall concerns. SSE works over HTTP/1.1, reconnects automatically via the EventSource API, and is simpler to implement and test than WebSocket. Since neither protocol is built yet, consolidating now costs nothing.

## Alternatives Considered
- **WebSocket for everything**: Rejected because the product has no client→server real-time messages. Bidirectional overhead with no benefit.
- **SSE (spec) + WebSocket (cron)**: Rejected because running two push protocols for the same direction is unnecessary complexity. The spec split appeared to be an oversight, not a deliberate tradeoff.
- **Keep polling**: Rejected because it creates load on the API and produces laggy UX. Polling also complicates the UI with retry logic that SSE's EventSource handles natively.

## Consequences
**Positive**:
- Single reconnect handler for all server push events
- No WebSocket handshake overhead
- Works transparently through HTTP proxies and load balancers
- `apiClient.ts` polling code can be deleted entirely

**Negative / Trade-offs**:
- SSE is one-way; if a future feature needs client→server real-time messaging (e.g., collaborative editing), we'd need to add WebSocket or long-polling alongside SSE
- Engineers familiar with WebSocket may need orientation

## Do Not Revisit Unless
Product requires client→server real-time messaging (e.g., collaborative resume editing, live cursor sharing). Measure that need before adding WebSocket.
