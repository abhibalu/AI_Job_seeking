import asyncio
from agents.resume_parser import ResumeParserAgent
from backend.settings import settings

def run_test():
    # Force a known good model
    print(f"Testing ResumeParserAgent with forced model: google/gemini-2.0-flash-exp:free")
    if not settings.OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is missing/empty")
        return

    text = """
    John Doe
    Software Engineer
    Email: john@example.com
    Experience:
    - Built a resume parser using Python.
    """
    
    agent = ResumeParserAgent()
    # OVERRIDE MODEL
    agent.model = "google/gemini-2.0-flash-exp:free"
    
    try:
        print("Running agent...")
        result = agent.run(resume_text=text)
        print("Result Status:", "Success" if "basics" in result else "Bad Structure")
        if "basics" in result:
             print(result)
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    run_test()
