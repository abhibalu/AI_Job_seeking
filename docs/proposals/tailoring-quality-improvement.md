# Tailoring Quality Improvement: Analysis & Roadmap

**Date:** 2026-03-13
**Status:** Phase 1 in progress, Phase 2 planned

## Problem Statement

The Actor-Critic tailoring loop produces inconsistent and sometimes inauthentic resumes. The pipeline infrastructure works (APIs, LangGraph, DB) — the quality issues are in the LLM-generated output itself.

Symptoms observed:
- Inconsistent results across runs for the same job
- Over-edited resumes that lose the candidate's authentic voice
- Missing ATS keyword integration despite JD parsing
- Force-saved resumes (max revisions hit) indistinguishable from approved ones

## Root Cause Analysis

### Bug: ATS Keywords Never Reach the Tailor (Critical)

Both jd_context construction sites (`api/routes/resumes.py:280` and `agents/pipeline_graph.py:84`) use `jd_parsed.get("keywords_to_include", [])` — but the JD parser outputs the field as `ats_keywords`. The tailor has been receiving an **empty list** every time. The entire "Vocabulary Source" strategy from the prompt ("Replace generic terms with ats_keywords") has been inert since the subgraph was built.

The legacy `run_tailoring()` method in `resume_tailor.py:87` uses the correct key — but this path is not used by the LangGraph subgraph.

### Temperature Mismatch

| Agent | Temperature | Role | Assessment |
|-------|------------|------|------------|
| JD Parser | 0.2 | Precise extraction | Correct |
| Job Evaluator | 0.3 | Consistent scoring | Correct |
| **Resume Tailor** | **0.7** | "Conservative editor" | Too high — prompt says "You are NOT a creative writer" but temp encourages creativity |
| **Resume Critic** | **0.7** | Strict QA reviewer | Too high — critic should be deterministic, not creative about what it catches |

### No Structural Guardrails

The tailor prompt instructs "preserve bullet counts" and "preserve IDs" but nothing enforces this. The draft goes from one LLM (tailor) to another LLM (critic) with zero deterministic validation. Structural violations can pass through both agents undetected.

### Critic Scope Too Broad

The critic tries to catch everything — missing keywords, unnatural phrasing, hallucinations, format issues — without severity levels or structured output. It would be more effective with a narrower scope (naturalness/authenticity) if structural checks were handled programmatically.

### No Quality Differentiation on Save

Force-saved resumes (max revisions reached, unresolved flaws) get `status='pending'` — identical to critic-approved resumes. No way to distinguish quality tiers.

## Phase 1: Bug Fixes & Tuning (Current)

Immediate changes that improve quality without architectural changes:

1. **Fix ATS keywords bug** — `keywords_to_include` → `ats_keywords` in both construction sites
2. **Lower temperatures** — Tailor 0.7→0.3, Critic 0.7→0.2
3. **Force-save status** — Save as `needs_review` when max revisions hit, `pending` on clean approval
4. **Structural validator** — Pure Python function checking bullet counts, IDs, sections, change ratio. Runs between draft and critique nodes.

## Phase 2: Plan-then-Execute Architecture (Next)

### The Missing Step

The current flow asks the tailor to **decide what to change AND make the changes** in a single LLM call — two cognitive tasks at once. A human would:

1. Know the base resume
2. Evaluate against JD → identify gaps, tech stack alignment
3. **Plan the specific edits** (what to change, what to preserve, why)
4. Execute the planned changes
5. Review for naturalness
6. Optionally re-evaluate the result

Step 3 doesn't exist in the current pipeline. The evaluator already produces `improvement_suggestions.resume_edits` with specific locations and suggestions — but this structured data gets dumped into `jd_context` as unstructured context.

### Proposed Flow

```
Evaluate → Parse JD → PLAN CHANGES → EXECUTE EDITS → VALIDATE → REVIEW → Save
                       (new node)     (refocused       (Python)   (refocused
                                       tailor)                     critic)
```

### Change Plan Output Format

```json
{
  "edits": [
    {
      "location": "work.metro.highlights[4]",
      "action": "rephrase",
      "current": "Built Cloud Functions API for data ingestion",
      "target": "Built serverless data ingestion pipelines using Cloud Functions",
      "reason": "JD requires AWS Lambda; Cloud Functions is closest approved equivalent",
      "source": "approved_skills.notable_projects.bnpl"
    }
  ],
  "preserve": ["work.metro.highlights[0-3]", "education.*"],
  "change_summary": "3 bullet edits, 2 skill additions. Focus: cloud terminology."
}
```

### Benefits

- **Audit trail** — The edit plan IS the "what changed and why" record
- **Constrained editor** — Tailor only touches what the plan specifies
- **Inspectable** — Plans can be reviewed before execution (or in batch)
- **Reproducible** — Same plan + same base = consistent output
- **Re-evaluation** — Run evaluator on tailored resume to measure improvement

### Re-Evaluation Loop

After tailoring, optionally re-run the evaluator on the tailored resume vs the same JD:
- Did the score improve by at least 10 points?
- Were the identified gaps addressed?
- Flag as ineffective tailoring if score didn't improve meaningfully
