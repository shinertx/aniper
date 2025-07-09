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

import openai
from prometheus_client import Counter

TWITTER_BEARER: str | None = os.getenv("TWITTER_BEARER")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm_call_total = Counter("llm_call_total", "Total LLM calls", ["agent"])

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
    # Updated query for DeFi/meme coin and crypto trends
    query = (
        "pepe OR doge OR shiba OR floki OR wojak OR bonk OR elon OR turbo OR dogwifhat OR jeo OR popcat OR catcoin OR mog OR pnd OR baby OR grok OR tate OR base OR blast "
        "OR moon OR pump OR rug OR airdrop OR degen OR rekt OR gm OR wagmi OR lfg OR 100x OR ath OR scam OR presale OR launch OR trending OR viral "
        "OR solana OR eth OR ethereum OR layerzero OR arbitrum OR optimism OR polygon OR bsc lang:en -is:retweet"
    )
    since = (_dt.datetime.utcnow() - _dt.timedelta(minutes=minutes)).isoformat("T") + "Z"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER}"}
    params = {"query": query, "max_results": max_results, "start_time": since, "tweet.fields": "text"}

    attempts = 0
    while attempts < 3:
        try:
            r = httpx.get(endpoint, headers=headers, params=params, timeout=10)
            if r.status_code == 429:
                # Twitter returns epoch seconds in x-rate-limit-reset
                reset_epoch = int(r.headers.get("x-rate-limit-reset", "2"))
                wait = max(0, reset_epoch - int(time.time()))
                time.sleep(min(60, wait * (2 ** attempts)))
                attempts += 1
                continue
            r.raise_for_status()
            data = r.json()
            return [tweet["text"] for tweet in data.get("data", []) if "text" in tweet]
        except Exception:  # pragma: no cover – network or JSON failures
            return []
    return []


def _score_narratives_heuristic(texts: List[str]) -> Dict[str, float]:
    """Heuristic scoring: keyword frequency."""
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


def _score_narratives_llm(texts: List[str]) -> Dict[str, float]:
    """LLM scoring: call OpenAI GPT-4 for narrative scoring."""
    if not OPENAI_API_KEY:
        raise RuntimeError("USE_LLM=true but OPENAI_API_KEY is not set!")
    openai.api_key = OPENAI_API_KEY
    prompt = f"Score the following tweets for these categories: ['cat', 'dog', 'political', 'retro']. Tweets: {json.dumps(texts)}. Return a JSON object with category keys and float values between 0 and 1."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=256,
    )
    llm_call_total.labels(agent="narrative").inc()
    result = json.loads(response.choices[0].message.content)
    return {k: round(float(result.get(k, 0)), 3) for k in ["cat", "dog", "political", "retro"]}


def score_narratives(texts: List[str]) -> Dict[str, float]:
    """Compute per-narrative score between 0 and 1, using LLM if enabled."""
    if USE_LLM:
        try:
            return _score_narratives_llm(texts)
        except Exception as e:
            # Log error, fallback to heuristic
            print(f"[WARN] LLM scoring failed: {e}. Falling back to heuristic.")
    return _score_narratives_heuristic(texts)


# ---------------------------------------------------------------------------
# Artifact production API (called by manager) -------------------------------
# ---------------------------------------------------------------------------

def produce() -> Tuple[str, str]:
    """Return artifact filename and JSON content string. Writes to strict path."""
    tweets = _fetch_recent_tweets()
    scores = score_narratives(tweets)
    # Write artifact to strict path: repo_root/artifacts/narrative_scores.json
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    artifacts_dir = os.path.join(repo_root, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    path = os.path.join(artifacts_dir, "narrative_scores.json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(scores, separators=",:", sort_keys=True))
    return "narrative_scores.json", json.dumps(scores, separators=",:", sort_keys=True)


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