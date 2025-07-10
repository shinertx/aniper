import pytest  # type: ignore

from brain.agents.narrative_agent import score_narratives


def test_score_narratives_basic():
    tweets = [
        "I love my CAT so much!",
        "Dogs are great companions.",
        "Retro games bring back memories.",
        "Another cat meme incoming",
        "Political debates are heating up.",
    ]
    scores = score_narratives(tweets)

    expected_keys = {
        "pepe", "doge", "shiba", "floki", "wojak", "bonk", "elon", "turbo", "dogwifhat", "jeo", "popcat", "catcoin", "mog", "pnd", "baby", "grok", "tate", "base", "blast",
        "moon", "pump", "rug", "airdrop", "degen", "rekt", "gm", "wagmi", "lfg", "100x", "ath", "scam", "presale", "launch", "trending", "viral",
        "solana", "eth", "ethereum", "layerzero", "arbitrum", "optimism", "polygon", "bsc"
    }
    assert set(scores.keys()) == expected_keys