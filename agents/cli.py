"""
CLI for running and testing agents.

Usage:
    python -m agents.cli init-db              # Initialize database
    python -m agents.cli evaluate <job_id>    # Evaluate single job
    python -m agents.cli parse <job_id>       # Parse JD for evaluated job
    python -m agents.cli run --max-jobs 5     # Run full pipeline
    python -m agents.cli status               # Show evaluation stats
"""
import argparse
import json
import sys

import polars as pl
from deltalake import DeltaTable

from backend.settings import settings
from .database import (
    init_database, 
    is_job_evaluated, 
    is_job_parsed,
    save_evaluation, 
    save_jd_parsed,
    get_evaluation,
    get_db_connection,
)
from .job_evaluator import JobEvaluatorAgent
from .jd_parser import JDParserAgent


def get_storage_options() -> dict:
    """Get S3 storage options for Delta Lake."""
    return {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }


def load_gold_jobs() -> pl.DataFrame:
    """Load jobs from Gold Delta table."""
    storage_options = get_storage_options()
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    dt = DeltaTable(gold_path, storage_options=storage_options)
    return pl.from_arrow(dt.to_pyarrow_table())


def get_job_by_id(job_id: str) -> dict | None:
    """Get a single job from Gold table by ID."""
    df = load_gold_jobs()
    job_df = df.filter(pl.col("id") == job_id)
    
    if job_df.is_empty():
        return None
    
    row = job_df.row(0, named=True)
    return row


def cmd_init_db(args):
    """Initialize the database."""
    init_database()
    print("✅ Database initialized")


def cmd_evaluate(args):
    """Evaluate a single job."""
    job_id = args.job_id
    
    # Check if already evaluated
    if is_job_evaluated(job_id) and not args.force:
        print(f"⏭️  Job {job_id} already evaluated. Use --force to re-evaluate.")
        return
    
    # Get job from Gold table
    job = get_job_by_id(job_id)
    if not job:
        print(f"❌ Job {job_id} not found in Gold table")
        return
    
    print(f"🔍 Evaluating job: {job.get('title', 'Unknown')} @ {job.get('company_name', 'Unknown')}")
    
    # Run evaluator
    agent = JobEvaluatorAgent()
    
    try:
        result = agent.run(
            job_id=job_id,
            description_text=job.get("description_text", ""),
            company_name=job.get("company_name", "Unknown"),
            title=job.get("title", "Unknown"),
            job_url=job.get("link", "Unknown"),
        )
        
        # Save to database
        save_evaluation(result)
        
        # Print summary
        print(f"\n✅ Evaluation complete:")
        print(f"   Verdict: {result.get('Verdict', 'Unknown')}")
        print(f"   Score: {result.get('job_match_score', 0)}")
        print(f"   Action: {result.get('recommended_action', 'Unknown')}")
        print(f"   Summary: {result.get('summary', '')[:100]}...")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()


def cmd_parse(args):
    """Parse JD for an evaluated job."""
    job_id = args.job_id
    
    # Check if evaluated first
    evaluation = get_evaluation(job_id)
    if not evaluation:
        print(f"❌ Job {job_id} not evaluated yet. Run 'evaluate {job_id}' first.")
        return
    
    # Check verdict
    verdict = evaluation.get("recommended_action", "")
    if verdict == "skip" and not args.force:
        print(f"⏭️  Job {job_id} marked as 'skip'. Use --force to parse anyway.")
        return
    
    # Check if already parsed
    if is_job_parsed(job_id) and not args.force:
        print(f"⏭️  Job {job_id} already parsed. Use --force to re-parse.")
        return
    
    # Get job from Gold table
    job = get_job_by_id(job_id)
    if not job:
        print(f"❌ Job {job_id} not found in Gold table")
        return
    
    print(f"📋 Parsing JD for: {job.get('title', 'Unknown')} @ {job.get('company_name', 'Unknown')}")
    
    # Run parser
    agent = JDParserAgent()
    
    try:
        result = agent.run(
            job_id=job_id,
            description_text=job.get("description_text", ""),
        )
        
        # Save to database
        save_jd_parsed(result)
        
        # Print summary
        print(f"\n✅ Parse complete:")
        print(f"   Must-haves: {len(result.get('must_haves', []))} items")
        print(f"   ATS Keywords: {result.get('ats_keywords', [])[:5]}...")
        print(f"   Domain: {result.get('domain', 'Unknown')}")
        print(f"   Seniority: {result.get('seniority', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Parse failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()


def cmd_run(args):
    """Run full pipeline on multiple jobs."""
    max_jobs = args.max_jobs
    
    # Initialize database
    init_database()
    
    # Load all jobs
    df = load_gold_jobs()
    print(f"📊 Found {len(df)} jobs in Gold table")
    
    evaluated = 0
    parsed = 0
    skipped = 0
    
    for row in df.iter_rows(named=True):
        if evaluated >= max_jobs:
            break
        
        job_id = str(row.get("id", ""))
        if not job_id:
            continue
        
        # Evaluate if not done
        if not is_job_evaluated(job_id):
            print(f"\n🔍 [{evaluated + 1}/{max_jobs}] Evaluating: {row.get('title', 'Unknown')[:40]}...")
            
            try:
                agent = JobEvaluatorAgent()
                result = agent.run(
                    job_id=job_id,
                    description_text=row.get("description_text", ""),
                    company_name=row.get("company_name", "Unknown"),
                    title=row.get("title", "Unknown"),
                    job_url=row.get("link", "Unknown"),
                )
                save_evaluation(result)
                evaluated += 1
                
                verdict = result.get("recommended_action", "")
                score = result.get("job_match_score", 0)
                print(f"   → {result.get('Verdict', '')} (Score: {score}, Action: {verdict})")
                
                # Parse if not skip
                if verdict != "skip" and not is_job_parsed(job_id):
                    print(f"   📋 Parsing JD...")
                    parser = JDParserAgent()
                    parse_result = parser.run(
                        job_id=job_id,
                        description_text=row.get("description_text", ""),
                    )
                    save_jd_parsed(parse_result)
                    parsed += 1
                    print(f"   → Parsed ({len(parse_result.get('must_haves', []))} must-haves)")
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            skipped += 1
    
    print(f"\n📊 Pipeline complete:")
    print(f"   Evaluated: {evaluated}")
    print(f"   Parsed: {parsed}")
    print(f"   Skipped: {skipped}")


def cmd_status(args):
    """Show evaluation statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count evaluations
    cursor.execute("SELECT COUNT(*) FROM job_evaluations")
    total_evals = cursor.fetchone()[0]
    
    cursor.execute("SELECT recommended_action, COUNT(*) FROM job_evaluations GROUP BY recommended_action")
    action_counts = dict(cursor.fetchall())
    
    cursor.execute("SELECT AVG(job_match_score) FROM job_evaluations")
    avg_score = cursor.fetchone()[0] or 0
    
    # Count parsed
    cursor.execute("SELECT COUNT(*) FROM jd_parsed")
    total_parsed = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n📊 Evaluation Status:")
    print(f"   Total evaluated: {total_evals}")
    print(f"   Average score: {avg_score:.1f}")
    print(f"   - Apply: {action_counts.get('apply', 0)}")
    print(f"   - Tailor: {action_counts.get('tailor', 0)}")
    print(f"   - Skip: {action_counts.get('skip', 0)}")
    print(f"\n   JDs parsed: {total_parsed}")


def main():
    parser = argparse.ArgumentParser(description="TailorAI Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init-db command
    subparsers.add_parser("init-db", help="Initialize database")
    
    # evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a single job")
    eval_parser.add_argument("job_id", help="Job ID to evaluate")
    eval_parser.add_argument("--force", action="store_true", help="Force re-evaluation")
    eval_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # parse command
    parse_parser = subparsers.add_parser("parse", help="Parse JD for evaluated job")
    parse_parser.add_argument("job_id", help="Job ID to parse")
    parse_parser.add_argument("--force", action="store_true", help="Force re-parse")
    parse_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument("--max-jobs", type=int, default=5, help="Max jobs to process")
    
    # status command
    subparsers.add_parser("status", help="Show evaluation stats")
    
    args = parser.parse_args()
    
    if args.command == "init-db":
        cmd_init_db(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "parse":
        cmd_parse(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
