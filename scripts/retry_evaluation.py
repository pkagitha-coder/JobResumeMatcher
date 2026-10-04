"""Retry evaluation for un-evaluated or failed job postings in the master archive."""

import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import time
import pandas as pd

from config.settings import (
    RESUME_PDF_PATH,
    MASTER_CSV_PATH,
    RANKED_CSV_PATH,
    MODEL_NAME,
)
from common.commons import (
    extract_text_from_pdf,
    ensure_model_exists,
    get_ai_evaluation,
    format_evaluation_result,
    save_ranked_report,
)


def evaluate_missing_jobs(
    master_csv_path=MASTER_CSV_PATH,
    resume_pdf_path=RESUME_PDF_PATH,
    ranked_csv_path=RANKED_CSV_PATH,
    model_name=MODEL_NAME
):
    master_csv_path = Path(master_csv_path)
    resume_pdf_path = Path(resume_pdf_path)

    # 1. Verify environment and files
    if not master_csv_path.exists():
        print(f"Error: {master_csv_path} does not exist yet. Run your main scraper script first.", flush=True)
        return

    try:
        resume_text = extract_text_from_pdf(resume_pdf_path)
    except Exception as e:
        print(f"Error loading resume: {e}", flush=True)
        return

    # 2. Check and pull the model if necessary
    if not ensure_model_exists(model_name):
        print("Aborting evaluation: Local AI engine is not available.", flush=True)
        return

    # 3. Read the master CSV tracking file
    df = pd.read_csv(master_csv_path)

    # 4. Initialize target evaluation columns if they do not exist yet
    for col in ['ai_match_score', 'matching_strengths', 'missing_requirements']:
        if col not in df.columns:
            df[col] = None

    # 5. Isolate rows where the score is missing, NaN, or explicitly 0 due to previous failures
    mask_to_evaluate = (
        df['ai_match_score'].isna() | (pd.to_numeric(df['ai_match_score'], errors='coerce') == 0)
    ) & df['description'].notna()
    jobs_to_evaluate = df[mask_to_evaluate]

    if jobs_to_evaluate.empty:
        print("All records in your history file already have valid AI evaluations. Nothing to process!", flush=True)
        return

    total = len(jobs_to_evaluate)
    print(f"Found {total} listing(s) missing AI evaluations. Processing now...", flush=True)

    # 6. Evaluate skipped entries loop with real-time feedback and incremental checkpointing
    try:
        for i, (idx, row) in enumerate(jobs_to_evaluate.iterrows(), 1):
            platform = str(row.get('site_name', 'UNKNOWN')).upper()
            title = row.get('title', 'Unknown Title')
            company = row.get('company', 'Unknown Company')
            print(f"[{i}/{total}] [{platform}] Evaluating: {title} at {company}...", end="", flush=True)

            start_t = time.time()
            result = get_ai_evaluation(resume_text, title, company, row.get('description', ''), model_name=model_name)
            elapsed = time.time() - start_t

            score, strengths, missing = format_evaluation_result(result)

            # Direct index assignment updates the master DataFrame in place
            df.at[idx, 'ai_match_score'] = score
            df.at[idx, 'matching_strengths'] = strengths
            df.at[idx, 'missing_requirements'] = missing

            print(f" Done ({elapsed:.1f}s, Score: {score})", flush=True)

            # Save incrementally after each row so progress is never lost even if interrupted
            df.to_csv(master_csv_path, index=False)

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user. Saving completed progress so far...", flush=True)
    finally:
        # 7. Write clean changes back to the master historical tracker
        df.to_csv(master_csv_path, index=False)
        print(f"Updated master history tracker: {master_csv_path}", flush=True)

        # 8. Re-generate the clean sorted active recommendation sheet
        save_ranked_report(df, ranked_csv_path)


if __name__ == "__main__":
    evaluate_missing_jobs()
