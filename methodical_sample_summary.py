#!/usr/bin/env python3
"""
methodical_sample_summary.py — probe‑based, rate‑limit‑friendly sampler
-----------------------------------------------------------------------
Purpose: build **unigram** and **bigram** frequency snapshots from veteran‑focused
subreddits within a bounded time window, using broad probe queries (not a
fixed keyword library). Complements targeted scrapers by surfacing emergent
language that a keyword list can miss.

# INSTALLATION
    python --version          # needs 3.10+
    pip install praw python-dotenv

# SETUP (.env)
    CLIENT_ID=...
    CLIENT_SECRET=...
    USER_AGENT=methodical-sample by u/<your_username> (contact: you@example.com)
    # Optional if using password grant (2FA must be off):
    REDDIT_USERNAME=...
    REDDIT_PASSWORD=...

# FIRST RUN
    python methodical_sample_summary.py --dotenv --doctor \
        --latest "2025-07-31T19:00:00" --subs VeteransBenefits Veterans VAClaims

# TYPICAL RUNS
    # 1) quick sample (no comments; safe defaults)
    python methodical_sample_summary.py --dotenv --latest "2025-07-31T19:00:00" --verbose

    # 2) bounded day window (UTC)
    python methodical_sample_summary.py --dotenv \
      --earliest "2025-07-30T00:00:00" --latest "2025-07-31T00:00:00" --verbose

# OUTPUTS
    top20_unigrams_by_sub.csv   # subreddit, word, count
    top20_bigrams_by_sub.csv    # subreddit, phrase, count
    overlap_report.csv          # optional overlap vs a keyword library

# NOTES
- Reddit caps search visibility (~1000 most recent results per query). This
  sampler mitigates by: (a) bounding by time, (b) stratifying probes, and
  (c) using gentle rate‑limits. It still cannot retrieve *everything*.
- Comments are OFF by default to avoid 429s; turn on only if necessary.

# TROUBLESHOOTING
- OAuthException → check CLIENT_ID/CLIENT_SECRET and app type (script).
- 429 TooManyRequests → the script backs off; consider lowering probes, raising sleeps.
- "Set LATEST_ISO_UTC" → provide --latest in ISO UTC (YYYY-MM-DDTHH:MM:SS).

# ETHICS
Use in accordance with Reddit Data API Terms. Avoid redistributing PII.
"""
from __future__ import annotations
import argparse
import csv
import os
import pathlib
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Iterable

# optional .env
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore

# third‑party
try:
    import praw  # type: ignore
    from prawcore.exceptions import TooManyRequests  # type: ignore
except Exception:
    praw = None  # type: ignore
    TooManyRequests = Exception  # type: ignore

# ------------------- tokenization & filters -------------------
STOPWORDS = {
    "a","an","and","are","as","at","be","been","but","by","can","do","for","from","had","has","have","he","her",
    "here","hers","him","his","how","i","if","in","into","is","it","its","just","me","mine","more","most","my",
    "no","not","now","of","on","one","or","our","ours","out","so","than","that","the","their","theirs","them",
    "there","these","they","this","those","to","too","up","very","was","we","were","what","when","where","which",
    "who","why","will","with","you","your","yours"
}
DOMAIN_STOP: set[str] = set()
WORD_RE = re.compile(r"[A-Za-z0-9']+")

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = re.sub(r"[-_/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokenize(s: str):
    return WORD_RE.findall(s.lower())

def valid_unigram(tok: str) -> bool:
    if tok in STOPWORDS or tok in DOMAIN_STOP:
        return False
    if len(tok) < 3:
        return False
    if tok.isdigit():
        return False
    return True

def valid_bigram(t1: str, t2: str) -> bool:
    if t1 in STOPWORDS or t2 in STOPWORDS:
        return False
    if t1 in DOMAIN_STOP or t2 in DOMAIN_STOP:
        return False
    if len(t1) < 2 or len(t2) < 2:
        return False
    return True

def bigrams(tokens: list[str]):
    for i in range(len(tokens) - 1):
        yield tokens[i], tokens[i + 1]

# ------------------- time helpers -------------------

def to_epoch_utc(iso_str: str | None):
    if not iso_str:
        return None
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

# ------------------- polite I/O helpers -------------------

def polite_sleep(n: float):
    try:
        time.sleep(n)
    except KeyboardInterrupt:
        raise

def backoff_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except TooManyRequests:
        print("[rate-limit] 429; sleeping 60s…")
        polite_sleep(62)
        return fn(*args, **kwargs)

# ------------------- doctor -------------------

def run_doctor(args) -> int:
    print("\n=== Preflight: methodical sampler ===")
    print(f"Python: {sys.version.split()[0]} — {'OK' if sys.version_info >= (3,10) else 'Needs 3.10+'}")

    if args.dotenv:
        if load_dotenv is None:
            print("python-dotenv not installed. Run: pip install python-dotenv")
        else:
            load_dotenv(); print("Loaded .env (if present).")

    if praw is None:
        print("praw not installed. Run: pip install praw")
        return 1

    cid = os.getenv("CLIENT_ID") or os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("CLIENT_SECRET") or os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("USER_AGENT") or os.getenv("REDDIT_USER_AGENT") or "methodical-sample by u/your_username"
    if not (cid and csec):
        print("Missing CLIENT_ID/CLIENT_SECRET in env or .env.")
        return 1

    try:
        reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=ua,
                             username=os.getenv("REDDIT_USERNAME"), password=os.getenv("REDDIT_PASSWORD"),
                             ratelimit_seconds=5)
        # light touch
        name = reddit.user.me()  # may be None for read-only
        print("Reddit API reachable.")
    except Exception as e:
        print(f"API error: {e}")
        return 1

    if not args.latest:
        print("Provide --latest in ISO UTC (e.g., 2025-07-31T19:00:00).")
        return 1

    print("All essential checks passed.")
    return 0

# ------------------- harvesting -------------------

def harvest(reddit, subreddits: list[str], probes: list[str], earliest_iso: str | None,
            latest_iso: str, time_budget_min: int, max_per_probe: int,
            include_comments: bool, max_comments: int, per_post_pause: float,
            sleep_every: int, sleep_seconds: float, verbose: bool):

    earliest_epoch = to_epoch_utc(earliest_iso)
    latest_epoch = to_epoch_utc(latest_iso)
    assert latest_epoch is not None, "latest epoch required"

    uni_per_sub: dict[str, Counter] = defaultdict(Counter)
    bi_per_sub: dict[str, Counter] = defaultdict(Counter)

    started = time.time()
    requests_made = 0

    for sub in subreddits:
        sr = reddit.subreddit(sub)
        if verbose:
            print(f"[{sub}] sampling with {len(probes)} probes…")
        for probe in probes:
            # paginate back via keyword search; sort=new so we can time‑bound
            results = backoff_call(sr.search, query=probe, sort="new", limit=None, params={"restrict_sr": 1})
            taken = 0
            for submission in results:
                if time.time() - started > time_budget_min * 60:
                    if verbose: print("⏱️ time budget reached; finishing…")
                    return uni_per_sub, bi_per_sub

                created = int(getattr(submission, "created_utc", 0)) or 0
                if created == 0:
                    continue
                if created > latest_epoch:
                    continue
                if (earliest_epoch is not None) and (created < earliest_epoch):
                    break  # older than window; next probe

                taken += 1
                if taken > max_per_probe:
                    break

                # titles + selftext (comments optional and off by default)
                chunks = [getattr(submission, "title", "") or "", getattr(submission, "selftext", "") or ""]
                blob = clean_text(" ".join(chunks))
                toks = tokenize(blob)
                uni_per_sub[sub].update([t for t in toks if valid_unigram(t)])
                for t1, t2 in bigrams(toks):
                    if valid_bigram(t1, t2):
                        bi_per_sub[sub].update([("%s %s" % (t1, t2),)])

                requests_made += 1
                if (sleep_every > 0) and (requests_made % sleep_every == 0):
                    polite_sleep(sleep_seconds)
                polite_sleep(per_post_pause)

                if include_comments and max_comments > 0:
                    try:
                        submission.comments.replace_more(limit=0)
                        for i, c in enumerate(submission.comments.list()):
                            if i >= max_comments:
                                break
                            body = clean_text(getattr(c, "body", "") or "")
                            toks_c = tokenize(body)
                            uni_per_sub[sub].update([t for t in toks_c if valid_unigram(t)])
                            for t1, t2 in bigrams(toks_c):
                                if valid_bigram(t1, t2):
                                    bi_per_sub[sub].update([("%s %s" % (t1, t2),)])
                    except Exception:
                        # comments are best‑effort
                        pass

        if verbose:
            print(f"[{sub}] done. unigrams={sum(uni_per_sub[sub].values())}, bigrams={sum(bi_per_sub[sub].values())}")

    return uni_per_sub, bi_per_sub

# ------------------- writers -------------------

def write_topn_csv(per_sub_counts: dict, out_path: str, header_word: str, subreddits: list[str], top_n: int):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subreddit", header_word, "count"])
        for sub in subreddits:
            for key, cnt in per_sub_counts[sub].most_common(top_n):
                w.writerow([sub, key, cnt])

def load_keyword_library(path: str | None) -> set[str]:
    if not path:
        return set()
    p = pathlib.Path(path)
    if not p.exists():
        return set()
    out: set[str] = set()
    if p.suffix.lower() == ".txt":
        for line in p.read_text(encoding="utf-8").splitlines():
            k = line.strip().lower()
            if k:
                out.add(k)
    elif p.suffix.lower() == ".csv":
        with p.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            cols = [c for c in (r.fieldnames or []) if "keyword" in c.lower()]
            col = cols[0] if cols else ((r.fieldnames or [None])[0])
            if col:
                for row in r:
                    k = (row.get(col) or "").strip().lower()
                    if k:
                        out.add(k)
    return out

def write_overlap_report(unis: dict, bis: dict, subreddits: list[str], library_path: str | None, top_n: int):
    lib = load_keyword_library(library_path)
    if not lib:
        return
    rows = []
    for sub in subreddits:
        top_uni = [w for w,_ in unis[sub].most_common(top_n)]
        top_bi  = [p for p,_ in bis[sub].most_common(top_n)]
        hits_uni = [w for w in top_uni if w in lib]
        hits_bi  = [p for p in top_bi if p in lib]
        rows.append([sub, len(hits_uni), len(hits_bi), "; ".join(hits_uni), "; ".join(hits_bi)])
    with open("overlap_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subreddit","hits_in_top_unigrams","hits_in_top_bigrams","which_unigrams","which_bigrams"])
        w.writerows(rows)
    print("Wrote overlap_report.csv (top vs your keyword library).")

# ------------------- main -------------------

def main():
    p = argparse.ArgumentParser(description="Methodical probe sampler for unigrams/bigrams (Reddit).")

    # env & doctor
    p.add_argument("--dotenv", action="store_true", help="Load .env from project root if present.")
    p.add_argument("--doctor", action="store_true", help="Run preflight checks and exit.")

    # time window
    p.add_argument("--earliest", default=None, help="Earliest ISO UTC (YYYY-MM-DDTHH:MM:SS). Optional.")
    p.add_argument("--latest", required=False, help="Latest ISO UTC (YYYY-MM-DDTHH:MM:SS). Required for runs.")

    # scope
    p.add_argument("--subs", nargs="*", default=["VeteransBenefits","Veterans","VAClaims"], help="Target subreddits.")
    p.add_argument("--probes", nargs="*", default=[
        "va","benefits","disability","claim","appeal","denied","rating","compensation",
        "form","cfr","service connected","evidence","nexus","pact act","dbq",
        "board appeal","supplemental","pending","effective date"
    ], help="Probe queries for stratified sampling.")

    # sampling & throttling
    p.add_argument("--time-budget", type=int, default=40, help="Wall clock minutes to run (default 40).")
    p.add_argument("--max-per-probe", type=int, default=80, help="Max posts per probe (default 80).")
    p.add_argument("--include-comments", action="store_true", help="Also sample comments (risk of 429).")
    p.add_argument("--max-comments-per-post", type=int, default=0, help="If sampling comments, cap per post.")
    p.add_argument("--per-post-pause", type=float, default=0.3, help="Pause seconds per post.")
    p.add_argument("--sleep-every", type=int, default=10, help="Sleep after N requests.")
    p.add_argument("--sleep-seconds", type=float, default=1.5, help="Seconds to sleep each cycle.")

    # outputs
    p.add_argument("--top-n", type=int, default=20, help="Top N words/phrases per subreddit (default 20).")
    p.add_argument("--keyword-library", default=None, help="Optional .txt/.csv to compute overlap (column contains 'keyword').")

    # verbosity
    p.add_argument("--verbose", action="store_true", help="Print progress messages.")

    args = p.parse_args()

    if args.dotenv and load_dotenv is not None:
        load_dotenv()

    if args.doctor:
        rc = run_doctor(args)
        sys.exit(rc)

    if praw is None:
        raise SystemExit("praw not installed. Run: pip install praw")

    cid = os.getenv("CLIENT_ID") or os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("CLIENT_SECRET") or os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("USER_AGENT") or os.getenv("REDDIT_USER_AGENT") or "methodical-sample by u/your_username"
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")
    if not (cid and csec):
        raise SystemExit("Missing CLIENT_ID/CLIENT_SECRET in env or .env. Use --dotenv.")

    reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=ua,
                         username=username, password=password, ratelimit_seconds=5)

    if not args.latest:
        raise SystemExit("Provide --latest in ISO UTC (e.g., 2025-07-31T19:00:00).")

    unis, bis = harvest(
        reddit=reddit,
        subreddits=args.subs,
        probes=args.probes,
        earliest_iso=args.earliest,
        latest_iso=args.latest,
        time_budget_min=args.time_budget,
        max_per_probe=args.max_per_probe,
        include_comments=args.include_comments,
        max_comments=args.max_comments_per_post,
        per_post_pause=args.per_post_pause,
        sleep_every=args.sleep_every,
        sleep_seconds=args.sleep_seconds,
        verbose=args.verbose,
    )

    write_topn_csv(unis, "top20_unigrams_by_sub.csv", "word", args.subs, args.top_n)
    write_topn_csv(bis,  "top20_bigrams_by_sub.csv",  "phrase", args.subs, args.top_n)
    print("Wrote: top20_unigrams_by_sub.csv, top20_bigrams_by_sub.csv")

    write_overlap_report(unis, bis, args.subs, args.keyword_library, args.top_n)

if __name__ == "__main__":
    main()
