import json
from pathlib import Path
from agents.database import get_evaluation

def investigate():
    # 1. Load Base Resume
    resume_path = Path("agent_prompts/base_resume.json")
    if not resume_path.exists():
        print(f"Error: {resume_path} not found")
        return

    with open(resume_path) as f:
        resume = json.load(f)
    
    print("--- BASE RESUME SKILLS ---")
    # Recursively find 'skills' or print relevant sections
    if 'skills' in resume:
        print(json.dumps(resume['skills'], indent=2))
    
    # Also check if they are mentioned in 'work' or 'projects' text
    resume_str = json.dumps(resume).lower()
    
    keywords_to_check = ["aws", "redshift", "fivetran"]
    print("\n--- STRING SEARCH IN RESUME ---")
    for kw in keywords_to_check:
        found = kw in resume_str
        print(f"'{kw}': {'FOUND' if found else 'NOT FOUND'}")

    # 2. Fetch Evaluation
    job_id = "4342315701"
    evaluation = get_evaluation(job_id)
    
    if not evaluation:
        print(f"\nError: Evaluation not found for job {job_id}")
        return

    print(f"\n--- EVALUATION FOR {job_id} ---")
    print(f"Verdict: {evaluation.get('verdict')}")
    print(f"Missing Keywords: {evaluation.get('missing_keywords')}")
    print(f"Matched Keywords: {evaluation.get('matched_keywords')}")
    print(f"JD Keywords: {evaluation.get('jd_keywords')}")

if __name__ == "__main__":
    investigate()
