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
from agents.resume_tailor import ResumeTailorAgent
from services.telegram_notifier import notify_high_match

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
        result = agent.run(state["job_details"].get("description_text", ""))
        return {"parsed_jd": result, "status": "parsed"}
    except Exception as e:
        logger.error(f"[Graph] JD Parsing failed: {e}")
        return {"errors": [f"JD Parse failed: {str(e)}"], "status": "error"}


def node_tailor(state: JobApplicationState) -> dict:
    logger.info(f"[Graph] Tailoring resume for job {state['job_id']}")
    
    # We load the base resume / approved skills from the db/files (ResumeTailorAgent does this)
    # JD Context is simplified for the tailor prompt
    jd_context = {
        "title": state["job_details"].get("title", "Unknown"),
        "company": state["job_details"].get("company_name", "Unknown"),
        "must_haves": state["parsed_jd"].get("must_haves", []),
        "keywords": state["parsed_jd"].get("keywords_to_include", []),
        "evaluation_score": state["evaluation"].get("job_match_score", 0),
        "evaluation_gaps": state["evaluation"].get("gaps", {}),
    }

    # IMPORTANT: The current ResumeTailorAgent expects specific args based on its run() signature.
    # Its `run_tailoring` method in `resume_tailor.py` takes job_id and handles DB fetching.
    # We'll use the orchestrator wrapper to avoid duplicate DB calls if possible, or just call run_tailoring.
    agent = ResumeTailorAgent()
    try:
        # We rely on the internal run_tailoring which saves to DB and returns the tailored resume ID
        record_id = agent.run_tailoring(state["job_id"])
        if not record_id:
            raise Exception("Tailoring returned no record ID")
            
        return {"tailored_resume_id": record_id, "status": "tailored"}
    except Exception as e:
        logger.error(f"[Graph] Tailoring failed: {e}")
        return {"errors": [f"Tailoring failed: {str(e)}"], "status": "error"}


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

    workflow.add_edge("parse", "tailor")
    workflow.add_edge("tailor", "notify_tailored")
    workflow.add_edge("notify_apply", END)
    workflow.add_edge("notify_tailored", END)

    return workflow
