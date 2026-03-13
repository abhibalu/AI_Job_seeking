import logging
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, START, END

from agents.resume_tailor import ResumeTailorAgent
from agents.resume_critic import ResumeCriticAgent
from agents.resume_validator import validate_structure

logger = logging.getLogger(__name__)

# 1. Sub-Graph State Definition
class TailoringState(TypedDict):
    job_id: str
    base_resume: dict
    jd_context: dict
    approved_skills: str
    draft_resume: dict        # The current working draft
    critique: list[str]       # Feedback from the Critic Agent
    revision_count: int       # Prevents infinite loops
    final_resume_id: str      # Supabase ID of the finalized resume
    status: str
    errors: list[str]


# 2. Sub-Graph Nodes
def node_draft(state: TailoringState) -> dict:
    """The Actor creates or revises the resume draft."""
    logger.info(f"[SubGraph] Drafting resume for job {state['job_id']} (Revision {state.get('revision_count', 0)})")
    
    agent = ResumeTailorAgent()
    try:
        # Pass critique to the prompt if this is a revision pass
        critique_context = "\n".join(state.get("critique", []))
        
        result = agent.run(
            base_resume=state["base_resume"],
            jd_context=state["jd_context"],
            approved_skills=state["approved_skills"],
            critique=critique_context # We will need to update ResumeTailorAgent.build_user_prompt to accept this
        )
        
        # When agent.run returns, it's a dict containing the drafted resume.
        return {
            "draft_resume": result,
            "revision_count": state.get("revision_count", 0) + 1,
            "status": "drafted"
        }
    except Exception as e:
        logger.error(f"[SubGraph] Drafting failed: {e}", exc_info=True)
        return {"errors": [f"Drafting failed: {str(e)}"], "status": "error"}


def node_validate(state: TailoringState) -> dict:
    """Programmatic structural validation — no LLM call needed."""
    logger.info(f"[SubGraph] Validating draft structure for job {state['job_id']}")

    violations = validate_structure(state["base_resume"], state["draft_resume"])
    if violations:
        logger.warning(f"[SubGraph] Structural violations found: {violations}")
    else:
        logger.info("[SubGraph] Draft passed structural validation.")

    return {"critique": violations, "status": "validated"}


def route_validate(state: TailoringState) -> Literal["critique", "revise", "error"]:
    """Route after validation: if structural issues, skip critic and revise directly."""
    if state.get("errors"):
        return "error"

    critique = state.get("critique", [])
    revision_count = state.get("revision_count", 0)
    MAX_REVISIONS = 2

    if not critique:
        # Structurally valid — proceed to LLM critic for content review
        return "critique"
    elif revision_count >= MAX_REVISIONS:
        # Can't revise further — let it through to critic anyway
        logger.warning("[SubGraph] Structural issues persist at max revisions. Proceeding to critic.")
        return "critique"
    else:
        # Structural issues found — send back to draft without wasting a critic LLM call
        return "revise"


def node_critique(state: TailoringState) -> dict:
    """The Critic reviews the draft against the JD limits and approved skills."""
    logger.info(f"[SubGraph] Critiquing draft for job {state['job_id']}")
    
    agent = ResumeCriticAgent()
    try:
        critique_list = agent.run(
            draft_resume=state["draft_resume"],
            jd_context=state["jd_context"],
            approved_skills=state["approved_skills"]
        )
        
        return {
            "critique": critique_list,
            "status": "critiqued"
        }
    except Exception as e:
        logger.error(f"[SubGraph] Critiquing failed: {e}", exc_info=True)
        return {"errors": [f"Critiquing failed: {str(e)}"], "status": "error"}


def node_save(state: TailoringState) -> dict:
    """Saves the final approved draft to the database."""
    logger.info(f"[SubGraph] Saving final tailored resume to DB for job {state['job_id']}")
    
    from agents.database import save_tailored_resume
    
    try:
        final_resume = state["draft_resume"]
        # Strip backend metadata from the resume JSON
        clean_resume = {k: v for k, v in final_resume.items() if not k.startswith('_')}

        # Differentiate force-saved (unresolved flaws) from critic-approved
        is_force_save = bool(state.get("critique", []))
        save_status = "needs_review" if is_force_save else "pending"
        if is_force_save:
            logger.info(f"[SubGraph] Force-saving with status='needs_review' ({len(state['critique'])} unresolved flaws)")

        record_id = save_tailored_resume(
            job_id=state["job_id"],
            version=state.get("revision_count", 0),
            content=clean_resume,
            status=save_status
        )
        return {
            "final_resume_id": record_id,
            "status": "saved"
        }
    except Exception as e:
        logger.error(f"[SubGraph] Saving failed: {e}", exc_info=True)
        return {"errors": [f"Saving failed: {str(e)}"], "status": "error"}


# 3. Routing Logic
def route_critique(state: TailoringState) -> Literal["revise", "save", "error"]:
    if state.get("errors"):
        return "error"
        
    critique = state.get("critique", [])
    revision_count = state.get("revision_count", 0)
    MAX_REVISIONS = 2
    
    if not critique:
        logger.info(f"[SubGraph] Critic approved draft (0 flaws). Routing to save.")
        return "save"
    elif revision_count >= MAX_REVISIONS:
        logger.warning(f"[SubGraph] Max revisions ({MAX_REVISIONS}) reached. Forcing save despite {len(critique)} flaws.")
        return "save"
    else:
        logger.info(f"[SubGraph] Critic found {len(critique)} flaws. Routing back to draft.")
        return "revise"


# 4. Build the Sub-Graph
def build_tailoring_subgraph() -> StateGraph:
    workflow = StateGraph(TailoringState)
    
    workflow.add_node("draft", node_draft)
    workflow.add_node("validate", node_validate)
    workflow.add_node("critique", node_critique)
    workflow.add_node("save", node_save)

    # Flow: draft → validate → (critique or revise) → ...
    workflow.add_edge(START, "draft")
    workflow.add_edge("draft", "validate")

    workflow.add_conditional_edges(
        "validate",
        route_validate,
        {
            "critique": "critique",
            "revise": "draft",
            "error": END,
        }
    )

    workflow.add_conditional_edges(
        "critique",
        route_critique,
        {
            "revise": "draft",
            "save": "save",
            "error": END,
        }
    )

    workflow.add_edge("save", END)
    
    return workflow
