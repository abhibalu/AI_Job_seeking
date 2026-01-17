"""
TailorAI FastAPI Application

REST API for job evaluation pipeline.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import jobs, evaluations, parse, tasks, resumes

app = FastAPI(
    title="TailorAI API",
    description="Job evaluation and resume tailoring API",
    version="0.1.0",
)

from agents.database import init_database

@app.on_event("startup")
def on_startup():
    init_database()

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .middleware import LangfuseMiddleware
app.add_middleware(LangfuseMiddleware)

# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluations"])
app.include_router(parse.router, prefix="/api/parse", tags=["Parse"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Resumes"])

from .routes import pdf
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF Generation"])


@app.get("/")
def root():
    return {"message": "TailorAI API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
