# Level 3 (Implementation): Actor-Critic Tailoring Loop

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

### 1. The Orchestrator (`agents/tailoring_subgraph.py`)
The sub-graph utilizes **LangGraph** to manage the state machine. 

**Key Implementation Details:**
- **State Partitioning:** The node `node_save` explicitly filters out keys starting with `_` to ensure backend metadata (like `_critique`) doesn't pollute the final resume JSON.
- **Safety Cap:** The `route_critique` function implements a recursive loop back to `draft` if flaws exist, but enforces an exit to `save` once `MAX_REVISIONS = 2` is reached to prevent cost overruns.

> [!NOTE]
> **Production Status:** **Active**. This is the heart of the resume generation engine.

### 2. The Actor (`agents/resume_tailor.py`)
The `ResumeTailorAgent` implements a "Conservative Editor" strategy through its system prompt (`agent_prompts/resume_tailor.md`).

**Key Implementation Details:**
- **Prompt Injection:** The `critique` from previous iterations is injected via the `build_user_prompt` method under an `### CRITIQUE TO ADDRESS (URGENT)` header, giving it high weight in the LLM's attention.
- **Structural Integrity:** The agent is explicitly forbidden from changing resume IDs or total bullet counts to ensure the UI can still map the results correctly.

> [!NOTE]
> **Production Status:** **Active**.

### 3. The Critic (`agents/resume_critic.py`)
The `ResumeCriticAgent` uses a specialized parsing method `_parse_json_response` to extract a list of strings from the LLM response.

**Key Implementation Details:**
- **Hallucination Detection:** The critic is specifically prompted to cross-reference the draft against the `approved_skills` source of truth.
- **Fallback Logic:** If the LLM fails to return a JSON array, the `_parse_json_response` method captures the raw text as a single critique item rather than crashing the graph.

> [!NOTE]
> **Production Status:** **Active**.

## System State Transition
- **Before:** The system calls `build_tailoring_subgraph().compile()`.
- **After:** The `save` node executes `agents.database::save_tailored_resume()`, returning the new `record_id` (Supabase UUID) back to the parent graph.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
