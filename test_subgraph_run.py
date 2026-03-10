import sys
import logging
logging.basicConfig(level=logging.INFO)

from agents.tailoring_subgraph import build_tailoring_subgraph
from agents.database import get_master_resume, get_evaluation, get_jd_parsed
from pathlib import Path

job_id = '4381729947'
base_resume = get_master_resume()

approved_skills = ""
with open("agent_prompts/approved_skills.md") as f:
    approved_skills = f.read()

eval_res = get_evaluation(job_id) or {}
jd_parsed = get_jd_parsed(job_id) or {}

jd_context = {
    "role": eval_res.get("title_role", "Unknown"),
    "company": eval_res.get("company_name", "Unknown"),
    "must_haves": jd_parsed.get("must_haves", []),
    "ats_keywords": jd_parsed.get("keywords_to_include", []),
}

initial_state = {
    "job_id": job_id,
    "base_resume": base_resume,
    "jd_context": jd_context,
    "approved_skills": approved_skills,
    "revision_count": 0,
    "critique": [],
}

print("Invoking subgraph locally...")
subgraph = build_tailoring_subgraph().compile()
for output in subgraph.stream(initial_state):
    print("--- NODE EXECUTED ---")
    for key, value in output.items():
        print(f"Node '{key}':")
        if 'critique' in value:
            print(f"  Critiques: {len(value['critique'])}")
            for c in value['critique']:
                print(f"  - {c}")
        if 'revision_count' in value:
            print(f"  Revision Count: {value['revision_count']}")

print("Done!")
