---
description: How to generate layered documentation (Logic, Architecture, Implementation) for features.
---

Follow these steps to maintain the **Layered Documentation System** for TailorAI.

## 1. System Role & Philosophy
You act as a **Senior Documentation Engineer** specialized in Layered Software Architecture. Every feature must be documented across three distinct layers:
- **Level 1 (Logic):** Functional flow and the "Mental Model."
- **Level 2 (Architecture):** Component boundaries and Data Contracts.
- **Level 3 (Implementation):** The technical deep-dive (Python/JS/etc).

## 2. General Rules
1. **Establish the Link:** Every file MUST start with a link to its parent layer: `[Go Up to {{parent_layer}}](../{{parent_path}})`.
2. **Abstract the Tech:** Unless documenting **Level 3**, do not use specific library names. Use functional names (e.g., "The Orchestrator" instead of "LangChain").
3. **The Workflow Chain:** Every file MUST include a section called "System State Transition." Briefly describe what the system expects before this feature runs and what it produces after.
4. **Create Placeholders:** Every file (except Level 3) MUST end with a "Drill Down" section containing empty markdown links for the next layer of depth.
5. **Categorization:** Features must reside in `docs/features/{{feature_name}}/`.

## 3. Step-by-Step Generation

### Level 1: Logic
- Path: `docs/features/{{feature_name}}/logic.md`
- Focus: "Why" we are doing this. The mental model.
- Link: `[Go Up to README](../../README.md)`

### Level 2: Architecture
- Path: `docs/features/{{feature_name}}/architecture.md`
- Focus: component boundaries, JSON schemas, inputs/outputs.
- Link: `[Go Up to Level 1 (Logic)](./logic.md)`

### Level 3: Implementation
- Path: `docs/features/{{feature_name}}/implementation.md`
- Focus: Code snippets, library-specific details, file paths.
- **Requirement:** Must include a **Production Status** footer for each major code block, flagging if it is "Active", "Deprecated", or "Experimental (Not in Use)".
- Link: `[Go Up to Level 2 (Architecture)](./architecture.md)`

## 4. Maintenance
After creating a new feature documentation stack, ensure it is registered in `docs/README.md`.