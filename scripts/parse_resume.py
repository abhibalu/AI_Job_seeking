import os
import json
import sys

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.resume_parser import ResumeParserAgent

INPUT_FILE = "/Users/abhijithm/Documents/Code/TailorAI/test/abhijith_sivadas_resume_retail.txt"
OUTPUT_FILE = "/Users/abhijithm/Documents/Code/TailorAI/test/master_resume.json"

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found at {INPUT_FILE}")
        return

    print(f"Reading text from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f:
        resume_text = f.read()

    print("Initializing ResumeParserAgent...")
    agent = ResumeParserAgent()
    
    print("Running parser (this may take a moment)...")
    result = agent.run(resume_text=resume_text)
    
    if "error" in result:
        print("Parsing failed!")
        if "raw" in result:
             print(f"Raw response: {result['raw']}")
        return

    print(f"Parsing successful. Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(result, f, indent=2)

    print("Done!")
    print("-" * 30)
    print(json.dumps(result, indent=2)[:500] + "...")

if __name__ == "__main__":
    main()
