# methodical_sample_summary.py

This repository contains `methodical_sample_summary.py`, a rate-limit-friendly Python script designed to sample and analyze discourse in veteran-focused subreddits. The script provides a structured, keyword-probe approach for collecting representative text data from Reddit, generating frequency counts of unigrams (single words) and bigrams (two-word phrases).

---

## Purpose

This script was developed as part of a larger dissertation project studying veteran discourse, particularly in communities like r/VeteransBenefits, r/Veterans, and r/VAClaims. The goal is to:

* Compare **researcher intuition** (keywords chosen deliberately for scraping) with **emergent patterns** (most frequent words and phrases actually appearing in discussions).
* Work within Reddit's API constraints while still producing **methodologically sound samples**.
* Avoid pitfalls discovered during earlier iterations (e.g., trying to pin posts to exact historical dates, which Reddit’s API does not reliably support).
* Provide outputs that help identify where researcher bias and community reality converge or diverge.

---

## Features

* **Probe-based sampling**: Uses broad, neutral keyword probes (e.g., "claim," "appeal," "rating") to ensure coverage across subreddits.
* **Time bounding**: Allows setting upper (required) and optional lower date bounds for analysis.
* **API-friendly design**: Built with conservative defaults to reduce the likelihood of hitting Reddit’s 429 "Too Many Requests" errors.
* **Token cleaning and filtering**: Removes stopwords and boilerplate to focus on meaningful terms.
* **Top-N frequency summaries**: Outputs CSV files of the top 20 unigrams and bigrams for each subreddit.
* **Optional keyword overlap report**: Can check alignment between your probe library and the actual top terms observed.

---

## Usage

1. **Set up Reddit credentials**

   * Create a Reddit app (type: script) at [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
   * Copy your client ID, client secret, username, password, and user agent into the script config.

2. **Adjust configuration**

   * Edit the `SUBREDDITS` list if you want different communities.
   * Modify `PROBE_QUERIES` if you want to probe with a different set of keywords.
   * Set `LATEST_ISO_UTC` (required) and optionally `EARLIEST_ISO_UTC`.

3. **Run the script**

   ```bash
   python methodical_sample_summary.py
   ```

4. **View outputs**

   * `top20_unigrams_by_sub.csv`
   * `top20_bigrams_by_sub.csv`
   * `overlap_report.csv` (if keyword library provided)

---

## Development Notes

This script evolved through extensive trial, error, and debugging:

* Early attempts to scrape Reddit by specific dates proved unfeasible due to API limitations.
* Pushshift, once commonly used for historical Reddit data, is unreliable for targeted day-level scrapes.
* The methodical probe approach balances feasibility and rigor, ensuring meaningful samples without overloading Reddit’s API.
* The script intentionally disables comment scraping by default to avoid 429 rate-limit errors, though the logic can be toggled back on if needed.

---

## Disclaimer

This script was developed with significant assistance from ChatGPT-5, guided by detailed prompts, debugging sessions, and design rationale provided by the repository owner. While ChatGPT-5 co-drafted portions of the code and documentation, all methodological decisions and research framing reflect the owner’s scholarly goals.

---

## License

This repository is released under the MIT License.
