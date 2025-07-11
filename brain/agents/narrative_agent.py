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
llm_call_total = Counter("llm_call_total", "Total LLM calls", ["agent", "platform"])

# --- Platform Specific Keywords ---
PUMPFUN_KEYWORDS = "pump.fun OR pumpfun"
LETSBONK_KEYWORDS = "letsbonk OR bonk"

# ---------------------------------------------------------------------------
# Helper functions -----------------------------------------------------------
# ---------------------------------------------------------------------------

def _fetch_recent_tweets(
    platform: str, minutes: int = 10, max_results: int = 100
) -> List[str]:
    """Pull recent Tweets that mention any narrative keyword for a specific platform.

    Down-grades gracefully (returns empty list) if `TWITTER_BEARER` unset or
    `httpx` missing.  This keeps unit tests hermetic and avoids hard network
    dependencies in CI.
    """
    if TWITTER_BEARER is None or httpx is None:
        return []

    endpoint = "https://api.twitter.com/2/tweets/search/recent"
    
    # Base query for general crypto trends
    base_query = (
        "pepe OR doge OR shiba OR floki OR wojak OR bonk OR elon OR turbo OR dogwifhat OR jeo OR popcat OR catcoin OR mog OR pnd OR baby OR grok OR tate OR base OR blast "
        "OR moon OR pump OR rug OR airdrop OR degen OR rekt OR gm OR wagmi OR lfg OR 100x OR ath OR scam OR presale OR launch OR trending OR viral "
        "OR solana OR eth OR ethereum OR layerzero OR arbitrum OR optimism OR polygon OR bsc lang:en -is:retweet"
    )

    # Add platform-specific keywords
    if platform == "pumpfun":
        platform_keywords = PUMPFUN_KEYWORDS
    elif platform == "letsbonk":
        platform_keywords = LETSBONK_KEYWORDS
    else:
        platform_keywords = ""

    # Construct the final query
    # Example for pumpfun: "((...base_query...) AND (pump.fun OR pumpfun)) OR (\"pump.fun viral memecoin July 2025\")"
    platform_search_phrase = f'"{platform} viral memecoin July 2025"'
    if platform_keywords:
        query = f"(({base_query}) AND ({platform_keywords})) OR ({platform_search_phrase})"
    else:
        query = base_query


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
        except Exception as e:  # pragma: no cover – network or JSON failures
            print(f"Error fetching tweets for {platform}: {e}")
            return []
    return []


def _score_narratives_heuristic(texts: List[str]) -> Dict[str, float]:
    """Heuristic scoring: keyword frequency for DeFi/meme/crypto trends."""
    categories = {
        "pepe": 0, "doge": 0, "shiba": 0, "floki": 0, "wojak": 0, "bonk": 0, "elon": 0, "turbo": 0, "dogwifhat": 0, "jeo": 0, "popcat": 0, "catcoin": 0, "mog": 0, "pnd": 0, "baby": 0, "grok": 0, "tate": 0, "base": 0, "blast": 0,
        "moon": 0, "pump": 0, "rug": 0, "airdrop": 0, "degen": 0, "rekt": 0, "gm": 0, "wagmi": 0, "lfg": 0, "100x": 0, "ath": 0, "scam": 0, "presale": 0, "launch": 0, "trending": 0, "viral": 0,
        "solana": 0, "eth": 0, "ethereum": 0, "layerzero": 0, "arbitrum": 0, "optimism": 0, "polygon": 0, "bsc": 0,
        "pump.fun": 0, "letsbonk": 0, # Added platform keywords
    }
    if not texts:
        return {k: 0.0 for k in categories}
    for txt in texts:
        lower = txt.lower()
        for k in categories:
            if k in lower:
                categories[k] += 1
    total = len(texts)
    return {k: round(v / total, 3) for k, v in categories.items()}


def _score_narratives_llm(texts: List[str], platform: str) -> Dict[str, float]:
    """LLM scoring: call OpenAI GPT-4 for narrative scoring."""
    if not OPENAI_API_KEY:
        raise RuntimeError("USE_LLM=true but OPENAI_API_KEY is not set!")
    openai.api_key = OPENAI_API_KEY
    categories = [
        "pepe", "doge", "shiba", "floki", "wojak", "bonk", "elon", "turbo", "dogwifhat", "jeo", "popcat", "catcoin", "mog", "pnd", "baby", "grok", "tate", "base", "blast",
        "moon", "pump", "rug", "airdrop", "degen", "rekt", "gm", "wagmi", "lfg", "100x", "ath", "scam", "presale", "launch", "trending", "viral",
        "solana", "eth", "ethereum", "layerzero", "arbitrum", "optimism", "polygon", "bsc",
        "pump.fun", "letsbonk",
    ]
    prompt = f"You are analyzing social media sentiment for crypto trading on the '{platform}' platform. Score the following tweets for these categories: {categories}. Tweets: {json.dumps(texts)}. Return a JSON object with category keys and float values between 0 and 1, reflecting the relevance and intensity for the '{platform}' context. Focus on signals relevant to '{platform} viral memecoin July 2025'."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    llm_call_total.labels(agent="narrative", platform=platform).inc()
    result = json.loads(response.choices[0].message.content)
    return {k: round(float(result.get(k, 0)), 3) for k in categories}


def score_narratives(texts: List[str], platform: str) -> Dict[str, float]:
    """Compute per-narrative score between 0 and 1, using LLM if enabled."""
    if USE_LLM:
        try:
            return _score_narratives_llm(texts, platform)
        except Exception as e:
            # Log error, fallback to heuristic
            print(f"[WARN] LLM scoring for {platform} failed: {e}. Falling back to heuristic.")
    return _score_narratives_heuristic(texts)


# ---------------------------------------------------------------------------
# Artifact production API (called by manager) -------------------------------
# ---------------------------------------------------------------------------

def produce() -> List[Tuple[str, str]]:
    """Return a list of (filename, JSON content string) tuples for each platform."""
    platforms_str = os.getenv("PLATFORMS", "pumpfun,letsbonk")
    platforms = [p.strip() for p in platforms_str.split(',') if p.strip()]
    artifacts = []
    
    for platform in platforms:
        print(f"Producing narrative scores for platform: {platform}")
        tweets = _fetch_recent_tweets(platform=platform)
        if not tweets:
            print(f"No tweets found for {platform}, skipping artifact generation.")
            continue
            
        scores = score_narratives(tweets, platform=platform)
        
        # Write artifact to strict path: repo_root/artifacts/narrative_scores_{platform}.json
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        artifacts_dir = os.path.join(repo_root, "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        
        filename = f"narrative_scores_{platform}.json"
        path = os.path.join(artifacts_dir, filename)
        content = json.dumps(scores, separators=",:", sort_keys=True)
        
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
            
        artifacts.append((filename, content))
        
    return artifacts


# ---------------------------------------------------------------------------
# CLI entry-point ------------------------------------------------------------
# ---------------------------------------------------------------------------

def main() -> None:  # pragma: no cover – exercised via produce() in tests
    artifacts = produce()
    # For CLI, just print the content of the first artifact
    if artifacts:
        sys.stdout.write(artifacts[0][1] + "\n")


if __name__ == "__main__":
    main()