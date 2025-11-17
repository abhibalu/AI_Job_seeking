# API Documentation

This document provides a comprehensive reference for the Resume Template API endpoints, including request/response formats, examples, and integration guidelines.

## 📡 Base URL

```
http://localhost:8000
```

## 🔍 API Discovery

- **Interactive Swagger UI**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## 📄 Resume Management

### Get Base Resume

```http
GET /resume
```

**Response:**
```json
{
  "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
  "basics": {
    "name": "Abhijith Sivadas Moothedath",
    "label": "Data Engineer",
    "email": "abhijith.sivadas.moothedath@gmail.com",
    "phone": "+353892704877",
    "location": {
      "city": "Dublin",
      "countryCode": "IE"
    },
    "profiles": [...]
  },
  "work": [...],
  "education": [...],
  "skills": [...]
}
```

### Get Resume Section

```http
GET /resume/{section}
GET /resume/{section}/{item_id}
```

**Parameters:**
- `section`: Section name (work, education, skills, etc.)
- `item_id`: Optional specific item ID within section

**Example:**
```http
GET /resume/work
GET /resume/work/metro
```

### Update Resume Section

```http
PATCH /resume/{section}
PATCH /resume/{section}/{item_id}
```

**Request Body:**
```json
{
  "highlights": ["Updated bullet point", "Another highlight"]
}
```

**Example:**
```http
PATCH /resume/work/metro
Content-Type: application/json

{
  "highlights": [
    "Designed scalable ETL pipelines using Apache Airflow",
    "Implemented data quality checks with 99.9% accuracy"
  ]
}
```

---

## 🎯 Variant Management

### Create Variant

```http
POST /variants
Content-Type: application/json

{
  "variant_name": "abhijith_sivadas_moothedath_sosafe",
  "company_name": "SoSafe",
  "tailored_resume": { ... },
  "title_role": "Senior Data Engineer",
  "job_match_score": 70,
  "verdict": "Moderate Match",
  "gaps": {
    "technical": ["AWS", "Kubernetes"],
    "domain": ["Fintech experience"],
    "soft_skills": []
  },
  "improvement_suggestions": {
    "resume_edits": [
      {
        "area": "work.metro.highlights[3]",
        "suggestion": "Emphasize serverless nature",
        "approved_reference": "Cloud Functions project"
      }
    ],
    "interview_prep": ["Study AWS basics"]
  },
  "interview_tips": {
    "high_priority_topics": [...],
    "your_strengths_to_highlight": [...],
    "questions_to_ask": [...]
  },
  "jd_keywords": ["Airflow", "dbt", "AWS"],
  "matched_keywords": ["Airflow", "dbt"],
  "missing_keywords": ["AWS", "Kubernetes"],
  "job_url": "https://example.com/job-posting"
}
```

**Response:**
```json
{
  "ok": true,
  "variant_name": "abhijith_sivadas_moothedath_sosafe",
  "path": "/path/to/variants/abhijith_sivadas_moothedath_sosafe.json"
}
```

### Get Variant

```http
GET /variants/{variant_name}
```

**Response:**
```json
{
  "company_name": "SoSafe",
  "resume": { ...tailored resume JSON... },
  "created_at": "2025-01-17T18:00:00.000Z",
  "job_match_score": 70,
  "verdict": "Moderate Match",
  "gaps": { ... },
  "interview_tips": { ... }
}
```

### Get Variant Resume Only

```http
GET /variants/{variant_name}/resume
```

**Response:**
```json
{
  "$schema": "...",
  "basics": { ... },
  "work": [ ... ],
  "skills": [ ... ]
}
```

### Create Bulk Variants

```http
POST /bulk
Content-Type: application/json

[
  {
    "variant_name": "abhijith_sivadas_moothedath_company1",
    "company_name": "Company 1",
    "tailored_resume": { ... },
    "_meta": { "job_id": 123 }
  },
  {
    "skills": ["Python", "SQL"],
    "work": [ ... ],
    "_meta": { "job_id": 456 }
  }
]
```

**Response:**
```json
{
  "total": 2,
  "created": [
    {
      "index": 0,
      "job_id": 123,
      "variant_name": "abhijith_sivadas_moothedath_company1",
      "path": "/path/to/variant1.json"
    }
  ],
  "errors": [
    {
      "index": 1,
      "error": "Missing variant_name"
    }
  ]
}
```

### Delete Variant

```http
DELETE /variants/{variant_name}
```

**Response:**
```json
{
  "ok": true,
  "deleted": "abhijith_sivadas_moothedath_sosafe"
}
```

---

## 📤 Export System

### Export Resume

```http
POST /export?variant_name={name}&fmt={format}&theme={theme}&review={review}
```

**Parameters:**
- `variant_name`: Required - Name of the variant
- `fmt`: Required - `html` or `pdf`
- `theme`: Optional - `local`, `elegant`, or custom theme name
- `review`: Optional - `true` for HTML preview mode, `false` for clean output

**Examples:**
```bash
# Export PDF with local theme
curl "http://localhost:8000/export?variant_name=sosafe&fmt=pdf"

# Export HTML with review mode
curl "http://localhost:8000/export?variant_name=sosafe&fmt=html&review=true"

# Export with elegant theme fallback
curl "http://localhost:8000/export?variant_name=sosafe&fmt=pdf&theme=elegant"
```

**Response:**
- For PDF: File download with `Content-Type: application/pdf`
- For HTML: File download with `Content-Type: text/html`

### Download Variant PDF

```http
GET /variants/{variant_name}/pdf
```

**Response:**
File download with PDF content.

---

## 🎨 User Interface (UI)

### List Variants

```http
GET /ui
```

**Response:**
HTML page listing all variants with status badges.

### Get Variant Details

```http
GET /ui/variant/{variant_name}
```

**Response:**
HTML page with:
- Resume preview (iframe)
- Approval/reject buttons
- Export options
- Interview prep link

### Get Interview Preparation

```http
GET /ui/variant/{variant_name}/interview-prep
```

**Response:**
HTML page with:
- Job match analysis
- Gap categorization
- Improvement suggestions
- Interview tips and questions

### UI Actions

```http
POST /ui/approve/{variant_name}
POST /ui/reject/{variant_name}
POST /ui/delete/{variant_name}
POST /ui/export/{variant_name}/{fmt}
```

---

## ✅ Approval Workflow

### List Approved Variants

```http
GET /approved
```

**Response:**
```json
[
  "abhijith_sivadas_moothedath_sosafe",
  "abhijith_sivadas_moothedath_salesforce"
]
```

### Get Variant Status

```http
GET /status/{variant_name}
```

**Response:**
```json
{
  "variant": "abhijith_sivadas_moothedath_sosafe",
  "status": "approved",
  "updated_at": "2025-01-17T18:00:00.000Z"
}
```

---

## 🔧 Utility Endpoints

### Health Check

```http
GET /
```

**Response:**
```json
{
  "ok": true
}
```

### Generate Diff Metadata

```http
POST /variants/{variant_name}/generate-diff
```

**Response:**
```json
{
  "ok": true,
  "variant_name": "abhijith_sivadas_moothedath_sosafe",
  "modifications": {
    "work": {
      "metro": {
        "edited_bullets": [0, 2, 4]
      }
    }
  }
}
```

---

## 📊 Error Responses

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid parameters or payload |
| 404 | Not Found - Resource does not exist |
| 500 | Internal Server Error - Server-side failure |

### Error Response Format

```json
{
  "detail": "Error message describing the issue"
}
```

### Example Error Responses

```json
// 404 - Variant not found
{
  "detail": "Variant 'unknown_company' not found"
}

// 400 - Invalid format
{
  "detail": "unsupported fmt; use html or pdf"
}

// 500 - Export failure
{
  "detail": "export failed. stderr: resume-cli error message"
}
```

---

## 🔄 Integration Examples

### cURL Examples

```bash
# Create a new variant
curl -X POST http://localhost:8000/variants \
  -H 'Content-Type: application/json' \
  -d '{
    "variant_name": "abhijith_sivadas_moothedath_test",
    "company_name": "Test Company",
    "tailored_resume": {
      "basics": { "name": "Abhijith Sivadas Moothedath", "label": "Data Engineer" },
      "work": [],
      "skills": []
    }
  }'

# Export to PDF
curl -X POST "http://localhost:8000/export?variant_name=test&fmt=pdf" \
  -o resume.pdf

# List approved variants
curl http://localhost:8000/approved
```

### Python Example

```python
import requests

# Create variant
variant_data = {
    "variant_name": "abhijith_sivadas_moothedath_example",
    "company_name": "Example Corp",
    "tailored_resume": {
        "basics": {"name": "Abhijith Sivadas Moothedath", "label": "Data Engineer"},
        "work": [],
        "skills": []
    }
}

response = requests.post(
    "http://localhost:8000/variants",
    json=variant_data
)
print(response.json())

# Export PDF
export_response = requests.post(
    "http://localhost:8000/export?variant_name=example&fmt=pdf"
)
with open("resume.pdf", "wb") as f:
    f.write(export_response.content)
```

### JavaScript Example

```javascript
// Create variant
const variantData = {
  variant_name: "abhijith_sivadas_moothedath_example",
  company_name: "Example Corp",
  tailored_resume: {
    basics: { name: "Abhijith Sivadas Moothedath", label: "Data Engineer" },
    work: [],
    skills: []
  }
};

fetch('/variants', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(variantData)
})
.then(response => response.json())
.then(data => console.log(data));

// Get approved variants
fetch('/approved')
  .then(response => response.json())
  .then(variants => console.log(variants));
```

---

## 📋 Data Models

### CreateVariantRequest

```json
{
  "variant_name": "string",
  "company_name": "string",
  "tailored_resume": {
    "basics": { "name": "string", "label": "string", ... },
    "work": [ { "id": "string", "highlights": ["string"], ... } ],
    "skills": [ { "name": "string", "keywords": ["string"] } ]
  },
  "title_role": "string",
  "job_match_score": 70,
  "gaps": {
    "technical": ["string"],
    "domain": ["string"],
    "soft_skills": ["string"]
  },
  "interview_tips": {
    "high_priority_topics": [ { "topic": "string", "why": "string", "prep": "string" } ],
    "your_strengths_to_highlight": ["string"],
    "questions_to_ask": ["string"]
  }
}
```

### ApprovalStatus

```json
{
  "variant": "string",
  "status": "draft|approved|rejected",
  "updated_at": "ISO 8601 timestamp"
}
```

---

## 🔒 Security Considerations

### Authentication
- Currently no authentication required
- Consider adding API key authentication for production
- Implement rate limiting for public endpoints

### Data Validation
- All inputs validated via Pydantic models
- JSON schema validation for resume structure
- File path sanitization for security

### File Operations
- Restricted file system access
- Safe directory creation and file handling
- No arbitrary file execution

---

## 🚀 Performance Notes

### Optimization
- FastAPI with automatic async support
- JSON caching for frequently accessed resumes
- Efficient file system operations
- Minimal memory footprint for large files

### Scalability
- Stateless design for horizontal scaling
- File storage can be moved to external storage
- Database integration possible for large-scale deployments

---

*Last updated: 2025-01-17*