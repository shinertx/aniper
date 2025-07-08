import json
import os
import sys
import datetime as _dt
import time
from typing import List, Dict, Tuple

# Third-party HTTP client – lightweight and async-friendly
try:
    import httpx  # type: ignore
except ImportError:  # pragma: no cover – CI installs dependency
    httpx = None  # type: ignore

TWITTER_BEARER: str | None = os.getenv("TWITTER_BEARER")

# ---------------------------------------------------------------------------
# Helper functions -----------------------------------------------------------
# ---------------------------------------------------------------------------

def _fetch_recent_tweets(minutes: int = 10, max_results: int = 100) -> List[str]:
    """Pull recent Tweets that mention any narrative keyword.

    Down-grades gracefully (returns empty list) if `TWITTER_BEARER` unset or
    `httpx` missing.  This keeps unit tests hermetic and avoids hard network
    dependencies in CI.
    """
    if TWITTER_BEARER is None or httpx is None:
        return []

    endpoint = "https://api.twitter.com/2/tweets/search/recent"
    query = "cat OR dog OR political OR retro lang:en -is:retweet"
    since = (_dt.datetime.utcnow() - _dt.timedelta(minutes=minutes)).isoformat("T") + "Z"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER}"}
    params = {"query": query, "max_results": max_results, "start_time": since, "tweet.fields": "text"}

    attempts = 0
    while attempts < 3:
        try:
            r = httpx.get(endpoint, headers=headers, params=params, timeout=10)
            if r.status_code == 429:
                # Honor Twitter rate-limit header or backoff doubling
                retry_after = int(r.headers.get("x-rate-limit-reset", "2"))
                time.sleep(min(60, retry_after * (2 ** attempts)))
                attempts += 1
                continue
            r.raise_for_status()
            data = r.json()
            return [tweet["text"] for tweet in data.get("data", []) if "text" in tweet]
        except Exception:  # pragma: no cover – network or JSON failures
            return []
    return []


def score_narratives(texts: List[str]) -> Dict[str, float]:
    """Compute per-narrative score between 0 and 1.

    The score is the share of tweets mentioning the keyword over the total
    corpus.  Multiple keywords may match the same tweet (e.g. a tweet can
    talk about *cats* and be *retro* at the same time).
    """
    categories = {"cat": 0, "dog": 0, "political": 0, "retro": 0}
    if not texts:
        return {k: 0.0 for k in categories}

    for txt in texts:
        lower = txt.lower()
        for k in categories:
            if k in lower:
                categories[k] += 1

    total = len(texts)
    return {k: round(v / total, 3) for k, v in categories.items()}


# ---------------------------------------------------------------------------
# Artifact production API (called by manager) -------------------------------
# ---------------------------------------------------------------------------

def produce() -> Tuple[str, str]:
    """Return artifact filename and JSON content string."""
    tweets = _fetch_recent_tweets()
    scores = score_narratives(tweets)
    return "narrative_scores.json", json.dumps(scores, separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# CLI entry-point ------------------------------------------------------------
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover – exercised via produce() in tests
    name, content = produce()
    # Write artifact next to this file under `artifacts/` directory one level up
    artifacts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "artifacts"))
    os.makedirs(artifacts_dir, exist_ok=True)
    path = os.path.join(artifacts_dir, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    sys.stdout.write(content + "\n")


if __name__ == "__main__":
    main() 