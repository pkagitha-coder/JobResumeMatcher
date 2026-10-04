"""HTML Report Generator for Job Resume Matcher.

Generates self-contained interactive HTML dashboards with click/application tracking,
score filtering, search, and localStorage persistence.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import html
from datetime import datetime
import pandas as pd

from config.settings import RANKED_HTML_PATH, REPORTS_DIR


def parse_bullet_list(text):
    """Splits comma-separated or newline-separated points into a clean list."""
    if not text or pd.isna(text):
        return []
    text_str = str(text).strip()
    if not text_str or text_str.lower() in ("none", "n/a", "evaluation error"):
        return []

    # If it's already bulleted with newlines or semicolons, split by that
    if "\n" in text_str:
        raw_items = text_str.split("\n")
    elif "; " in text_str:
        raw_items = text_str.split("; ")
    else:
        # Standard format in this project is comma-separated sentences
        raw_items = text_str.split(", ")

    cleaned = []
    for item in raw_items:
        clean = item.strip().lstrip("•-* \t")
        if clean:
            cleaned.append(clean)
    return cleaned


def get_score_class(score):
    """Returns CSS class based on numeric AI match score."""
    try:
        val = float(score)
        if val >= 85:
            return "score-high"
        elif val >= 75:
            return "score-medium"
        elif val >= 60:
            return "score-moderate"
        else:
            return "score-low"
    except Exception:
        return "score-unknown"


def generate_html_content(df, title_date_str=None):
    """Generates a complete, self-contained HTML page with CSS and JS."""
    if title_date_str is None:
        title_date_str = datetime.now().strftime("%Y-%m-%d")

    records = df.to_dict(orient="records") if not df.empty else []

    # Calculate high-level metrics
    total_jobs = len(records)
    scores = [r.get("ai_match_score") for r in records if pd.notna(r.get("ai_match_score"))]
    valid_scores = [float(s) for s in scores if isinstance(s, (int, float, str)) and str(s).isdigit()]
    avg_score = round(sum(valid_scores) / len(valid_scores)) if valid_scores else 0

    # Build job cards HTML
    cards_html = []
    for idx, row in enumerate(records):
        score_val = row.get("ai_match_score", 0)
        try:
            score_num = int(float(score_val))
        except (ValueError, TypeError):
            score_num = 0

        score_cls = get_score_class(score_num)
        job_title = html.escape(str(row.get("title", "Unknown Title")))
        company = html.escape(str(row.get("company", "Unknown Company")))
        location = html.escape(str(row.get("location", "Location Not Specified")))
        site_name = html.escape(str(row.get("site_name", "Web")).capitalize())
        raw_url = str(row.get("job_url", "")).strip()
        job_url = html.escape(raw_url)

        strengths = parse_bullet_list(row.get("matching_strengths", ""))
        missing = parse_bullet_list(row.get("missing_requirements", ""))

        strengths_html = "".join([f"<li>{html.escape(s)}</li>" for s in strengths]) if strengths else "<li>None highlighted</li>"
        missing_html = "".join([f"<li>{html.escape(m)}</li>" for m in missing]) if missing else "<li>None detected</li>"

        # Unique identifier for the card in DOM
        card_id = f"job-card-{idx}"

        cards_html.append(f"""
        <article class="job-card" id="{card_id}" data-url="{job_url}" data-score="{score_num}" data-site="{site_name.lower()}">
            <header class="card-header">
                <div class="score-badge {score_cls}">
                    <span class="score-num">{score_num}%</span>
                    <span class="score-lbl">Match</span>
                </div>
                <div class="job-heading">
                    <h2 class="job-title">{job_title}</h2>
                    <div class="job-meta">
                        <span class="company-name">🏢 {company}</span>
                        <span class="location-name">📍 {location}</span>
                        <span class="site-pill site-{site_name.lower()}">{site_name}</span>
                    </div>
                </div>
                <div class="card-actions">
                    <a href="{job_url}" target="_blank" rel="noopener noreferrer" class="btn-apply" data-action="apply">
                        Apply on {site_name} ↗
                    </a>
                    <label class="apply-checkbox-label">
                        <input type="checkbox" class="applied-toggle" data-target="{card_id}">
                        <span class="applied-checkbox-custom"></span>
                        <span class="applied-status-text">Applied</span>
                    </label>
                    <div class="applied-time-badge" style="display:none;"></div>
                </div>
            </header>

            <div class="analysis-details">
                <div class="analysis-col strengths-col">
                    <h3 class="col-title pros-title">✓ Matching Strengths ({len(strengths)})</h3>
                    <ul class="bullet-list pros-list">
                        {strengths_html}
                    </ul>
                </div>
                <div class="analysis-col missing-col">
                    <h3 class="col-title cons-title">⚠ Missing Requirements ({len(missing)})</h3>
                    <ul class="bullet-list cons-list">
                        {missing_html}
                    </ul>
                </div>
            </div>
        </article>
        """)

    all_cards_str = "\n".join(cards_html) if cards_html else "<div class='empty-state'>No ranked jobs found.</div>"

    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Ranked Jobs ({title_date_str}) - Job Resume Matcher</title>
    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #26354a;
            --bg-card-applied: #122822;
            --border-color: #334155;
            --border-applied: #059669;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --primary-hover: #0284c7;
            --success: #10b981;
            --success-bg: rgba(16, 185, 129, 0.12);
            --warning: #f59e0b;
            --warning-bg: rgba(245, 158, 11, 0.12);
            --danger: #ef4444;
            --danger-bg: rgba(239, 68, 68, 0.12);
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-family);
            background-color: var(--bg-body);
            color: var(--text-main);
            line-height: 1.5;
            padding: 24px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* Header & Dashboard Stats */
        header.dashboard-header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}

        .top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 20px;
        }}

        .header-title h1 {{
            font-size: 1.6rem;
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .header-title .date-badge {{
            font-size: 0.85rem;
            background-color: #334155;
            color: #cbd5e1;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 500;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }}

        .metric-card {{
            background-color: rgba(30, 41, 59, 0.7);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
        }}

        .metric-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .metric-value.applied {{
            color: var(--success);
        }}

        .metric-value.unapplied {{
            color: var(--warning);
        }}

        .metric-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-top: 4px;
        }}

        /* Controls / Filter Bar */
        .filter-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 24px;
        }}

        .search-box {{
            flex: 1 1 250px;
            position: relative;
        }}

        .search-box input {{
            width: 100%;
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: #ffffff;
            padding: 10px 14px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--primary);
        }}

        .tab-group {{
            display: flex;
            background-color: #0f172a;
            border-radius: 6px;
            padding: 3px;
            border: 1px solid var(--border-color);
        }}

        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 6px 14px;
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .tab-btn.active {{
            background-color: var(--primary);
            color: #0f172a;
        }}

        .select-filter {{
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: #ffffff;
            padding: 9px 12px;
            font-size: 0.85rem;
            outline: none;
            cursor: pointer;
        }}

        .btn-utility {{
            background-color: #334155;
            color: #e2e8f0;
            border: none;
            border-radius: 6px;
            padding: 9px 14px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }}

        .btn-utility:hover {{
            background-color: #475569;
        }}

        /* Job Cards */
        .jobs-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .job-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-left: 5px solid var(--primary);
            border-radius: 10px;
            padding: 20px;
            transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        }}

        .job-card:hover {{
            border-color: #475569;
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }}

        .job-card.is-applied {{
            border-left-color: var(--border-applied);
            background-color: var(--bg-card-applied);
        }}

        .card-header {{
            display: flex;
            gap: 16px;
            align-items: flex-start;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }}

        /* Score Badge */
        .score-badge {{
            min-width: 68px;
            height: 68px;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-weight: 700;
        }}

        .score-high {{
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: #ffffff;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
        }}

        .score-medium {{
            background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
            color: #ffffff;
        }}

        .score-moderate {{
            background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
            color: #ffffff;
        }}

        .score-low {{
            background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
            color: #ffffff;
        }}

        .score-num {{
            font-size: 1.4rem;
            line-height: 1;
        }}

        .score-lbl {{
            font-size: 0.65rem;
            text-transform: uppercase;
            margin-top: 2px;
            opacity: 0.85;
        }}

        .job-heading {{
            flex: 1 1 300px;
        }}

        .job-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 6px;
        }}

        .job-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            font-size: 0.9rem;
            color: var(--text-muted);
            align-items: center;
        }}

        .company-name {{
            font-weight: 600;
            color: #e2e8f0;
        }}

        .site-pill {{
            font-size: 0.75rem;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}

        .site-linkedin {{
            background-color: #0a66c2;
            color: #ffffff;
        }}

        .site-glassdoor {{
            background-color: #0caa41;
            color: #ffffff;
        }}

        .card-actions {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            min-width: 170px;
        }}

        .btn-apply {{
            display: inline-block;
            background-color: var(--primary);
            color: #0f172a;
            font-weight: 600;
            font-size: 0.95rem;
            padding: 8px 18px;
            border-radius: 6px;
            text-decoration: none;
            transition: all 0.2s ease;
            text-align: center;
            width: 100%;
        }}

        .btn-apply:hover {{
            background-color: var(--primary-hover);
            color: #ffffff;
            transform: translateY(-1px);
        }}

        .apply-checkbox-label {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            color: var(--text-muted);
            cursor: pointer;
            user-select: none;
        }}

        .applied-toggle {{
            accent-color: var(--success);
            cursor: pointer;
            width: 16px;
            height: 16px;
        }}

        .applied-time-badge {{
            font-size: 0.72rem;
            color: var(--success);
            background-color: var(--success-bg);
            padding: 2px 6px;
            border-radius: 4px;
        }}

        /* Pros and Cons */
        .analysis-details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 16px;
            border-top: 1px solid var(--border-color);
            padding-top: 14px;
        }}

        .col-title {{
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }}

        .pros-title {{
            color: var(--success);
        }}

        .cons-title {{
            color: var(--warning);
        }}

        .bullet-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .bullet-list li {{
            font-size: 0.88rem;
            color: #cbd5e1;
            position: relative;
            padding-left: 18px;
            line-height: 1.4;
        }}

        .pros-list li::before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: var(--success);
            font-weight: bold;
        }}

        .cons-list li::before {{
            content: "•";
            position: absolute;
            left: 2px;
            color: var(--warning);
            font-size: 1.1rem;
            line-height: 1;
        }}

        .empty-state {{
            text-align: center;
            padding: 48px;
            color: var(--text-muted);
            font-size: 1.1rem;
            background-color: var(--bg-card);
            border-radius: 10px;
            border: 1px dashed var(--border-color);
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 12px;
            }}
            .card-actions {{
                align-items: stretch;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Top Dashboard Header -->
        <header class="dashboard-header">
            <div class="top-row">
                <div class="header-title">
                    <h1>🚀 Job Resume Matcher <span class="date-badge">{title_date_str}</span></h1>
                </div>
                <div>
                    <button id="btn-export" class="btn-utility">📥 Export Applied CSV</button>
                    <button id="btn-reset" class="btn-utility" style="margin-left: 8px;">🔄 Reset Tracking</button>
                </div>
            </div>

            <!-- Real-time Stats Grid -->
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value" id="stat-total">{total_jobs}</div>
                    <div class="metric-label">Total Listings</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value applied" id="stat-applied">0</div>
                    <div class="metric-label">Applied</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value unapplied" id="stat-unapplied">{total_jobs}</div>
                    <div class="metric-label">Unapplied</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="stat-avg-score">{avg_score}%</div>
                    <div class="metric-label">Avg Match Score</div>
                </div>
            </div>
        </header>

        <!-- Search and Filters Bar -->
        <section class="filter-bar">
            <div class="search-box">
                <input type="text" id="filter-search" placeholder="🔍 Search title, company, skills, or location...">
            </div>

            <div class="tab-group" id="filter-tabs">
                <button class="tab-btn active" data-tab="all">All (<span id="count-all">{total_jobs}</span>)</button>
                <button class="tab-btn" data-tab="unapplied">Unapplied (<span id="count-unapplied">{total_jobs}</span>)</button>
                <button class="tab-btn" data-tab="applied">Applied (<span id="count-applied">0</span>)</button>
            </div>

            <select id="filter-score" class="select-filter">
                <option value="0">All Scores (0%+)</option>
                <option value="85">Top Match (85%+)</option>
                <option value="80">Good Fit (80%+)</option>
                <option value="70">Moderate Fit (70%+)</option>
            </select>

            <select id="filter-site" class="select-filter">
                <option value="all">All Sites</option>
                <option value="linkedin">LinkedIn</option>
                <option value="glassdoor">Glassdoor</option>
            </select>
        </section>

        <!-- Job Cards Container -->
        <main class="jobs-list" id="jobs-container">
            {all_cards_str}
        </main>
    </div>

    <!-- Client-side Tracker Script -->
    <script>
        (function() {{
            const STORAGE_KEY = 'job_resume_matcher_applied_records';

            function getStorage() {{
                try {{
                    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');
                }} catch (e) {{
                    return {{}};
                }}
            }}

            function saveStorage(data) {{
                try {{
                    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
                }} catch (e) {{
                    console.error('Failed to save to localStorage', e);
                }}
            }}

            function formatTime(isoStr) {{
                if (!isoStr) return '';
                const d = new Date(isoStr);
                return d.toLocaleDateString(undefined, {{ month: 'short', day: 'numeric' }}) + ' ' +
                       d.toLocaleTimeString(undefined, {{ hour: '2-digit', minute: '2-digit' }});
            }}

            function markJob(jobUrl, isApplied, timestamp = null) {{
                if (!jobUrl) return;
                const store = getStorage();
                if (isApplied) {{
                    store[jobUrl] = {{
                        applied: true,
                        applied_at: timestamp || new Date().toISOString()
                    }};
                }} else {{
                    delete store[jobUrl];
                }}
                saveStorage(store);
                refreshUI();
            }}

            function refreshUI() {{
                const store = getStorage();
                const cards = document.querySelectorAll('.job-card');
                let appliedCount = 0;
                let unappliedCount = 0;

                cards.forEach(card => {{
                    const url = card.getAttribute('data-url');
                    const checkbox = card.querySelector('.applied-toggle');
                    const timeBadge = card.querySelector('.applied-time-badge');
                    const record = store[url];

                    if (record && record.applied) {{
                        appliedCount++;
                        card.classList.add('is-applied');
                        if (checkbox) checkbox.checked = true;
                        if (timeBadge) {{
                            timeBadge.style.display = 'inline-block';
                            timeBadge.textContent = 'Applied: ' + formatTime(record.applied_at);
                        }}
                    }} else {{
                        unappliedCount++;
                        card.classList.remove('is-applied');
                        if (checkbox) checkbox.checked = false;
                        if (timeBadge) {{
                            timeBadge.style.display = 'none';
                            timeBadge.textContent = '';
                        }}
                    }}
                }});

                // Update metric counters
                const total = cards.length;
                document.getElementById('stat-total').textContent = total;
                document.getElementById('stat-applied').textContent = appliedCount;
                document.getElementById('stat-unapplied').textContent = unappliedCount;

                document.getElementById('count-all').textContent = total;
                document.getElementById('count-applied').textContent = appliedCount;
                document.getElementById('count-unapplied').textContent = unappliedCount;

                filterCards();
            }}

            function filterCards() {{
                const searchTerm = document.getElementById('filter-search').value.toLowerCase().trim();
                const activeTab = document.querySelector('.tab-btn.active').getAttribute('data-tab');
                const minScore = parseInt(document.getElementById('filter-score').value, 10) || 0;
                const siteFilter = document.getElementById('filter-site').value.toLowerCase();

                const cards = document.querySelectorAll('.job-card');

                cards.forEach(card => {{
                    const text = card.textContent.toLowerCase();
                    const score = parseInt(card.getAttribute('data-score'), 10) || 0;
                    const site = card.getAttribute('data-site') || '';
                    const isApplied = card.classList.contains('is-applied');

                    // Filter match checks
                    const matchesSearch = !searchTerm || text.includes(searchTerm);
                    const matchesScore = score >= minScore;
                    const matchesSite = (siteFilter === 'all') || (site === siteFilter);

                    let matchesTab = true;
                    if (activeTab === 'applied') matchesTab = isApplied;
                    if (activeTab === 'unapplied') matchesTab = !isApplied;

                    if (matchesSearch && matchesScore && matchesSite && matchesTab) {{
                        card.style.display = '';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }}

            // Event Listeners
            document.addEventListener('DOMContentLoaded', () => {{
                refreshUI();

                // 1. Click on "Apply" link -> mark applied automatically
                document.getElementById('jobs-container').addEventListener('click', (e) => {{
                    const applyBtn = e.target.closest('a[data-action="apply"]');
                    if (applyBtn) {{
                        const card = applyBtn.closest('.job-card');
                        const url = card.getAttribute('data-url');
                        markJob(url, true);
                    }}
                }});

                // 2. Checkbox toggle
                document.getElementById('jobs-container').addEventListener('change', (e) => {{
                    if (e.target.classList.contains('applied-toggle')) {{
                        const card = e.target.closest('.job-card');
                        const url = card.getAttribute('data-url');
                        markJob(url, e.target.checked);
                    }}
                }});

                // 3. Search & filters
                document.getElementById('filter-search').addEventListener('input', filterCards);
                document.getElementById('filter-score').addEventListener('change', filterCards);
                document.getElementById('filter-site').addEventListener('change', filterCards);

                // 4. Tab group
                document.getElementById('filter-tabs').addEventListener('click', (e) => {{
                    const btn = e.target.closest('.tab-btn');
                    if (!btn) return;
                    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    filterCards();
                }});

                // 5. Export Applied CSV
                document.getElementById('btn-export').addEventListener('click', () => {{
                    const store = getStorage();
                    const cards = document.querySelectorAll('.job-card');
                    const rows = [["Title", "Company", "Match Score", "Job URL", "Applied At"]];

                    cards.forEach(card => {{
                        const url = card.getAttribute('data-url');
                        if (store[url] && store[url].applied) {{
                            const title = card.querySelector('.job-title')?.textContent.trim() || '';
                            const company = card.querySelector('.company-name')?.textContent.replace('🏢', '').trim() || '';
                            const score = card.getAttribute('data-score') || '';
                            const appliedAt = store[url].applied_at || '';
                            rows.push([`"${{title.replace(/"/g, '""')}}"`, `"${{company.replace(/"/g, '""')}}"`, score, `"${{url}}"`, `"${{appliedAt}}"`]);
                        }}
                    }});

                    if (rows.length === 1) {{
                        alert('No applied jobs tracked yet! Click "Apply" on any opening to start tracking.');
                        return;
                    }}

                    const csvContent = "data:text/csv;charset=utf-8," + rows.map(r => r.join(",")).join("\\n");
                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", `applied_jobs_${{new Date().toISOString().slice(0,10)}}.csv`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }});

                // 6. Reset Tracking
                document.getElementById('btn-reset').addEventListener('click', () => {{
                    if (confirm('Are you sure you want to reset all applied status tracking?')) {{
                        localStorage.removeItem(STORAGE_KEY);
                        refreshUI();
                    }}
                }});
            }});
        }})();
    </script>
</body>
</html>
"""
    return html_page


def generate_html_report(csv_or_df, output_html_path=None, date_str=None):
    """Generates an HTML report from a CSV file or pandas DataFrame.

    If output_html_path is None and csv_or_df is a filepath, changes .csv to .html.
    """
    if isinstance(csv_or_df, pd.DataFrame):
        df = csv_or_df
    else:
        csv_path = Path(csv_or_df)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        df = pd.read_csv(csv_path)
        if output_html_path is None:
            output_html_path = csv_path.with_suffix(".html")
        if date_str is None:
            # Try to infer date from filename
            base = csv_path.stem
            parts = base.split("_")
            for p in parts:
                if len(p) == 10 and p.count("-") == 2:
                    date_str = p
                    break

    if output_html_path is None:
        output_html_path = RANKED_HTML_PATH

    output_html_path = Path(output_html_path)

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    content = generate_html_content(df, title_date_str=date_str)

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Interactive HTML report generated: {output_html_path}", flush=True)
    return str(output_html_path)


if __name__ == "__main__":
    target_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(REPORTS_DIR / "ai_ranked_jobs.csv")
    if not target_csv.exists():
        print(f"Error: Target file {target_csv} does not exist.")
        sys.exit(1)
    out = generate_html_report(target_csv)
    print(f"Successfully generated HTML report at: {out}")
