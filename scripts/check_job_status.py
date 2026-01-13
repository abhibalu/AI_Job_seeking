from agents.database import get_evaluation, is_job_parsed, list_evaluations
import json

print("--- Latest 5 Evaluations ---")
latest = list_evaluations(limit=5)
for eval in latest:
    print(f"ID: {eval.get('job_id')} | Date: {eval.get('evaluated_at')} | Action: {eval.get('recommended_action')}")

job_id = '4309695599'
print(f"\n--- Checking Specific Job {job_id} ---")
# ... existing check ...

evaluation = get_evaluation(job_id)
if evaluation:
    print("\n--- Evaluation Found ---")
    print(f"Action: {evaluation.get('recommended_action')}")
    print(f"Verdict: {evaluation.get('verdict')}")
    print(f"Score: {evaluation.get('job_match_score')}")
    print(f"Model: {evaluation.get('model_used')}")
    print(f"Evaluated At: {evaluation.get('evaluated_at')}")
else:
    print("\n--- No Evaluation Found ---")

is_parsed = is_job_parsed(job_id)
print(f"\nIs Parsed: {is_parsed}")
