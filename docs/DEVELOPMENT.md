# Development Guide

This guide provides comprehensive information for developers working on the Resume Template project, including setup, testing, contribution guidelines, and advanced development topics.

## 🛠️ Development Setup

### Prerequisites

- **Python**: 3.9 or higher
- **Node.js**: 14.x or higher (for resume-cli and theme development)
- **Git**: For version control
- **IDE**: VS Code or Python IDE with support for FastAPI

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd resume_template

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for themes and resume-cli)
npm install -g resume-cli

# Install theme dependencies
cd theme-local
npm install
cd ..
```

### Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt  # If exists, or create one

# Set up pre-commit hooks (recommended)
pre-commit install

# Configure environment variables
cp .env.example .env
# Edit .env with your configuration
```

## 📁 Code Organization

### Project Structure

```
resume_template/
├── app/                    # Application core
│   ├── __init__.py
│   ├── main.py           # FastAPI application and routes
│   ├── templates/        # HTML templates (UI)
│   │   ├── index.html
│   │   ├── variant.html
│   │   └── interview_prep.html
│   └── test.json         # Test data
├── docs/                 # Documentation
│   ├── README.md         # Overview and setup
│   ├── API.md           # API documentation
│   ├── ARCHITECTURE.md  # System architecture
│   └── DEVELOPMENT.md   # This guide
├── n8n_prompts/          # AI agent system prompts
│   ├── job_match_analyzer_agent_system_prompt.md
│   ├── resume_writer_agent_system_prompt.md
│   ├── resume_tailor_agent_system_prompt.md
│   ├── create_variant_api_schema.json
│   └── AGENT_WORKFLOW.md
├── theme-local/          # Custom resume theme
│   ├── package.json
│   ├── template.hbs
│   └── index.js
├── tests/                # Test files (create if needed)
│   ├── __init__.py
│   ├── test_main.py
│   └── test_api.py
├── .gitignore
├── requirements.txt
├── package.json
├── README.md
└── resume.json
```

### Key Modules and Functions

#### `app/main.py` - Core Application

**Main Components:**

1. **Application Setup**
```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from pathlib import Path
import json
import subprocess
import tempfile
import datetime as dt

# Application initialization
app = FastAPI(title="Resume API")

# Path configuration
ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "resume.json"
VARIANTS_DIR = ROOT / "variants"
OUT_DIR = ROOT / "out"
APPROVALS_PATH = ROOT / "approvals.json"

# Template setup
TEMPLATES = Jinja2Templates(directory=str(ROOT / "app" / "templates"))
```

2. **Utility Functions**
```python
def read_json(p: Path) -> Dict[str, Any]:
    """Read and parse a JSON file."""
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def read_json_safe(p: Path, default: Any) -> Any:
    """Read JSON file, returning default if file does not exist or parsing fails."""
    if not p.exists():
        return default
    try:
        return read_json(p)
    except Exception:
        return default

def write_json(p: Path, data: Dict[str, Any]):
    """Write data as formatted JSON to file."""
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

3. **Data Models**
```python
class CreateVariantRequest(BaseModel):
    variant_name: str
    tailored_resume: Dict[str, Any]
    company_name: str
    # Optional fields for job match analysis
    title_role: Optional[str] = None
    recruiter_email: Optional[str] = None
    JD: Optional[str] = None
    verdict: Optional[str] = None
    job_match_score: Optional[int] = None
    summary: Optional[str] = None
    required_exp: Optional[str] = None
    gaps: Optional[Dict[str, List[str]]] = None
    improvement_suggestions: Optional[Dict[str, Any]] = None
    interview_tips: Optional[Dict[str, Any]] = None
    recommended_action: Optional[str] = None
    jd_keywords: Optional[List[str]] = None
    matched_keywords: Optional[List[str]] = None
    missing_keywords: Optional[List[str]] = None
    posted_date: Optional[str] = None
    application_deadline: Optional[str] = None
    job_url: Optional[str] = None

class ApprovalStatus(BaseModel):
    variant: str
    status: str  # draft|approved|rejected
    updated_at: str
```

#### Key API Functions

1. **Resume Management**
```python
@app.get("/resume")
def get_resume():
    """Get the base/original resume JSON."""
    return read_json(BASE_PATH)

@app.patch("/resume/{section}")
def patch_section(section: str, payload: Dict[str, Any]):
    """Update a section in the base resume.json."""
    base = read_json(BASE_PATH)
    base[section] = payload
    write_json(BASE_PATH, base)
    return {"ok": True}
```

2. **Variant Management**
```python
@app.post("/variants")
def create_variant(req: CreateVariantRequest):
    """Create a new tailored resume variant (full JSON)."""
    variant_path = VARIANTS_DIR / f"{req.variant_name}.json"
    data = {
        "company_name": req.company_name,
        "resume": req.tailored_resume,
        "created_at": dt.datetime.utcnow().isoformat(),
    }
    
    # Add optional fields if provided
    optional_fields = [
        'title_role', 'recruiter_email', 'JD', 'verdict', 'job_match_score',
        'summary', 'required_exp', 'gaps', 'improvement_suggestions',
        'interview_tips', 'recommended_action', 'jd_keywords',
        'matched_keywords', 'missing_keywords', 'posted_date',
        'application_deadline', 'job_url'
    ]
    
    for field in optional_fields:
        if getattr(req, field) is not None:
            data[field] = getattr(req, field)
    
    write_json(variant_path, data)
    return {"ok": True, "variant_name": req.variant_name, "path": str(variant_path)}
```

3. **Export System**
```python
@app.post("/export")
def export_resume(variant_name: str, fmt: str = "pdf", theme: Optional[str] = None, review: bool = False):
    """Export a variant resume as HTML or PDF with custom naming."""
    variant_data = get_variant(variant_name)
    resume_json = variant_data.get("resume")
    company = variant_data.get("company_name", "unknown")

    # Process for review mode vs final output
    output_json = json.loads(json.dumps(resume_json))  # deep copy
    if review and fmt == "html":
        output_json["_review_mode"] = True
        base = read_json(BASE_PATH)
        output_json["_base_resume"] = base
    else:
        # Clean final output: remove meta
        output_json.pop("meta", None)
        output_json.pop("_review_mode", None)
        output_json.pop("_base_resume", None)

    # Generate file using resume-cli
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(output_json, tf, ensure_ascii=False, indent=2)
        tmp_path = tf.name

    OUT_DIR.mkdir(exist_ok=True)
    variant_dir = OUT_DIR / variant_name
    variant_dir.mkdir(parents=True, exist=True)

    filename = f"Abhijith_sivadas_moothedath_{company}.{fmt}"
    out_file = variant_dir / filename

    # Theme resolution with fallback
    chosen = theme or "local"
    def theme_value(val: str) -> str:
        if val == "elegant":
            return "elegant"
        if val == "local":
            return "local"
        return val

    def run_export(theme_arg: str):
        cmd = [
            "resume", "export", str(out_file),
            "--theme", theme_arg,
            "--resume", tmp_path,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    # Execute with fallback
    res = run_export(theme_value(chosen))
    if res.returncode != 0 and chosen in (None, "local"):
        fallback = run_export("elegant")
        if fallback.returncode != 0:
            raise HTTPException(500, f"export failed. local: {res.stderr} | elegant: {fallback.stderr}")

    return FileResponse(path=str(out_file), filename=filename)
```

## 🧪 Testing

### Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Test fixtures
├── test_main.py          # Main application tests
├── test_api.py           # API endpoint tests
├── test_utils.py         # Utility function tests
└── integration/          # Integration tests
    ├── __init__.py
    ├── test_workflow.py
    └── test_n8n.py
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_create_variant"
```

### Example Test Cases

#### API Test (`tests/test_api.py`)
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_resume():
    """Test getting the base resume."""
    response = client.get("/resume")
    assert response.status_code == 200
    data = response.json()
    assert "basics" in data
    assert "work" in data
    assert "skills" in data

def test_create_variant():
    """Test creating a new resume variant."""
    variant_data = {
        "variant_name": "test_variant",
        "company_name": "Test Company",
        "tailored_resume": {
            "basics": {
                "name": "Test User",
                "label": "Test Position",
                "email": "test@example.com"
            },
            "work": [],
            "skills": []
        }
    }
    
    response = client.post("/variants", json=variant_data)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["variant_name"] == "test_variant"

def test_export_resume():
    """Test exporting a resume variant."""
    # First create a variant
    variant_data = {
        "variant_name": "test_export",
        "company_name": "Export Test",
        "tailored_resume": {
            "basics": {
                "name": "Test User",
                "label": "Test Position",
                "email": "test@example.com"
            },
            "work": [],
            "skills": []
        }
    }
    
    client.post("/variants", json=variant_data)
    
    # Test HTML export
    response = client.post("/export?variant_name=test_export&fmt=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_approval_workflow():
    """Test the approval workflow."""
    # Test getting approvals
    response = client.get("/approved")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    
    # Test getting status for non-existent variant
    response = client.get("/status/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
```

#### Utility Test (`tests/test_utils.py`)
```python
import pytest
import json
import tempfile
from pathlib import Path
from app.main import read_json, write_json, read_json_safe

def test_read_write_json():
    """Test JSON reading and writing functions."""
    test_data = {"test": "data", "number": 42}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        # Test writing
        write_json(temp_path, test_data)
        assert temp_path.exists()
        
        # Test reading
        read_data = read_json(temp_path)
        assert read_data == test_data
        
    finally:
        if temp_path.exists():
            temp_path.unlink()

def test_read_json_safe():
    """Test safe JSON reading with defaults."""
    test_data = {"existing": "data"}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        temp_path = Path(f.name)
    
    try:
        # Test reading existing file
        result = read_json_safe(temp_path, {"default": "value"})
        assert result == test_data
        
        # Test reading non-existent file
        nonexistent = Path("/nonexistent/file.json")
        result = read_json_safe(nonexistent, {"default": "value"})
        assert result == {"default": "value"}
        
    finally:
        if temp_path.exists():
            temp_path.unlink()
```

## 🚀 Development Workflow

### 1. Local Development

```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Run in background
nohup uvicorn app.main:app --reload --port 8000 > app.log 2>&1 &

# View logs
tail -f app.log
```

### 2. Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
pylint app/

# Type checking
mypy app/
```

### 3. Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
EOF

# Install hooks
pre-commit install
```

## 🔧 Configuration

### Environment Variables

```bash
# .env file
PORT=8000
VARIANT_DIR=./variants
OUT_DIR=./out
DEBUG=True
LOG_LEVEL=INFO
```

### Development Configuration

```python
# config.py
import os
from pathlib import Path

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", 8000))
    VARIANT_DIR = Path(os.getenv("VARIANT_DIR", "./variants"))
    OUT_DIR = Path(os.getenv("OUT_DIR", "./out"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

## 🎨 Theme Development

### Custom Theme Development

```bash
# Navigate to theme directory
cd theme-local

# Install dependencies
npm install

# Develop template
# Edit template.hbs

# Test locally
npm run dev  # If available
```

### Theme Testing

```python
# Test theme rendering in development
def test_theme_rendering():
    """Test custom theme rendering."""
    test_resume = {
        "basics": {
            "name": "Test User",
            "label": "Test Position",
            "email": "test@example.com"
        },
        "work": [],
        "skills": []
    }
    
    # Test export with custom theme
    response = client.post("/export?variant_name=test&fmt=html&theme=local")
    assert response.status_code == 200
```

## 🤖 AI Agent Development

### Prompt Development

```bash
# Navigate to prompts directory
cd n8n_prompts

# Edit agent prompts
# - job_match_analyzer_agent_system_prompt.md
# - resume_writer_agent_system_prompt.md
# - resume_tailor_agent_system_prompt.md

# Test prompts with n8n
# Use local testing with sample data
```

### Schema Validation

```python
# Test API schema validation
def test_create_variant_schema():
    """Test variant creation with schema validation."""
    from n8n_prompts.create_variant_api_schema import CreateVariantRequest
    
    valid_data = {
        "variant_name": "test_schema",
        "company_name": "Test Company",
        "tailored_resume": {
            "basics": {"name": "Test", "label": "Position", "email": "test@example.com"},
            "work": [],
            "skills": []
        }
    }
    
    # This should validate successfully
    request = CreateVariantRequest(**valid_data)
    assert request.variant_name == "test_schema"
```

## 📊 Debugging

### Common Issues and Solutions

#### 1. Export Failures

**Issue**: `resume-cli` command fails
```bash
# Solution: Check resume-cli installation
npm list -g resume-cli

# Reinstall if needed
npm uninstall -g resume-cli
npm install -g resume-cli
```

**Issue**: Theme not found
```python
# Debug theme resolution
def debug_theme_resolution(theme_name: str):
    """Debug theme resolution process."""
    chosen = theme_name or "local"
    print(f"Attempting theme: {chosen}")
    
    if chosen == "local":
        local_path = Path("theme-local")
        print(f"Local theme exists: {local_path.exists()}")
    
    # Test theme execution
    cmd = ["resume", "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Resume CLI available: {result.returncode == 0}")
```

#### 2. File System Issues

**Issue**: Permission denied
```bash
# Check permissions
ls -la variants/
ls -la out/

# Fix permissions
chmod 755 variants/
chmod 755 out/
```

**Issue**: File not found
```python
# Debug file existence
def debug_file_paths():
    """Debug file path issues."""
    paths = [
        "resume.json",
        "variants/",
        "out/",
        "approvals.json"
    ]
    
    for path in paths:
        p = Path(path)
        print(f"{path}: {'EXISTS' if p.exists() else 'MISSING'}")
        if p.exists() and p.is_file():
            print(f"  Size: {p.stat().st_size} bytes")
```

### Logging Configuration

```python
# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Example usage in API
@app.post("/variants")
def create_variant(req: CreateVariantRequest):
    logger.info(f"Creating variant: {req.variant_name}")
    try:
        # ... variant creation logic
        logger.info(f"Variant created successfully: {req.variant_name}")
        return {"ok": True, "variant_name": req.variant_name}
    except Exception as e:
        logger.error(f"Failed to create variant {req.variant_name}: {str(e)}")
        raise
```

## 🔄 Git Workflow

### Branch Strategy

```bash
# Main development branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Commit Guidelines

```bash
# Commit message format
<type>(<scope>): <description>

# Types:
# feat: New feature
# fix: Bug fix
# docs: Documentation changes
# style: Code style changes
# refactor: Code refactoring
# test: Test changes
# chore: Build or auxiliary tool changes

# Examples:
feat(api): add new variant endpoint
fix(export): resolve theme fallback issue
docs: update API documentation
test: add variant creation tests
```

## 🚀 Deployment

### Development Deployment

```bash
# Build and run in Docker
docker build -t resume-template .
docker run -p 8000:8000 resume-template

# Or run directly
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Production Considerations

```python
# Production configuration
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "WARNING"
    
    # Add production-specific settings
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_URL = os.getenv("REDIS_URL")
    API_KEY = os.getenv("API_KEY")
```

## 📈 Performance Optimization

### Caching Strategy

```python
# Add caching for frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_resume():
    """Cache base resume to avoid repeated file reads."""
    return read_json(BASE_PATH)

@lru_cache(maxsize=256)
def get_cached_variant(variant_name: str):
    """Cache variant data."""
    return get_variant(variant_name)
```

### Async Operations

```python
# Convert file operations to async
import aiofiles

async def async_read_json(path: Path) -> Dict[str, Any]:
    """Async JSON file reading."""
    async with aiofiles.open(path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)

async def async_write_json(path: Path, data: Dict[str, Any]):
    """Async JSON file writing."""
    async with aiofiles.open(path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))
```

## 🧪 Advanced Testing

### Integration Tests

```python
# tests/integration/test_workflow.py
import pytest
import requests
from pathlib import Path

class TestIntegrationWorkflow:
    """Test complete workflow from variant creation to export."""
    
    def test_complete_workflow(self):
        """Test the complete variant workflow."""
        # 1. Create variant
        variant_data = {...}
        response = requests.post("http://localhost:8000/variants", json=variant_data)
        assert response.status_code == 200
        
        variant_name = variant_data["variant_name"]
        
        # 2. Get variant
        response = requests.get(f"http://localhost:8000/variants/{variant_name}")
        assert response.status_code == 200
        
        # 3. Export to HTML
        response = requests.post(f"http://localhost:8000/export?variant_name={variant_name}&fmt=html")
        assert response.status_code == 200
        
        # 4. Export to PDF
        response = requests.post(f"http://localhost:8000/export?variant_name={variant_name}&fmt=pdf")
        assert response.status_code == 200
        
        # 5. Approve variant
        response = requests.post(f"http://localhost:8000/ui/approve/{variant_name}")
        assert response.status_code == 303
        
        # 6. Check approved list
        response = requests.get("http://localhost:8000/approved")
        assert response.status_code == 200
        assert variant_name in response.json()
```

### Performance Tests

```python
# tests/performance/test_api.py
import pytest
import time
import requests

class TestPerformance:
    """Test API performance under load."""
    
    @pytest.mark.performance
    def test_variant_creation_performance(self):
        """Test variant creation performance."""
        start_time = time.time()
        
        for i in range(100):
            variant_data = {...}
            response = requests.post("http://localhost:8000/variants", json=variant_data)
            assert response.status_code == 200
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Created 100 variants in {duration:.2f} seconds")
        assert duration < 30  # Should complete in under 30 seconds
```

## 🤝 Contributing

### Pull Request Process

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** with appropriate tests
4. **Ensure tests pass**: `pytest`
5. **Update documentation** if needed
6. **Submit pull request** with clear description

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or documented)
- [ ] Security considerations addressed
- [ ] Performance impact considered

---

*Last updated: 2025-01-17*