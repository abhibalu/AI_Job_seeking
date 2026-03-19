import logging
import time
from contextlib import contextmanager
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from agents.change_planner import ChangePlannerAgent
from agents.resume_tailor import ResumeTailorAgent
from agents.resume_critic import ResumeCriticAgent
from agents.resume_validator import validate_structure, validate_planned_edits

logger = logging.getLogger(__name__)


@contextmanager
def _timed_node(name: str, job_id: str):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        logger.info("[SubGraph] %s complete", name, extra={
            "node": name,
            "job_id": job_id,
            "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
        })


# 1. Sub-Graph State Definition
class TailoringState(TypedDict):
    job_id: str
    base_resume: dict
    jd_context: dict
    approved_skills: str
    edit_plan: dict           # Structured plan from ChangePlanner
    draft_resume: dict        # The current working draft
    critique: list[str]       # Feedback from the Critic Agent
    revision_count: int       # Prevents infinite loops
    final_resume_id: str      # Supabase ID of the finalized resume
    status: str
    errors: list[str]


# 2. Sub-Graph Nodes
def node_plan(state: TailoringState) -> dict:
    """Plan specific edits based on JD context and approved skills."""
    logger.info(f"[SubGraph] Planning edits for job {state['job_id']}")

    agent = ChangePlannerAgent()
    with _timed_node("plan", state["job_id"]):
        try:
            edit_plan = agent.run(
                base_resume=state["base_resume"],
                jd_context=state["jd_context"],
                approved_skills=state["approved_skills"],
            )

            logger.info(f"[SubGraph] Edit plan: {len(edit_plan.get('edits', []))} edits planned")
            return {
                "edit_plan": edit_plan,
                "status": "planned"
            }
        except Exception as e:
            logger.error(f"[SubGraph] Planning failed: {e}", exc_info=True)
            return {"errors": [f"Planning failed: {str(e)}"], "status": "error"}


def node_draft(state: TailoringState) -> dict:
    """Execute the edit plan — apply planned edits to the base resume."""
    logger.info(f"[SubGraph] Executing edits for job {state['job_id']} (Revision {state.get('revision_count', 0)})")

    agent = ResumeTailorAgent()
    with _timed_node("draft", state["job_id"]):
        try:
            # Pass critique if this is a revision pass
            critique_context = "\n".join(state.get("critique", []))

            result = agent.run(
                base_resume=state["base_resume"],
                edit_plan=state.get("edit_plan", {}),
                approved_skills=state["approved_skills"],
                critique=critique_context
            )

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

    with _timed_node("validate", state["job_id"]):
        violations = validate_structure(state["base_resume"], state["draft_resume"])

        # Also check that only planned locations were modified
        plan_violations = validate_planned_edits(
            state["base_resume"], state["draft_resume"], state.get("edit_plan", {})
        )
        violations.extend(plan_violations)

        if violations:
            logger.warning(f"[SubGraph] Validation violations found: {violations}")
        else:
            logger.info("[SubGraph] Draft passed structural and plan validation.")

        return {"critique": violations, "status": "validated"}


def route_validate(state: TailoringState) -> Literal["critique", "revise", "error"]:
    """Route after validation: if structural issues, skip critic and revise directly."""
    if state.get("errors"):
        return "error"

    critique = state.get("critique", [])
    revision_count = state.get("revision_count", 0)
    MAX_REVISIONS = 2

    if not critique:
        route = "critique"
    elif revision_count >= MAX_REVISIONS:
        logger.warning("[SubGraph] Structural issues persist at max revisions. Proceeding to critic.")
        route = "critique"
    else:
        route = "revise"

    logger.info("[SubGraph] route_validate → %s", route, extra={
        "job_id": state.get("job_id"),
        "revision_count": revision_count,
        "violations": len(critique),
    })
    return route


def node_critique(state: TailoringState) -> dict:
    """The Critic reviews the draft for naturalness and authenticity."""
    logger.info(f"[SubGraph] Critiquing draft for job {state['job_id']}")

    agent = ResumeCriticAgent()
    with _timed_node("critique", state["job_id"]):
        try:
            critique_list = agent.run(
                draft_resume=state["draft_resume"],
                base_resume=state["base_resume"],
                edit_plan=state.get("edit_plan", {}),
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

    with _timed_node("save", state["job_id"]):
        try:
            final_resume = state["draft_resume"]
            # Strip backend metadata from the resume JSON
            clean_resume = {k: v for k, v in final_resume.items() if not k.startswith('_')}

            # Differentiate force-saved (unresolved flaws) from critic-approved
            is_force_save = bool(state.get("critique", []))
            save_status = "needs_review" if is_force_save else "pending"
            if is_force_save:
                logger.info(f"[SubGraph] Force-saving with status='needs_review' ({len(state['critique'])} unresolved flaws)")

            # Clean edit_plan metadata before saving
            edit_plan = state.get("edit_plan", {})
            clean_plan = {k: v for k, v in edit_plan.items() if not k.startswith('_')} if edit_plan else None

            record_id = save_tailored_resume(
                job_id=state["job_id"],
                version=state.get("revision_count", 0),
                content=clean_resume,
                status=save_status,
                edit_plan=clean_plan
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
        logger.warning("[SubGraph] route_critique → error",
                       extra={"job_id": state.get("job_id"), "errors": state.get("errors")})
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


def route_plan(state: TailoringState) -> Literal["draft", "error"]:
    """Route after planning: proceed to draft or abort on error."""
    if state.get("errors"):
        return "error"
    return "draft"


# 4. Build the Sub-Graph
def build_tailoring_subgraph() -> StateGraph:
    workflow = StateGraph(TailoringState)

    workflow.add_node("plan", node_plan)
    workflow.add_node("draft", node_draft)
    workflow.add_node("validate", node_validate)
    workflow.add_node("critique", node_critique)
    workflow.add_node("save", node_save)

    # Flow: plan → draft → validate → (critique or revise) → ...
    workflow.add_edge(START, "plan")

    workflow.add_conditional_edges(
        "plan",
        route_plan,
        {
            "draft": "draft",
            "error": END,
        }
    )

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
