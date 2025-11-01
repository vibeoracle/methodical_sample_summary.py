# README — added_troubleshooting_methodical_sample_summary.py (fixed)

## Overview

`added_troubleshooting_methodical_sample_summary.py` is a **fully standalone**, rate-limit-friendly Reddit sampler designed to collect **unigram** and **bigram** frequency data from veteran-focused subreddits (e.g., r/VeteransBenefits, r/VAClaims, r/Veterans) within a specified time window.

It complements more targeted scrapers (like `va_claim_help_scraper2`) by surfacing **emergent language** — terms or phrases not pre-defined in a keyword library.

This “fixed” version eliminates `.env` dependency and uses **direct password-grant authentication** for stability. It also corrects indentation errors, adds better defaults, and allows you to run it without command-line parameters.

---

## Key Features

* **Probe-based sampling:** Uses broad, neutral probes (e.g., “claim,” “benefits,” “nexus”) rather than fixed keywords.
* **Time-bounded collection:** Define `--earliest` and `--latest` timestamps (ISO UTC).
* **Gentle rate limiting:** Built-in pauses and backoff handling for Reddit’s 429 errors.
* **Cross-subreddit comparison:** Outputs top 20 unigrams and bigrams for each subreddit.
* **Optional keyword overlap:** Compare emergent terms against your existing `keywords.txt` or `.csv`.
* **Standalone auth:** Bypasses `.env` and ensures the same credential flow works as your other scripts.

---

## Usage

Run from working directory:

```bash
python3 added_troubleshooting_methodical_sample_summary.py \
  --earliest "2025-10-22T00:00:00" \
  --latest "2025-11-01T23:59:59" \
  --verbose
```

Or run with defaults (the script will use the above window and three subs):

```bash
python3 added_troubleshooting_methodical_sample_summary.py
```

### Optional arguments

| Flag                 | Description                                                        |
| -------------------- | ------------------------------------------------------------------ |
| `--subs`             | List of subreddits (default: VeteransBenefits, Veterans, VAClaims) |
| `--probes`           | Override probe terms for custom sampling                           |
| `--keyword-library`  | Compare emergent terms to keyword list (.txt/.csv)            |
| `--include-comments` | Include comments (default off for speed and API safety)            |

---

## Outputs

All outputs save to the **current working directory**:

* `top20_unigrams_by_sub.csv`
* `top20_bigrams_by_sub.csv`
* `overlap_report.csv` *(optional)*

Each CSV includes:

* `subreddit`
* `word` or `phrase`
* `count`

---

## Differences from Previous Version (`methodical_sample_summary.py`)

| Area                     | Old Script                                       | Fixed Script                                    |
| ------------------------ | ------------------------------------------------ | ----------------------------------------------- |
| **Authentication**       | Relied on `.env` + environment variables         | Hard-coded password grant; no `.env` dependency |
| **Error handling**       | Occasional indentation errors, 401 auth failures | Cleaned up, robust exception handling           |
| **Time window defaults** | Required flags each run                          | Built-in defaults for bounded window            |
| **CLI structure**        | Complex preflight (`--doctor`)                   | Simplified—no `.env` or doctor needed           |
| **Readability**          | Dense indentation / flow                         | Flattened control structure, clearer output     |
| **Reliability**          | Intermittent 401s                                | Consistent login (password grant)               |

---

## Example Output Snippet

| subreddit        | word   | count |
| ---------------- | ------ | ----- |
| VeteransBenefits | claim  | 1184  |
| VeteransBenefits | service| 736   |
| VAClaims         | denied | 490   |
| Veterans         | rating | 443   |

---

## Notes

* Keep total runtime below 40 minutes to avoid rate-limit exhaustion.
* The script stops automatically when the time budget is reached.
* Comments are disabled by default (to avoid API overload).
* Ethics: Do not redistribute identifiable content.
