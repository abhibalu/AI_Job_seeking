import json
from .base import BaseAgent

RESUME_PARSER_SYSTEM_PROMPT = """
You are an expert Resume Parser. Your job is to convert raw resume text into a structured JSON object following the JSON Resume schema.

Output MUST be a valid JSON object. Do not include any markdown formatting (like ```json), just the raw JSON.

The schema structure is as follows:
{
  "basics": {
    "name": "string",
    "label": "string (Job Title)",
    "email": "string",
    "phone": "string",
    "url": "string (Website)",
    "summary": "string",
    "location": {
      "address": "string",
      "postalCode": "string",
      "city": "string",
      "countryCode": "string",
      "region": "string"
    },
    "profiles": [
      {
        "network": "string (e.g. LinkedIn)",
        "username": "string",
        "url": "string"
      }
    ]
  },
  "work": [
    {
      "name": "string (Company)",
      "position": "string",
      "url": "string",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD (or 'Present')",
      "summary": "string",
      "highlights": ["string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "url": "string",
      "area": "string (Major)",
      "studyType": "string (Degree)",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD",
      "score": "string",
      "courses": ["string"]
    }
  ],
  "awards": [
    {
      "title": "string",
      "date": "YYYY-MM-DD",
      "awarder": "string",
      "summary": "string"
    }
  ],
  "skills": [
    {
      "name": "string",
      "level": "string",
      "keywords": ["string"]
    }
  ],
  "languages": [
    {
      "language": "string",
      "fluency": "string"
    }
  ],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "highlights": ["string"],
      "keywords": ["string"],
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD",
      "url": "string",
      "roles": ["string"]
    }
  ]
}

Instructions:
1. Extract as much information as possible from the text.
2. Infer "label" (current job title) if not explicitly stated.
3. Split work experience descriptions into concise "highlights" (bullet points).
4. If a field is not found, omit it or use empty lists/null.
5. Ensure valid JSON output.
"""

class ResumeParserAgent(BaseAgent):
    def get_system_prompt(self) -> str:
        return RESUME_PARSER_SYSTEM_PROMPT

    def build_user_prompt(self, resume_text: str) -> str:
        return f"Resume Text:\n\n{resume_text}"

