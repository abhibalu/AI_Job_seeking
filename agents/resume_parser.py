import json
import logging
from pydantic import ValidationError

from .base import BaseAgent
from api.schemas import JSONResumeSchema

logger = logging.getLogger(__name__)

# One-shot example showing expected JSON Resume structure and fidelity
ONE_SHOT_EXAMPLE = {
    "basics": {
        "name": "John Doe",
        "label": "Programmer",
        "email": "john@gmail.com",
        "phone": "(912) 555-4321",
        "url": "https://johndoe.com",
        "summary": "A summary of John Doe…",
        "location": {
            "address": "2712 Broadway St",
            "postalCode": "CA 94115",
            "city": "San Francisco",
            "countryCode": "US",
            "region": "California",
        },
        "profiles": [
            {
                "network": "Twitter",
                "username": "john",
                "url": "https://twitter.com/john",
            }
        ],
    },
    "work": [
        {
            "name": "Company",
            "position": "President",
            "url": "https://company.com",
            "startDate": "2013-01-01",
            "endDate": "2014-01-01",
            "summary": "Description…",
            "highlights": ["Started the company"],
        }
    ],
    "education": [
        {
            "institution": "University",
            "url": "https://institution.com/",
            "area": "Software Development",
            "studyType": "Bachelor",
            "startDate": "2011-01-01",
            "endDate": "2013-01-01",
            "score": "4.0",
            "courses": ["DB1101 - Basic SQL"],
        }
    ],
    "awards": [
        {
            "title": "Award",
            "date": "2014-11-01",
            "awarder": "Company",
            "summary": "There is no spoon.",
        }
    ],
    "skills": [
        {
            "name": "Web Development",
            "level": "Master",
            "keywords": ["HTML", "CSS", "JavaScript"],
        }
    ],
    "languages": [{"language": "English", "fluency": "Native speaker"}],
    "projects": [
        {
            "name": "Project",
            "startDate": "2019-01-01",
            "endDate": "2021-01-01",
            "description": "Description...",
            "highlights": ["Won award at AIHacks 2016"],
            "url": "https://project.com/",
        }
    ],
}

RESUME_PARSER_SYSTEM_PROMPT = """
You are an expert Resume Parser performing VERBATIM extraction — not summarization.

Your job is to convert raw resume text into a structured JSON object following the JSON Resume schema. You must preserve ALL content from the source text with full fidelity.

Output MUST be a valid JSON object. Do not include any markdown formatting (like ```json), just the raw JSON.

## Section Mapping

Map resume sections to JSON Resume fields as follows:

| Resume Section | JSON Resume Field |
|---|---|
| Contact info, name, title | basics |
| LinkedIn, GitHub, etc. | basics.profiles[] |
| WORK EXPERIENCE / EMPLOYMENT | work[] |
| TECHNICAL PROJECTS / PROJECTS / SIDE PROJECTS | projects[] |
| EDUCATION | education[] |
| SKILLS / TECHNICAL SKILLS | skills[] |
| AWARDS / CERTIFICATIONS | awards[] |
| LANGUAGES | languages[] |

## Schema

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
      "location": "string (e.g. 'Bangalore, India')",
      "position": "string",
      "url": "string",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD (or 'Present')",
      "summary": "string",
      "highlights": ["string — one entry per bullet point, preserving full text"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "url": "string",
      "area": "string (Major/Field of Study)",
      "studyType": "string (Full degree name, e.g. 'Bachelor of Engineering')",
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
      "highlights": ["string — one entry per bullet point, preserving full text"],
      "keywords": ["string"],
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD",
      "url": "string",
      "roles": ["string"]
    }
  ]
}

## Instructions

1. Extract ALL information from the source text. Every section, every bullet point, every detail.
2. Each bullet point in the source becomes a SEPARATE highlights[] entry, preserving the FULL original text.
3. For "label", use the most recent job title from the WORK EXPERIENCE section (e.g. "Data Engineer"). Do NOT copy text from the PROFILE/SUMMARY section into label.
4. Preserve location information for work entries (city, country).
5. Preserve full degree names and areas of study for education entries.
6. If a field is not found, omit it or use empty lists/null.
7. Ensure valid JSON output.

## DO NOT

- DO NOT summarize, shorten, or paraphrase bullet points. Copy them verbatim.
- DO NOT truncate highlights — include the complete text of each bullet.
- DO NOT merge multiple bullet points into one highlight entry.
- DO NOT drop any sections. If the resume has a TECHNICAL PROJECTS section, it MUST appear in projects[].
- DO NOT strip location information from work entries.
- DO NOT abbreviate degree names in education entries.
- DO NOT use profile/summary text as the "label" — label must be a short job title only (e.g. "Data Engineer", "Software Developer").
- DO NOT drop bullet points. The number of highlights[] entries for each work/project entry MUST match the number of bullet points in the source text for that entry.
"""


class ResumeParserAgent(BaseAgent):
    def __init__(self, model=None):
        super().__init__(model=model, temperature=0.1)

    def get_system_prompt(self) -> str:
        return RESUME_PARSER_SYSTEM_PROMPT

    def build_user_prompt(self, resume_text: str) -> str:
        example = json.dumps(ONE_SHOT_EXAMPLE, indent=2)
        return (
            f"Here is an example of the expected JSON Resume output structure:\n{example}\n\n"
            f"Now parse the following resume text into the same format.\n\n"
            f"Resume Text:\n\n{resume_text}"
        )

    def run(self, **kwargs) -> dict:
        """Parse resume with Pydantic validation and one retry."""
        self.system_prompt = self.get_system_prompt()
        user_prompt = self.build_user_prompt(**kwargs)

        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            prompt = user_prompt
            if attempt > 0 and last_error:
                prompt += f"\n\n⚠️ Previous output failed validation:\n{last_error}\nFix the issues and return valid JSON."

            response_text = self._call_llm(prompt, response_format={"type": "json_object"})
            result = self._parse_json_response(response_text)

            try:
                validated = JSONResumeSchema.model_validate(result)
                clean = validated.model_dump()
                clean["_model_used"] = self.model
                clean["_agent"] = self.__class__.__name__
                return clean
            except ValidationError as e:
                last_error = str(e)
                logger.warning(f"Resume parse attempt {attempt+1} failed validation: {last_error}")

        # Both attempts failed — return raw result with warning flag
        result["_validation_failed"] = True
        result["_validation_error"] = last_error
        return result
