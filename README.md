# How to Run: JSON Resume UI + API

This project provides a FastAPI backend and a minimal UI to manage versioned JSON-resume variants, preview/export to HTML/PDF, and approve for downstream automations (e.g., n8n).

## Prerequisites
- Python 3.9+
- Node.js + npm
- resume-cli (for HTML/PDF export)

```bash
npm i -g resume-cli
```

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the server
```bash
uvicorn app.main:app --reload --port 8000
```
Open UI at: http://localhost:8000/ui

## Architecture Overview
- **resume.json** = Original/base resume (never modified by variants)
- **variants/{variant_name}.json** = Full tailored resume + metadata (company_name, created_at)
- **out/{variant_name}/Abhijith_sivadas_moothedath_{company}.pdf** = Generated PDFs
- **approvals.json** = Approval status (draft|approved|rejected)

## Workflow: n8n → API → You → n8n

### 1. n8n creates a tailored variant
```bash
curl -X POST http://localhost:8000/variants \
  -H 'Content-Type: application/json' \
  -d '{
    "variant_name": "abhijith_sivadas_moothedath_acme",
    "company_name": "acme",
    "tailored_resume": { <full JSON resume> }
  }'
```

### 2. n8n exports PDF
```bash
curl -X POST "http://localhost:8000/export?variant_name=abhijith_sivadas_moothedath_acme&fmt=pdf"
```
Generates: `out/abhijith_sivadas_moothedath_acme/Abhijith_sivadas_moothedath_acme.pdf`

### 3. You review and approve via UI
- Open http://localhost:8000/ui
- Click variant → Preview → Approve/Reject

### 4. n8n polls for approved variants
```bash
# List all approved variants
curl http://localhost:8000/approved
# ["abhijith_sivadas_moothedath_acme", ...]

# Download approved PDF
curl -O http://localhost:8000/variants/abhijith_sivadas_moothedath_acme/pdf
```

## API Reference

### Base Resume
- `GET /resume` - Get original resume JSON
- `GET /resume/{section}` - Get a section (e.g., /resume/work)
- `PATCH /resume/{section}` - Update base resume section

### Variants
- `POST /variants` - Create tailored variant (body: variant_name, company_name, tailored_resume)
- `GET /variants/{variant_name}` - Get variant metadata + resume
- `GET /variants/{variant_name}/resume` - Get just the resume JSON
- `GET /variants/{variant_name}/pdf` - Download generated PDF

### Export
- `POST /export?variant_name={name}&fmt=pdf` - Generate PDF/HTML with custom naming

### Approval (for n8n)
- `GET /approved` - List approved variant names
- `GET /status/{variant_name}` - Get approval status
- `POST /ui/approve/{variant_name}` - Mark as approved
- `POST /ui/reject/{variant_name}` - Mark as rejected

### UI
- `GET /ui` - List all variants
- `GET /ui/variant/{variant_name}` - Detail page with preview

## Notes
- Variants store **full tailored JSON**, not diffs
- PDF naming: `Abhijith_sivadas_moothedath_{company_name}.pdf`
- Approval workflow keeps you in the loop before n8n sends resumes
- If export fails, ensure resume-cli is installed: `npm i -g resume-cli`
