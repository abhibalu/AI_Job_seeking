"""
LangGraph Orchestrator for TailorAI.

Defines the core state machine for evaluating, parsing, and tailoring job applications.
Routes each job through a 3-path flow based on the LLM's recommended_action:
- 'skip': End immediately (poor fit).
- 'apply': End immediately + notify (base resume is already a strong match).
- 'tailor': Parse JD -> Tailor Resume -> Notify (base resume needs tweaks).
"""
import logging
from typing import TypedDict, Annotated, Literal

from langgraph.graph import StateGraph, START, END

from agents.job_evaluator import JobEvaluatorAgent
from agents.jd_parser import JDParserAgent
from agents.tailoring_subgraph import build_tailoring_subgraph
from services.telegram_notifier import notify_high_match
from agents.database import get_master_resume
from pathlib import Path

logger = logging.getLogger(__name__)


# 1. State Definition
class JobApplicationState(TypedDict):
    job_id: str
    job_details: dict         # {title, company_name, description_text, job_url, etc.}
    evaluation: dict          # Output from JobEvaluatorAgent
    parsed_jd: dict           # Output from JDParserAgent
    tailored_resume_id: str   # Supabase ID of the generated resume (if tailored)
    status: str               # Current stage of processing
    errors: list[str]


# 2. Nodes (The Actors)
def node_evaluate(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Evaluating job {state['job_id']}")
    agent = JobEvaluatorAgent()
    d = state["job_details"]
    try:
        result = agent.run(
            job_id=state["job_id"],
            description_text=d.get("description_text", ""),
            company_name=d.get("company_name", "Unknown"),
            title=d.get("title", "Unknown"),
            job_url=d.get("job_url", "Unknown"),
        )
        return {"evaluation": result, "status": "evaluated"}
    except Exception as e:
        logger.error(f"[Graph] Evaluation failed: {e}")
        return {"errors": [f"Evaluation failed: {str(e)}"], "status": "error"}


def node_parse(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Parsing JD for job {state['job_id']}")
    agent = JDParserAgent()
    try:
        result = agent.run(
            job_id=state["job_id"],
            description_text=state["job_details"].get("description_text", ""),
        )
        # Also save parsed JD to the database for dashboard compatibility
        try:
            from agents.database import save_jd_parsed
            save_jd_parsed(result)
        except Exception as e:
            logger.warning(f"[Graph] Failed to save parsed JD to DB: {e}")
        return {"parsed_jd": result, "status": "parsed"}
    except Exception as e:
        logger.error(f"[Graph] JD Parsing failed: {e}")
        return {"errors": [f"JD Parse failed: {str(e)}"], "status": "error"}


def node_tailor(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Launching Tailoring Sub-Graph for job {state['job_id']}")
    
    parsed_jd = state.get("parsed_jd", {})
    jd_context = {
        "role": state["job_details"].get("title", "Unknown"),
        "company": state["job_details"].get("company_name", "Unknown"),
        "summary": state["evaluation"].get("summary", ""),
        "must_haves": parsed_jd.get("must_haves", []),
        "ats_keywords": parsed_jd.get("ats_keywords", []),
        "strategic_gaps": state["evaluation"].get("gaps", {}),
        "improvement_suggestions": state["evaluation"].get("improvement_suggestions", []),
    }
    
    try:
        # Load necessary ground-truth data from DB to feed the subgraph
        base_resume = get_master_resume()
        
        # Load approved skills
        approved_skills = ""
        skills_path = Path("agent_prompts/approved_skills.md")
        if skills_path.exists():
            with open(skills_path) as f:
                approved_skills = f.read()
                
        if not base_resume:
            raise Exception("No master resume found in DB")
            
        initial_subgraph_state = {
            "job_id": state["job_id"],
            "base_resume": base_resume,
            "jd_context": jd_context,
            "approved_skills": approved_skills,
            "revision_count": 0,
            "critique": [],
        }
        
        # Compile and invoke the subgraph
        subgraph = build_tailoring_subgraph().compile()
        logger.info(f"[Graph] Sub-graph compiled, invoking...")
        
        # We don't need a dedicated checkpointer here because the top-level 
        # graph's checkpointer will persist the overarching state.
        final_sub_state = subgraph.invoke(initial_subgraph_state)
        
        if final_sub_state.get("errors"):
            raise Exception("; ".join(final_sub_state["errors"]))
            
        record_id = final_sub_state.get("final_resume_id")
        if not record_id:
            raise Exception("Tailoring subgraph returned no final_resume_id")
            
        return {"tailored_resume_id": record_id, "status": "tailored"}
        
    except Exception as e:
        logger.error(f"[Graph] Tailoring Sub-Graph failed: {e}", exc_info=True)
        return {"errors": [f"Tailoring Sub-Graph failed: {str(e)}"], "status": "error"}


def node_notify_apply(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Notifying apply for job {state['job_id']}")
    eval_res = state["evaluation"]
    notify_high_match(
        company=state["job_details"].get("company_name", "Unknown"),
        title=state["job_details"].get("title", "Unknown"),
        score=eval_res.get("job_match_score", 0),
        job_id=state["job_id"],
        action="apply",
    )
    return {"status": "notified_apply"}


def node_notify_tailored(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Notifying tailored for job {state['job_id']}")
    eval_res = state["evaluation"]
    # Send a notification that tailoring is complete
    notify_high_match(
        company=state["job_details"].get("company_name", "Unknown"),
        title=state["job_details"].get("title", "Unknown"),
        score=eval_res.get("job_match_score", 0),
        job_id=state["job_id"],
        action="review_tailored", # custom action for tailored resumes
    )
    return {"status": "notified_tailored"}


# 3. Routing Logic
def route_after_evaluation(state: JobApplicationState) -> Literal["skip", "apply", "tailor", "error"]:
    if state.get("errors"):
        return "error"
        
    action = state["evaluation"].get("recommended_action", "skip").lower()
    
    if action == "apply":
        return "apply"
    elif action == "tailor":
        return "tailor"
        
    return "skip"


def build_pipeline_graph() -> StateGraph:
    """Constructs and returns the LangGraph State machine for the job pipeline."""
    workflow = StateGraph(JobApplicationState)

    # Add Nodes
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("parse", node_parse)
    workflow.add_node("tailor", node_tailor)
    workflow.add_node("notify_apply", node_notify_apply)
    workflow.add_node("notify_tailored", node_notify_tailored)

    # Define Control Flow
    workflow.add_edge(START, "evaluate")
    
    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluation,
        {
            "skip": END,
            "apply": "notify_apply",
            "tailor": "parse",
            "error": END, # Abort on evaluation error
        }
    )

    def route_after_parse(state: JobApplicationState) -> str:
        if state.get("errors"):
            return "error"
        return "tailor"

    workflow.add_conditional_edges(
        "parse",
        route_after_parse,
        {
            "tailor": "tailor",
            "error": END,
        }
    )
    workflow.add_edge("tailor", "notify_tailored")
    workflow.add_edge("notify_apply", END)
    workflow.add_edge("notify_tailored", END)

    return workflow
