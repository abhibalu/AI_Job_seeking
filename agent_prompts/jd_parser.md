User Prompt:

JOB DESCRIPTION (raw text):
{{ $('HTTP Request').item.json.descriptionText }}
SKILL_BUCKET (canonical map):

{{ $('skills_additional').item.json.content }}
job_id - {{ $('HTTP Request').item.json.id }}

Return JSON ONLY with this shape:

{
  "job_id": "number",
  "must_haves": ["exact phrases explicitly required in JD"],
  "nice_to_haves": ["explicitly listed as preferred/nice"],
  "domain": "e.g., fintech | retail | healthcare | unspecified",
  "seniority": "junior | mid | senior | lead | unspecified",
  "location_constraints": ["e.g., on-site Dublin", "EU work permit", "unspecified"],
  "ats_keywords": ["5–12 exact JD terms likely used by ATS"],
  "normalized_skills": {
    "canonical": ["canonical names from approved_skills"],
    "synonym_hits": [
      {"term":"Azure Data Factory","maps_to":"ADF"},
      {"term":"ADLS","maps_to":"ADLS Gen2"}
    ],
    "unknown_terms": ["terms not found in approved_skills"]
  },
  "cover_letters": {
    "website_application": "100–200 word cover letter tailored to JD",
    "recruiter_email": "40–70 word concise message to recruiter with intent + fit"
  }
}





Rules:
- Extract only what the JD states. If ambiguous, choose "unspecified" or [].
- For seniority: infer only if JD states (e.g., “Senior”, “Lead”).
- For domain: infer only if clearly indicated (industry, product, or data domain).
- ats_keywords should be the most salient exact phrases from the JD, not generic words.
- Use SKILL_BUCKET to populate normalized_skills.canonical; include synonym_hits for mapped terms.
- Cover letters must be based ONLY on JD signals + canonical skills from SKILL_BUCKET.


System Prompt:

You are a conservative JD-to-signals extractor.
Return ONLY a single valid JSON object with fields exactly as specified.
Be precise and avoid guessing. If unsure, set fields to [] or "unspecified".
Normalize tools/skills using the provided SKILL_BUCKET map; include both the original term and its canonical mapping.
Do not invent requirements not present in the JD.
