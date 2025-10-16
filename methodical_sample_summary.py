# methodical_sample_summary.py  —  no-comments, rate-limit friendly

import os, re, csv, time, pathlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

import praw
from prawcore.exceptions import TooManyRequests

# =============== CONFIG (edit these) ===============

REDDIT = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID", "YOUR_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET", "YOUR_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT", "methodical-sample v1.0 by u/YOUR_USERNAME"),
    username=os.getenv("REDDIT_USERNAME", "YOUR_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD", "YOUR_PASSWORD"),
)

SUBREDDITS = ["VeteransBenefits", "Veterans", "VAClaims"]

# Broad probes (stratified sampling; keep broad/neutral)
PROBE_QUERIES = [
    "va", "benefits", "disability", "claim", "appeal",
    "denied", "rating", "compensation", "form", "cfr",
    "service connected", "evidence", "nexus", "pact act",
    "dbq", "board appeal", "supplemental", "pending", "effective date"
]

# Time window (UTC). Upper bound required; earliest optional.
# July 31, 2025 3:00 PM Eastern = 19:00:00 UTC
EARLIEST_ISO_UTC = None
LATEST_ISO_UTC   = "2025-07-31T19:00:00"

# Runtime & sampling caps (gentle defaults to avoid 429s)
TIME_BUDGET_MIN         = 40
MAX_POSTS_PER_PROBE     = 80    # was 120
INCLUDE_COMMENTS        = False # **disabled** to avoid 429
MAX_COMMENTS_PER_POST   = 0     # ignored when INCLUDE_COMMENTS=False
PER_POST_PAUSE_SEC      = 0.3
SLEEP_EVERY_N_REQUESTS  = 10
SLEEP_SECONDS           = 1.5

TOP_N = 20
KEYWORD_LIBRARY_PATH = None  # e.g., "my_keywords.txt" (one term per line) to compute overlap
VERBOSE = True

# Stopwords & tokenization
STOPWORDS = {
    "a","an","and","are","as","at","be","been","but","by","can","do","for","from","had","has","have","he","her",
    "here","hers","him","his","how","i","if","in","into","is","it","its","just","me","mine","more","most","my",
    "no","not","now","of","on","one","or","our","ours","out","so","than","that","the","their","theirs","them",
    "there","these","they","this","those","to","too","up","very","was","we","were","what","when","where","which",
    "who","why","will","with","you","your","yours"
}
DOMAIN_STOP = set()
WORD_RE = re.compile(r"[A-Za-z0-9']+")

# =============== HELPERS ===============

def to_epoch_utc(iso_str):
    if not iso_str: return None
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

EARLIEST_EPOCH = to_epoch_utc(EARLIEST_ISO_UTC)
LATEST_EPOCH   = to_epoch_utc(LATEST_ISO_UTC)
assert LATEST_EPOCH is not None, "Set LATEST_ISO_UTC (UTC)."

def clean_text(s: str) -> str:
    if not s: return ""
    s = re.sub(r"http\S+|www\.\S+", " ", s)
    s = re.sub(r"[-_/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokenize(s: str): return WORD_RE.findall(s.lower())

def valid_unigram(tok: str) -> bool:
    if tok in STOPWORDS or tok in DOMAIN_STOP: return False
    if len(tok) < 3: return False
    if tok.isdigit(): return False
    return True

def valid_bigram(t1: str, t2: str) -> bool:
    if t1 in STOPWORDS or t2 in STOPWORDS: return False
    if t1 in DOMAIN_STOP or t2 in DOMAIN_STOP: return False
    if len(t1) < 2 or len(t2) < 2: return False
    return True

def bigrams(tokens):
    for i in range(len(tokens)-1):
        yield tokens[i], tokens[i+1]

def load_keyword_library(path):
    if not path: return set()
    p = pathlib.Path(path)
    if not p.exists(): return set()
    out = set()
    if p.suffix.lower() == ".txt":
        for line in p.read_text(encoding="utf-8").splitlines():
            k = line.strip().lower()
            if k: out.add(k)
    elif p.suffix.lower() == ".csv":
        with p.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            cols = [c for c in (r.fieldnames or []) if "keyword" in c.lower()]
            col = cols[0] if cols else (r.fieldnames[0] if r.fieldnames else None)
            if col:
                for row in r:
                    k = (row.get(col) or "").strip().lower()
                    if k: out.add(k)
    return out

def polite_sleep(n):
    try: time.sleep(n)
    except KeyboardInterrupt: raise

def backoff_call(fn, *args, **kwargs):
    """Call fn; on TooManyRequests, back off and retry once."""
    try:
        return fn(*args, **kwargs)
    except TooManyRequests:
        if VERBOSE: print("[rate-limit] 429; sleeping 60s…")
        polite_sleep(62)
        return fn(*args, **kwargs)

# =============== HARVEST ===============

def harvest():
    uni_per_sub = defaultdict(Counter)
    bi_per_sub  = defaultdict(Counter)

    started = time.time()
    requests_made = 0

    for sub in SUBREDDITS:
        sr = REDDIT.subreddit(sub)
        if VERBOSE:
            print(f"[{sub}] sampling with {len(PROBE_QUERIES)} probes…")

        for probe in PROBE_QUERIES:
            # paginate back via keyword search; sort=new so we can time-bound
            results = backoff_call(sr.search, query=probe, sort="new", limit=None, params={"restrict_sr": 1})
            taken = 0

            for submission in results:
                # wall-clock budget
                if time.time() - started > TIME_BUDGET_MIN * 60:
                    if VERBOSE: print("⏱️ time budget reached; finishing…")
                    return uni_per_sub, bi_per_sub

                created = int(getattr(submission, "created_utc", 0))
                if created == 0:  # safety
                    continue

                if created > LATEST_EPOCH:
                    continue
                if EARLIEST_EPOCH is not None and created < EARLIEST_EPOCH:
                    break

                taken += 1
                if taken > MAX_POSTS_PER_PROBE:
                    break

                # Titles + selftexts only (comments disabled to avoid 429)
                chunks = [submission.title or "", submission.selftext or ""]

                # Tokenize & update counts
                blob = clean_text(" ".join(chunks))
                toks = tokenize(blob)
                uni_per_sub[sub].update([t for t in toks if valid_unigram(t)])
                for t1, t2 in bigrams(toks):
                    if valid_bigram(t1, t2):
                        bi_per_sub[sub].update([(f"{t1} {t2}",)])

                requests_made += 1
                if requests_made % SLEEP_EVERY_N_REQUESTS == 0:
                    polite_sleep(SLEEP_SECONDS)

                polite_sleep(PER_POST_PAUSE_SEC)

        if VERBOSE:
            print(f"[{sub}] done. unigrams={sum(uni_per_sub[sub].values())}, bigrams={sum(bi_per_sub[sub].values())}")

    return uni_per_sub, bi_per_sub

# =============== WRITE OUT ===============

def write_topn_csv(per_sub_counts: dict, out_path: str, header_word: str):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subreddit", header_word, "count"])
        for sub in SUBREDDITS:
            for key, cnt in per_sub_counts[sub].most_common(TOP_N):
                w.writerow([sub, key, cnt])

def write_overlap_report(unis: dict, bis: dict, library_path: str | None):
    lib = load_keyword_library(library_path)
    if not lib:
        return
    rows = []
    for sub in SUBREDDITS:
        top_uni = [w for w,_ in unis[sub].most_common(TOP_N)]
        top_bi  = [p for p,_ in bis[sub].most_common(TOP_N)]
        hits_uni = [w for w in top_uni if w in lib]
        hits_bi  = [p for p in top_bi if p in lib]
        rows.append([sub, len(hits_uni), len(hits_bi),
                     "; ".join(hits_uni), "; ".join(hits_bi)])
    with open("overlap_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["subreddit","hits_in_top20_unigrams","hits_in_top20_bigrams","which_unigrams","which_bigrams"])
        w.writerows(rows)
    print("Wrote overlap_report.csv (top-20 vs your keyword library).")

# =============== MAIN ===============

if __name__ == "__main__":
    print("Starting methodical sample…")
    print(f"Upper bound (UTC): {LATEST_ISO_UTC}")
    print(f"Lower bound (UTC): {EARLIEST_ISO_UTC or '(none)'}")

    uni_per_sub, bi_per_sub = harvest()

    write_topn_csv(uni_per_sub, "top20_unigrams_by_sub.csv", "word")
    write_topn_csv(bi_per_sub,  "top20_bigrams_by_sub.csv",  "phrase")
    print("Wrote: top20_unigrams_by_sub.csv, top20_bigrams_by_sub.csv")

    write_overlap_report(uni_per_sub, bi_per_sub, KEYWORD_LIBRARY_PATH)
