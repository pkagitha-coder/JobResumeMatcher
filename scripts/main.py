"""Main scraping and AI evaluation pipeline for JobResumeMatcher."""

import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import csv
import time
from datetime import datetime
import pandas as pd
from jobspy import scrape_jobs

from config.settings import (
    RESUME_PDF_PATH,
    MASTER_CSV_PATH,
    RANKED_CSV_PATH,
    RANKED_HTML_PATH,
    TIMESTAMP_FILE,
    SEARCH_TERM,
    LOCATION,
    RESULTS_LIMIT,
    SCRAPE_SITES,
    COUNTRY_INDEED,
    LINKEDIN_FETCH_DESCRIPTION,
    MODEL_NAME,
)
from common.commons import (
    extract_text_from_pdf,
    ensure_model_exists,
    get_existing_job_ids,
    get_ai_evaluation,
    format_evaluation_result,
    get_daily_ranked_csv_path,
    save_ranked_report,
)


def get_hours_since_last_run(timestamp_path):
    """Calculates hours elapsed since the last run. Defaults to 24 if no file exists."""
    now = datetime.now()
    timestamp_path = Path(timestamp_path)
    if not timestamp_path.exists():
        print("No previous runtime tracked. Defaulting search window to the last 24 hours.", flush=True)
        return 24

    try:
        with open(timestamp_path, "r") as f:
            last_run_str = f.read().strip()
        last_run_dt = datetime.fromisoformat(last_run_str)
        elapsed_seconds = (now - last_run_dt).total_seconds()
        elapsed_hours = max(1, int(elapsed_seconds / 3600))  # Minimum of 1 hour lookback

        print(f"Last runtime was: {last_run_dt.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"Time elapsed: {elapsed_hours} hours. Setting lookback window to match.", flush=True)
        return elapsed_hours
    except Exception as e:
        print(f"Error parsing timestamp file ({e}). Defaulting search window to 24 hours.", flush=True)
        return 24


def save_current_runtime(timestamp_path):
    """Saves the current timestamp to mark a successful run."""
    with open(timestamp_path, "w") as f:
        f.write(datetime.now().isoformat())


def main():
    # 1. Read Resume Text
    try:
        resume_text = extract_text_from_pdf(RESUME_PDF_PATH)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return

    # 2. Check and pull the model if necessary
    if not ensure_model_exists(MODEL_NAME):
        print("Aborting: Local AI engine is not available.", flush=True)
        return

    # 3. Determine dynamically how many hours old the search should look back
    hours_lookback = get_hours_since_last_run(TIMESTAMP_FILE)

    # 4. Find already scraped job IDs to avoid duplicate processing
    existing_ids = get_existing_job_ids(MASTER_CSV_PATH)

    # 5. Scrape fresh postings with the dynamic hourly window
    print(f"Scraping {SCRAPE_SITES} for '{SEARCH_TERM}' looking back {hours_lookback} hours...", flush=True)
    try:
        live_jobs = scrape_jobs(
            site_name=SCRAPE_SITES,
            search_term=SEARCH_TERM,
            location=LOCATION,
            results_wanted=RESULTS_LIMIT,
            hours_old=hours_lookback,
            linkedin_fetch_description=LINKEDIN_FETCH_DESCRIPTION,
            country_indeed=COUNTRY_INDEED
        )
    except Exception as e:
        print(f"Scraping failed: {e}", flush=True)
        return

    if live_jobs.empty:
        print("No jobs found across selected platforms within this dynamic window.", flush=True)
        save_current_runtime(TIMESTAMP_FILE)
        return

    # 6. Filter out duplicates based on the 'id' field
    live_jobs['id'] = live_jobs['id'].astype(str)
    new_jobs = live_jobs[~live_jobs['id'].isin(existing_ids)].copy()

    print(f"Found {len(live_jobs)} total listings. {len(new_jobs)} are brand new.", flush=True)

    if new_jobs.empty:
        print("No new unique jobs to evaluate today.", flush=True)
        save_current_runtime(TIMESTAMP_FILE)
        return

    # 7. Append new raw items to the master archive
    master_path = Path(MASTER_CSV_PATH)
    file_exists = master_path.exists()
    new_jobs.to_csv(
        master_path,
        mode='a',
        header=not file_exists,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC,
        escapechar="\\"
    )

    # 8. Run AI Matching on the new rows using latest prompt & keyword matching
    new_jobs = new_jobs.dropna(subset=['description']).copy()
    scores, pros, cons = [], [], []

    total_new = len(new_jobs)
    print(f"Analyzing {total_new} new listing(s) with local {MODEL_NAME}...", flush=True)
    for i, (idx, row) in enumerate(new_jobs.iterrows(), 1):
        platform = str(row.get('site_name', 'UNKNOWN')).upper()
        title = row.get('title', 'Unknown Title')
        company = row.get('company', 'Unknown Company')
        print(f"[{i}/{total_new}] [{platform}] Assessing: {title} at {company}...", end="", flush=True)

        start_t = time.time()
        result = get_ai_evaluation(resume_text, title, company, row['description'], model_name=MODEL_NAME)
        elapsed = time.time() - start_t

        score, strengths, missing = format_evaluation_result(result)

        scores.append(score)
        pros.append(strengths)
        cons.append(missing)

        print(f" Done ({elapsed:.1f}s, Score: {score})", flush=True)

    # 9. Package and write the clean UI report out
    new_jobs['ai_match_score'] = scores
    new_jobs['matching_strengths'] = pros
    new_jobs['missing_requirements'] = cons

    daily_ranked_path = get_daily_ranked_csv_path()
    save_ranked_report(new_jobs, output_path=daily_ranked_path, merge_existing=True, update_latest=True)

    # 10. Update the timestamp checkpoint only after completing a successful run
    save_current_runtime(TIMESTAMP_FILE)
    daily_html_path = daily_ranked_path.with_suffix(".html")
    print("\nEvaluation finished successfully! Timestamp updated.", flush=True)
    print(f"📊 Daily CSV:  {daily_ranked_path}", flush=True)
    print(f"🌐 Daily HTML: {daily_html_path}", flush=True)
    print(f"🌐 Latest HTML (open in browser): {RANKED_HTML_PATH}\n", flush=True)


if __name__ == "__main__":
    main()
