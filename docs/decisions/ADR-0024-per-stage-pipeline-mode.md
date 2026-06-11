# ADR-0024: Per-stage pipeline mode (separate from kill switches)

**Status:** Accepted (2026-06-11)

## Context

The OotoCV feed header surfaces three pills the user toggles to control
which agent stages run automatically:

```
Scrape [auto] → Evaluate [auto] → Tailor [manual]
```

These are user-facing operating modes ("am I reviewing today, or letting
the agent run?") and live in the feed, not Settings. They are **distinct
from kill switches** (ADR-0019), which are operator-facing safety toggles
for external services (OpenRouter / Apify / Google Docs).

Conflating the two would lose the user-vs-operator distinction:
- mode  = "should the agent run this stage automatically?" → no-op the cron
- kill  = "is this external service available?"            → return 503

## Decision

Three new rows in `system_config`:

| Key                       | Default  | Read by                       |
|---------------------------|----------|-------------------------------|
| `pipeline_scrape_mode`    | `auto`   | `services/scheduler.py` → scrape cron |
| `pipeline_evaluate_mode`  | `auto`   | `services/scheduler.py` → eval cron   |
| `pipeline_tailor_mode`    | `manual` | tailor auto-spawn gate                |

Values: `auto | manual`. When a cron stage is `manual`, the scheduler job
no-ops; manual triggers via `/api/scheduler/trigger/*` still work.

`pipeline_tailor_mode=auto` activates the auto-spawn path, gated by
`auto_send_threshold` (ADR-0012) — when an eval lands with
`match_score >= auto_send_threshold`, the tailoring worker is spawned.

Default `pipeline_tailor_mode=manual` prevents cost runaway from a forgotten
threshold (R7 in the spec).

Exposed via:
- `GET /api/pipeline/config` → `{scrape_mode, evaluate_mode, tailor_mode, auto_send_threshold}`
- `PATCH /api/pipeline/config` → same shape, partial updates

## Consequences

- Two-axis control: mode (user) vs kill switch (operator). Settings + logs
  must surface both with clearly different labels (R4 mitigation).
- Promotion to a dedicated `pipeline_config` table is deferred until
  per-stage scheduling overrides (e.g. different intervals per stage) become
  a requirement.
- The status line below the feed pills can be driven server-side from these
  three keys.

## Alternatives rejected

- **Conflate with kill switches** — loses the user/operator distinction;
  "I'm reviewing today" is not "the API is down".
- **New `pipeline_config` table upfront** — premature; YAGNI. Three rows in
  an existing key-value table is the smallest change that fits the design.

## See also

- ADR-0019 (service kill switches)
- ADR-0012 (auto_send_threshold consent modal)
- Migration `025_system_config_pipeline_modes.sql`
