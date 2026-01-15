from agents.database import get_master_resume
import json

def check_master():
    print("Fetching current Master Resume from DB...")
    resume = get_master_resume()
    if not resume:
        print("No master resume found in DB!")
        return

    # Check for AWS/Redshift
    resume_str = json.dumps(resume).lower()
    
    keywords = ["aws", "redshift", "fivetran"]
    print("--- KEYWORD CHECK ---")
    for kw in keywords:
        found = kw in resume_str
        print(f"'{kw}': {'FOUND' if found else 'NOT FOUND'}")

if __name__ == "__main__":
    check_master()
