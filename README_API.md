# Resume API

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- UI: open http://localhost:8000/ui to list variants, preview, approve/reject, and export PDF.

## Key endpoints
- GET /resume?variant=V
- GET /resume/{section}[/{id}]?variant=V
- PATCH /resume/{section}
- PATCH /resume/{section}/{id}
- POST /variants/{V}
- GET /variants/{V}/resume
- PATCH /variants/{V}/{section}
- PATCH /variants/{V}/{section}/{id}
- POST /tailor { variant, overlay }
- POST /export?variant=V&fmt=pdf|html

Arrays merge by id if items have an `id` field; otherwise arrays are replaced.
