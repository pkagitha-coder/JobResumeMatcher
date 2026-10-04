"""Common helper functions and evaluation logic for JobResumeMatcher."""

import os
import sys
import json
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime
import pandas as pd
from pypdf import PdfReader
import ollama

from config.settings import (
    RESUME_PDF_PATH,
    MASTER_CSV_PATH,
    RANKED_CSV_PATH,
    RANKED_HTML_PATH,
    REPORTS_DIR,
    MODEL_NAME,
    MAX_DESCRIPTION_CHARS,
    DEFAULT_TIMEOUT_SECONDS,
    MODEL_TEMPERATURE,
    MODEL_NUM_CTX,
    MODEL_NUM_PREDICT,
    REPORT_COLUMNS,
)
from common.report_generator import generate_html_report


def extract_text_from_pdf(pdf_path=RESUME_PDF_PATH):
    """Extracts raw text from a local PDF resume."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Resume not found at {pdf_path}. Please place your resume in the resume/ folder.")

    print(f"Reading resume from {pdf_path}...", flush=True)
    reader = PdfReader(str(pdf_path))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def ensure_model_exists(model_name=MODEL_NAME):
    """Checks if the local model exists; pulls it automatically if it's missing."""
    print(f"Verifying local AI model '{model_name}'...", flush=True)
    try:
        local_models = ollama.list()
        downloaded_names = [m.get('model', '') for m in local_models.get('models', [])]

        if model_name in downloaded_names or any(model_name in name for name in downloaded_names):
            print("Model found and ready.", flush=True)
            return True

        print(f"Model '{model_name}' not found locally. Attempting to download now...", flush=True)
        ollama.pull(model_name)
        print("Model downloaded successfully!", flush=True)
        return True
    except Exception as e:
        print(f"Ollama connection error: {e}", flush=True)
        print("Make sure the Ollama application is launched and running in your taskbar.", flush=True)
        return False


def get_ai_evaluation(resume_text, job_title, company, description, model_name=MODEL_NAME, timeout=DEFAULT_TIMEOUT_SECONDS):
    """Evaluates candidate fit against a job opening using LLM semantic understanding."""
    clean_desc = (str(description) if description is not None else "").strip()
    if len(clean_desc) > MAX_DESCRIPTION_CHARS:
        clean_desc = clean_desc[:MAX_DESCRIPTION_CHARS] + "\n[Description truncated for evaluation length]"

    system_instruction = (
        "You are an exceptionally objective, data-driven technical recruiter system. "
        "Your task is to analyze a candidate's resume text against a specific job opening description "
        "and calculate an accurate, contextual job fit evaluation.\n\n"
        "EVALUATION GUIDELINES:\n"
        "1. FACTUAL GROUNDING: Base findings strictly on the factual text provided. Do not invent details.\n"
        "2. ACRONYM & SYNONYM EQUIVALENCE: Treat standard technical abbreviations and full names as equivalent "
        "(e.g., AWS = Amazon Web Services, K8s = Kubernetes, CI/CD = Continuous Integration / Continuous Deployment, "
        "GCP = Google Cloud Platform, TS = TypeScript, JS = JavaScript, etc.).\n"
        "3. ACCURATE PROS & CONS: If a skill, tool, or equivalent experience is present in the resume, you are strictly "
        "FORBIDDEN from listing it under 'cons'. List it under 'pros'. Only list genuine gaps or missing requirements under 'cons'.\n"
        "4. SCHEMA ENFORCEMENT: Output a single, complete, valid JSON object matching the requested schema. "
        "Do not include conversational phrases or markdown code blocks."
    )

    user_prompt = f"""
        Evaluate the candidate for this job opening.

        JOB OPENING:
        Title: {job_title}
        Company: {company}
        Description:
        \"\"\"{clean_desc}\"\"\"

        CANDIDATE RESUME:
        \"\"\"{resume_text}\"\"\"

        Respond with this exact JSON schema:
        {{
            "score": 85,
            "pros": ["bullet 1 explaining matched skill or strength", "bullet 2"],
            "cons": ["bullet 1 explaining actual missing requirement or gap", "bullet 2"]
        }}
        """

    fallback_response = {"score": 0, "pros": ["Skipped due to parsing"], "cons": ["Formatting error"]}

    try:
        client = ollama.Client(timeout=timeout)
        response = client.chat(
            model=model_name,
            format='json',
            messages=[
                {'role': 'system', 'content': system_instruction},
                {'role': 'user', 'content': user_prompt}
            ],
            options={
                'temperature': MODEL_TEMPERATURE,
                'num_ctx': MODEL_NUM_CTX,
                'num_predict': MODEL_NUM_PREDICT
            }
        )

        text = response['message']['content'].strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) > 2 and (lines[0].startswith("```json") or lines[0].startswith("```")):
                text = "\n".join(lines[1:-1]).strip()

        if not text.endswith("}"):
            print("Warning: Model returned a truncated response string. Attempting basic structural fix...", flush=True)
            if ']' in text and not text.endswith("]}"):
                text += "}"
            else:
                return fallback_response

        return json.loads(text)

    except json.JSONDecodeError as je:
        print(f"JSON Structure error caught: {je}. Raw output was: {text[:100]}...", flush=True)
        return fallback_response
    except Exception as e:
        print(f"Evaluation error: {e}", flush=True)
        return {"score": 0, "pros": ["Evaluation error"], "cons": [str(e)]}


def format_evaluation_result(result):
    """Formats an AI evaluation result dict into (score, matching_strengths, missing_requirements)."""
    score = result.get("score", 0)
    strengths = ", ".join(result.get("pros", []))
    missing = ", ".join(result.get("cons", []))
    return score, strengths, missing


def get_existing_job_ids(csv_path=MASTER_CSV_PATH):
    """Reads the master CSV to collect job IDs we have already processed."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return set()
    try:
        df = pd.read_csv(csv_path)
        if 'id' in df.columns:
            return set(df['id'].dropna().astype(str).tolist())
    except Exception:
        pass
    return set()


def get_daily_ranked_csv_path(date=None):
    """Returns the date-stamped CSV path in REPORTS_DIR, e.g. 'reports/ai_ranked_jobs_YYYY-MM-DD.csv'."""
    if date is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif isinstance(date, (datetime, pd.Timestamp)):
        date_str = date.strftime("%Y-%m-%d")
    else:
        date_str = str(date)
    return REPORTS_DIR / f"ai_ranked_jobs_{date_str}.csv"


def save_ranked_report(df, output_path=None, merge_existing=True, update_latest=True):
    """Sorts evaluated jobs by AI match score and saves both ranked CSV and HTML reports.

    If output_path is None, defaults to the daily ranked CSV path in REPORTS_DIR.
    If merge_existing is True and output_path exists (and is not RANKED_CSV_PATH), merges new results
    with existing listings for that day (deduplicating by job_url/title+company) and re-sorts.
    If update_latest is True and output_path is not RANKED_CSV_PATH, also updates RANKED_CSV_PATH & RANKED_HTML_PATH.
    """
    if output_path is None:
        output_path = get_daily_ranked_csv_path()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    available_columns = [col for col in REPORT_COLUMNS if col in df.columns]
    report_df = df[available_columns].copy()

    # Filter for valid numeric scores
    if 'ai_match_score' in report_df.columns:
        scores_numeric = pd.to_numeric(report_df['ai_match_score'], errors='coerce')
        report_df = report_df[scores_numeric.notna()].copy()

    # Merge with existing file if it exists and merge_existing is enabled
    is_same_as_latest = output_path.resolve() == RANKED_CSV_PATH.resolve()
    if merge_existing and not is_same_as_latest and output_path.exists():
        try:
            existing_df = pd.read_csv(output_path)
            existing_cols = [col for col in REPORT_COLUMNS if col in existing_df.columns]
            existing_df = existing_df[existing_cols]
            combined = pd.concat([existing_df, report_df], ignore_index=True)

            # Deduplicate (keep latest evaluation)
            if 'job_url' in combined.columns:
                has_url = combined['job_url'].notna() & (combined['job_url'].astype(str).str.strip() != "")
                with_url = combined[has_url].drop_duplicates(subset=['job_url'], keep='last')
                without_url = combined[~has_url]
                if 'title' in without_url.columns and 'company' in without_url.columns:
                    without_url = without_url.drop_duplicates(subset=['title', 'company'], keep='last')
                combined = pd.concat([with_url, without_url], ignore_index=True)
            elif 'title' in combined.columns and 'company' in combined.columns:
                combined = combined.drop_duplicates(subset=['title', 'company'], keep='last')

            report_df = combined
        except Exception as e:
            print(f"Warning: Could not read existing {output_path} to merge ({e}). Overwriting.", flush=True)

    # Sort descending by numeric score
    if 'ai_match_score' in report_df.columns:
        scores_numeric = pd.to_numeric(report_df['ai_match_score'], errors='coerce')
        report_df['_temp_score'] = scores_numeric
        report_df = report_df.sort_values(by='_temp_score', ascending=False)
        report_df = report_df.drop(columns=['_temp_score'])

    cols_to_write = [col for col in REPORT_COLUMNS if col in report_df.columns]
    report_df = report_df[cols_to_write]
    report_df.to_csv(output_path, index=False)
    print(f"Ranked CSV saved to: {output_path}", flush=True)

    # Automatically generate corresponding interactive HTML report
    try:
        output_html_path = output_path.with_suffix(".html")
        generate_html_report(report_df, output_html_path)
    except Exception as e:
        print(f"Warning: Failed to generate HTML report for {output_path} ({e})", flush=True)

    # Keep default reports/ai_ranked_jobs.csv and reports/ai_ranked_jobs.html updated
    if update_latest and not is_same_as_latest:
        report_df.to_csv(RANKED_CSV_PATH, index=False)
        print(f"Latest ranked CSV updated at: {RANKED_CSV_PATH}", flush=True)
        try:
            generate_html_report(report_df, RANKED_HTML_PATH)
        except Exception as e:
            print(f"Warning: Failed to generate latest HTML report ({e})", flush=True)

    return report_df
