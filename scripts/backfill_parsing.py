"""
Backfill JD Parsing Script
==========================

Parses JDs for all existing evaluations that have recommended_action='tailor' or 'apply'
but haven't been parsed yet.

Usage:
    python scripts/backfill_parsing.py
"""
import sys
import time
from pathlib import Path
import concurrent.futures

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.database import list_evaluations, is_job_parsed, save_jd_parsed
from agents.jd_parser import JDParserAgent
from api.routes.evaluations import get_job_by_id


def process_job(job_id: str, action: str):
    """Fetch JD text and run parser."""
    try:
        # Double check inside thread
        if is_job_parsed(job_id):
            return f"SKIP: {job_id} (Already parsed)"

        # Fetch full JD text (requires Delta Lake access)
        job = get_job_by_id(job_id)
        if not job:
            return f"ERROR: {job_id} (JD text not found in Gold table)"
        
        description = job.get("description_text", "")
        if not description:
            return f"ERROR: {job_id} (Empty description)"

        # Run Parser
        agent = JDParserAgent()
        result = agent.run(job_id=job_id, description_text=description)
        
        # Save
        save_jd_parsed(result)
        return f"SUCCESS: {job_id} (Parsed {len(result.get('must_haves', []))} signals)"

    except Exception as e:
        return f"FAILED: {job_id} ({str(e)})"


def main():
    print("--- TailorAI Parsing Backfill ---")
    
    # 1. Get Candidate Jobs
    print("Fetching evaluations...")
    # We fetch both 'tailor' and 'apply'
    candidates = []
    
    for action in ["tailor", "apply"]:
        evals = list_evaluations(limit=1000, action=action)
        candidates.extend(evals)
        
    print(f"Found {len(candidates)} candidates with 'tailor' or 'apply'.")
    
    # 2. Filter Unparsed
    to_process = []
    for ev in candidates:
        job_id = str(ev["job_id"])
        if not is_job_parsed(job_id):
            to_process.append((job_id, ev.get("recommended_action")))
            
    print(f"Jobs needing parsing: {len(to_process)}")
    
    if not to_process:
        print("Nothing to do!")
        return

    # 3. Concurrent Execution
    max_workers = 5
    print(f"\nStarting processing with {max_workers} workers...")
    
    start_time = time.time()
    completed = 0
    errors = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_map = {
            executor.submit(process_job, job_id, action): job_id 
            for job_id, action in to_process
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_map):
            job_id = future_map[future]
            try:
                result = future.result()
                print(result)
                if "FAILED" in result or "ERROR" in result:
                    errors += 1
            except Exception as e:
                print(f"CRITICAL ERROR for {job_id}: {e}")
                errors += 1
            
            completed += 1
            print(f"Progress: {completed}/{len(to_process)}")

    duration = time.time() - start_time
    print(f"\nDone! Processed {completed} jobs in {duration:.2f}s.")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
