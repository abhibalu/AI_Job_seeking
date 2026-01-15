import json
from pathlib import Path
from agents.database import save_resume

def sync_resume():
    print("Syncing 'agent_prompts/base_resume.json' to Database (is_master=True)...")
    
    resume_path = Path("agent_prompts/base_resume.json")
    if not resume_path.exists():
        print(f"Error: {resume_path} not found")
        return

    with open(resume_path) as f:
        content = json.load(f)
    
    # Save to DB
    save_resume(content, name="Master Resume", is_master=True)
    print("Success: Resume saved to database as latest master.")

if __name__ == "__main__":
    sync_resume()
