# Resume Template Documentation

Welcome to the Resume Template project - a comprehensive FastAPI-based system for managing versioned JSON resume variants with AI-powered tailoring capabilities.

## 📋 Overview

This project provides a complete solution for:
- **Resume Management**: Store and manage multiple tailored resume variants
- **AI-Powered Tailoring**: Integrate with n8n workflows for automated resume customization
- **Export Capabilities**: Generate HTML and PDF exports with custom themes
- **Approval Workflow**: Review and approve variants before automated processing
- **Interview Preparation**: Built-in job match analysis and interview prep features

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js + npm
- resume-cli (for HTML/PDF export)

```bash
# Install resume-cli globally
npm i -g resume-cli
```

### Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Access Points
- **API Documentation**: http://localhost:8000/docs
- **User Interface**: http://localhost:8000/ui
- **Base Resume**: http://localhost:8000/resume

## 📁 Project Structure

```
resume_template/
├── app/                    # FastAPI application
│   ├── main.py           # Main application logic
│   ├── templates/        # HTML templates (UI)
│   └── test.json         # Test data
├── docs/                 # Documentation (this directory)
├── n8n_prompts/          # AI agent system prompts
├── theme-local/          # Custom resume theme
├── variants/             # Generated resume variants
├── out/                  # Exported files (HTML/PDF)
├── resume.json           # Base/original resume
├── approvals.json        # Approval status tracking
└── requirements.txt      # Python dependencies
```

## 🎯 Key Features

### 1. Variant Management
- Create multiple tailored resume variants
- Store full JSON resumes (not diffs)
- Track company-specific metadata
- Support for bulk operations

### 2. AI Integration
- **Job Match Analyzer**: Analyzes candidate-job fit
- **Resume Writer**: Creates tailored resumes based on analysis
- **Truthfulness Guardrails**: Prevents fabrication of experience
- **Metadata Tracking**: Records all AI modifications

### 3. Export System
- **HTML Export**: Interactive preview with AI edit highlighting
- **PDF Export**: Professional PDF generation
- **Custom Themes**: Local and elegant theme support
- **Custom Naming**: `Abhijith_sivadas_moothedath_{company}.pdf`

### 4. Approval Workflow
- **UI Review**: Visual interface for variant approval
- **Status Tracking**: draft|approved|rejected states
- **n8n Integration**: Automated polling for approved variants
- **Interview Prep**: Detailed gap analysis and preparation tips

## 📖 Documentation Structure

This documentation is organized into the following sections:

- **[API Documentation](./API.md)**: Complete API reference with examples
- **[Architecture Overview](./ARCHITECTURE.md)**: System design and component interactions
- **[Development Guide](./DEVELOPMENT.md)**: Setup, testing, and contribution guidelines

## 🔧 Configuration

### Environment Variables
- `PORT`: Server port (default: 8000)
- `VARIANT_DIR`: Directory for storing variants (default: ./variants)
- `OUT_DIR`: Directory for exports (default: ./out)

### Customization
- **Resume Theme**: Modify `theme-local/template.hbs` for custom styling
- **AI Prompts**: Update `n8n_prompts/` for different tailoring strategies
- **API Endpoints**: Extend `app/main.py` for additional functionality

## 🤝 Integration

### n8n Workflows
The project includes comprehensive n8n integration:
- **Agent Prompts**: System prompts for AI agents
- **API Schema**: JSON schema for variant creation
- **Workflow Documentation**: Detailed process diagrams

### External Systems
- **Resume CLI**: For PDF/HTML generation
- **FastAPI**: RESTful API with automatic documentation
- **Jinja2**: Template engine for UI rendering

## 📊 Monitoring

### Key Metrics
- Variant creation success rate
- Export completion times
- Approval workflow efficiency
- AI agent performance

### Logging
- API request/response logging
- Error tracking and debugging
- Performance monitoring

## 🚀 Next Steps

1. **Explore the API**: Check out [API Documentation](./API.md)
2. **Understand Architecture**: Read [Architecture Overview](./ARCHITECTURE.md)
3. **Start Developing**: Follow [Development Guide](./DEVELOPMENT.md)
4. **Set up n8n**: Configure automated workflows using provided prompts

## 📞 Support

For questions or issues:
- Review the existing documentation
- Check the API documentation for endpoint details
- Examine n8n prompts for workflow customization
- Review the architecture for system understanding

---

*Last updated: 2025-01-17*