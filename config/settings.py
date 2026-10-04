"""Application settings and configuration for JobResumeMatcher."""

import os
from pathlib import Path

# --- DIRECTORY PATHS ---
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
RESUME_DIR = BASE_DIR / "resume"

# Ensure runtime directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
RESUME_DIR.mkdir(parents=True, exist_ok=True)

# --- FILE PATHS ---
RESUME_PDF_PATH = RESUME_DIR / "resume.pdf"
MASTER_CSV_PATH = REPORTS_DIR / "all_jobs_history.csv"
RANKED_CSV_PATH = REPORTS_DIR / "ai_ranked_jobs.csv"
RANKED_HTML_PATH = REPORTS_DIR / "ai_ranked_jobs.html"
TIMESTAMP_FILE = BASE_DIR / "last_run_timestamp.txt"

# --- SCRAPER CONFIGURATION ---
SEARCH_TERM = "Software Architect"
LOCATION = "Hyderabad, India"
RESULTS_LIMIT = 30
SCRAPE_SITES = ["linkedin", "glassdoor"]
COUNTRY_INDEED = "india"
LINKEDIN_FETCH_DESCRIPTION = True

# --- LOCAL AI CONFIGURATION (OLLAMA) ---
MODEL_NAME = "qwen2.5-coder:14b-instruct-q8_0"
MAX_DESCRIPTION_CHARS = 5000  # Cap overly long descriptions to prevent LLM context stalls
DEFAULT_TIMEOUT_SECONDS = 90  # Prevent infinite hangs if Ollama server stalls
MODEL_TEMPERATURE = 0.1
MODEL_NUM_CTX = 8192
MODEL_NUM_PREDICT = 600       # Cap output tokens to prevent runaway generation loops

# --- REPORT SCHEMA ---
REPORT_COLUMNS = [
    'ai_match_score',
    'site_name',
    'title',
    'company',
    'location',
    'job_url',
    'matching_strengths',
    'missing_requirements'
]
