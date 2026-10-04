# 🎯 AI Job Resume Matcher & Application Tracker

An automated, privacy-first job hunting pipeline that scrapes fresh job listings from **LinkedIn** and **Glassdoor**, evaluates candidate fit against your resume using a **local Ollama LLM**, ranks opportunities by AI match score, and generates an **interactive HTML dashboard** with persistent click-to-apply tracking.

---

## ✨ Features

- **⚡ Dynamic Smart Lookback**: Automatically computes hours elapsed since your last run so you never miss fresh job postings and never waste time re-scraping duplicates.
- **🤖 100% Local & Private AI Evaluation**:
  - Uses local LLMs via [Ollama](https://ollama.ai) (default: `qwen2.5-coder:14b-instruct-q8_0`, or any model like `llama3.2`, `mistral`, `gemma2`).
  - Zero API fees and completely private—your resume and job data never leave your computer.
  - Generates objective fit scores (0–100%), matching strengths (`✓`), and missing requirements (`⚠`).
- **📊 Daily History & Deduplication**:
  - Automatically writes dated daily reports (`reports/ai_ranked_jobs_YYYY-MM-DD.csv`).
  - Preserves raw scraping archives in `reports/all_jobs_history.csv`.
  - Running multiple times on the same day cleanly merges new listings into that day's report without duplicates.
- **🌐 Interactive Browser Dashboard (`reports/ai_ranked_jobs.html`)**:
  - **Click-to-Apply Tracking**: Clicking **"Apply on LinkedIn/Glassdoor ↗"** opens the job posting in a new tab and automatically marks the posting as **Applied** with an exact timestamp.
  - **Persistent State**: Application status is stored in browser `localStorage`, surviving browser restarts and carrying over across daily reports for matching jobs.
  - **Focus Mode Filters**: Instant search by keywords/skills, filter tabs for **All**, **Unapplied Only** (rapid apply mode), and **Applied**, plus minimum match score thresholds (85%+, 80%+, 70%+).
  - **Export to CSV**: One-click download of all applied jobs with applied timestamps for recordkeeping.
- **📁 Modular Architecture**: Clean separation into `config/`, `common/`, `scripts/`, `reports/`, and `resume/`.

---

## 📁 Project Structure

```
JobResumeMatcher/
├── config/
│   ├── __init__.py
│   └── settings.py              # Central settings (paths, search term, location, model parameters)
├── common/
│   ├── __init__.py
│   ├── commons.py               # Core utilities (PDF extraction, Ollama client, scoring helpers)
│   └── report_generator.py      # Standalone & integrated HTML report generator
├── scripts/
│   ├── __init__.py
│   ├── main.py                  # Main scraping and AI evaluation pipeline
│   └── retry_evaluation.py      # Retries missing/failed AI evaluations from master history
├── reports/                     # Output directory for all reports and scraping history
│   ├── all_jobs_history.csv     # Master archive of raw scraped jobs
│   ├── ai_ranked_jobs.csv       # Latest ranked CSV
│   ├── ai_ranked_jobs.html      # Latest interactive HTML dashboard
│   ├── ai_ranked_jobs_YYYY-MM-DD.csv
│   └── ai_ranked_jobs_YYYY-MM-DD.html
├── resume/                      # Folder for candidate resume PDF files
│   └── pradeep_software_architect_ai.pdf
├── requirements.txt             # Python dependencies
├── last_run_timestamp.txt       # Checkpoint tracking last successful scrape timestamp
└── main.py                      # Root convenience forwarder (runs scripts.main)
```

---

## 🚀 Getting Started

### 1. Prerequisites

1. **Python 3.10+** installed.
2. **Ollama** installed and running:
   - macOS / Linux: `curl -fsSL https://ollama.com/install.sh | sh` or `brew install ollama`
   - Windows: Download from [ollama.ai](https://ollama.ai)
3. Download an Ollama model (default is `qwen2.5-coder:14b-instruct-q8_0`, or use any model you prefer):
   ```bash
   ollama pull qwen2.5-coder:14b-instruct-q8_0
   ```
   *(For machines with 8GB RAM, you can use a lighter model like `llama3.2:3b` or `qwen2.5-coder:7b` by changing `MODEL_NAME` in `config/settings.py`)*

---

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd JobResumeMatcher
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate       # On macOS/Linux
   # .venv\Scripts\activate        # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

### 3. Add Your Resume

1. Place your resume PDF in the `resume/` directory:
   ```bash
   cp /path/to/your/resume.pdf resume/my_resume.pdf
   ```
2. Update the filename in `config/settings.py`:
   ```python
   RESUME_PDF_PATH = RESUME_DIR / "my_resume.pdf"
   ```

---

### 4. Configure Your Job Search

Open `config/settings.py` and customize your target role and location:

```python
# --- SCRAPER CONFIGURATION ---
SEARCH_TERM = "Software Architect"     # Role / target title
LOCATION = "Hyderabad, India"          # Location or "Remote"
RESULTS_LIMIT = 30                     # Max listings per platform
SCRAPE_SITES = ["linkedin", "glassdoor"] # Supported: linkedin, glassdoor, indeed, zip_recruiter
COUNTRY_INDEED = "india"               # Country code if using indeed
```

---

## 💻 Usage

### Run the Pipeline
Scrape new postings, run local AI resume-job matching, and generate today's ranked CSV & HTML dashboard:
```bash
python3 main.py
```
*(Or run directly via `python3 scripts/main.py`)*

### View the Interactive Dashboard
Open the generated HTML dashboard in your web browser:
```bash
open reports/ai_ranked_jobs.html
```

- Click **"Apply on LinkedIn/Glassdoor ↗"** on any job card to open the listing in a new tab. The card will automatically update to **Applied** with a timestamp.
- Switch to the **Unapplied** tab to see remaining openings you haven't applied to yet.
- Use the **Search Bar** to instantly filter by technology (e.g. `Kubernetes`, `AWS`, `Java`).
- Use the **Export Applied CSV** button at the top to download a timestamped record of all jobs you've applied for.

---

## 🛠️ Utility Scripts

### Re-evaluating Failed or Missing Listings
If an Ollama evaluation was interrupted or you want to evaluate previously scraped jobs:
```bash
python3 scripts/retry_evaluation.py
```

### Re-generating HTML Dashboards
To regenerate the interactive dashboard from any historical CSV file:
```bash
# Rebuild from the latest ranked CSV
python3 common/report_generator.py reports/ai_ranked_jobs.csv

# Rebuild from a specific day's CSV
python3 common/report_generator.py reports/ai_ranked_jobs_2026-10-02.csv
```

---

## ⚙️ Advanced Configuration (`config/settings.py`)

| Setting | Default | Description |
|---|---|---|
| `MODEL_NAME` | `qwen2.5-coder:14b-instruct-q8_0` | Local Ollama model used for semantic matching |
| `MODEL_TEMPERATURE` | `0.1` | Low temperature for consistent, objective evaluations |
| `MODEL_NUM_CTX` | `8192` | Context window size for handling full job descriptions |
| `MAX_DESCRIPTION_CHARS` | `5000` | Truncation safety cap to avoid context latency stalls |
| `DEFAULT_TIMEOUT_SECONDS` | `90` | Request timeout per job evaluation |
| `SCRAPE_SITES` | `["linkedin", "glassdoor"]` | Job platforms to search |

---

## 🛡️ Privacy & Compliance
- **Zero Cloud API Calls**: No data is sent to OpenAI, Anthropic, Google, or any external LLM provider.
- All resume parsing, job ranking, and click tracking happen **100% locally** on your machine.
- Local tracking state is stored in your browser's standard `localStorage`.

---

## 📄 License
MIT License. Free for personal and commercial use.
