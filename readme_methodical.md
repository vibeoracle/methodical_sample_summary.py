# Methodical Sample Summary — Probe-Based Reddit Sampler

`methodical_sample_summary.py` is a rate-limit-friendly Python script designed to collect and analyze discourse from veteran-focused subreddits, including **r/Veterans**, **r/VeteransBenefits**, and **r/VAClaims**. The scraper performs structured sampling using broad **probe keywords** to generate representative frequency counts of unigrams (single words) and bigrams (two-word phrases). It complements targeted, keyword-based scrapers by surfacing *emergent language* and *organic discourse patterns* that may fall outside predefined research assumptions.

---

## Purpose

This script was developed as part of a larger dissertation project on digital veteran discourse. It functions as a **complementary tool** to targeted rhetorical-strategy scrapers, aiming to compare:

* **Researcher intuition** (keyword-based searches) vs. **community emergence** (naturally recurring discourse).
* How **institutionally significant** topics (e.g., “service connected,” “effective date,” etc.) relate to **emergent issues** (e.g., sleep apnea, PACT Act) within online veteran spaces.
* Where researcher bias and community priorities intersect, diverge, or evolve over time.

The methodical sampler works within Reddit’s inherent API constraints (≈1,000 visible results per query) to produce **bounded, ethically gathered data** without overburdening the platform.

---

## Features

* **Probe-Based Sampling** – Uses broad, neutral keyword probes (e.g., “claim,” “appeal,” “rating”) to gather representative text samples across subreddits.
* **Time Bounding** – Accepts upper (`--latest`) and optional lower (`--earliest`) ISO UTC date bounds for reproducible temporal windows.
* **API-Aware Design** – Includes built-in backoff and polite sleep intervals to minimize 429 (“Too Many Requests”) errors.
* **Token Cleaning & Filtering** – Strips boilerplate, links, and stopwords to focus on meaningful terms.
* **Frequency Summaries** – Exports CSV files of the top 20 unigrams and bigrams per subreddit.
* **Optional Overlap Report** – Compares top terms against a user-provided keyword library to assess convergence between designed and organic language.

---

## ⚙️ Setup & Installation

### Requirements

Python 3.10 or newer
Install dependencies:

```bash
pip install praw python-dotenv
```

### Reddit Credentials

1. Create a Reddit *script app* at [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
2. Add your credentials to a `.env` file in the project folder:

```bash
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
USER_AGENT=methodical-sample by u/<your_username> (contact: you@example.com)
# Optional if using password grant (2FA must be off):
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

---

## 🚀 Usage

Run the built-in **doctor** first to verify setup:

```bash
python methodical_sample_summary.py --dotenv --doctor --latest "2025-07-31T19:00:00"
```

If all checks pass, start a quick probe-based scrape:

```bash
python methodical_sample_summary.py --dotenv --latest "2025-07-31T19:00:00" --verbose
```

Optionally define a time window:

```bash
python methodical_sample_summary.py --dotenv \
  --earliest "2025-07-30T00:00:00" --latest "2025-07-31T00:00:00" --verbose
```

Outputs:

* `top20_unigrams_by_sub.csv`
* `top20_bigrams_by_sub.csv`
* `overlap_report.csv` (if keyword library provided)

---

## Parameters

| Flag                 | Description                                                                    |
| -------------------- | ------------------------------------------------------------------------------ |
| `--subs`             | List of target subreddits (default: VeteransBenefits Veterans VAClaims)        |
| `--probes`           | Probe keywords for sampling (default set includes claim, appeal, rating, etc.) |
| `--latest`           | **Required** upper time bound in ISO UTC (e.g., 2025-07-31T19:00:00)           |
| `--earliest`         | Optional lower bound for time window                                           |
| `--time-budget`      | Wall-clock minutes to run (default 40)                                         |
| `--max-per-probe`    | Maximum posts per probe query (default 80)                                     |
| `--include-comments` | Enable comment sampling (off by default)                                       |
| `--keyword-library`  | Path to .txt or .csv keyword list for overlap comparison                       |
| `--verbose`          | Print progress logs                                                            |

---

## Methodological Context

The methodical sampler arose from a design tension: keyword-based scrapers are strong for tracking institutional discourse but risk missing **emergent topics**. This script intentionally reverses that focus—scraping broadly to observe what naturally circulates.

By contrasting the *targeted rhetorical strategy scrapes* with this *organic frequency sample*, the researcher can identify:

* Hidden alignments between intuition and emergence.
* Patterns that escape keyword thresholds but shape community discourse.
* Methodological limits that reveal how infrastructures (like Reddit’s API) structure what can be known.

This design treats uncertainty as a form of rigor, acknowledging infrastructural constraints as part of the analytic ecology.

---

## Development Notes

* Early versions attempted post-by-date collection, but Reddit’s API restricts access to ~1,000 most recent results per query.
* Pushshift, once popular for historical Reddit data, proved unreliable for date-bounded retrievals.
* The final sampler embraces bounded sampling and linguistic aggregation as a reproducible compromise between completeness and feasibility.
* Comments are disabled by default to reduce 429 errors; enable only for small-scale runs.

---

## Ethics & License

This project complies with [Reddit’s Data API Terms of Use](https://www.redditinc.com/policies/data-api-terms).
No personally identifying information (usernames, URLs, or IDs) should be redistributed or published in research outputs.

Released under the **MIT License**.

---

## Acknowledgment

Developed collaboratively with **ChatGPT-5** through iterative debugging and design dialogues.
Methodological framing, interpretation, and research applications were directed by the repository’s author as part of a dissertation on digital veteran discourse.

---
