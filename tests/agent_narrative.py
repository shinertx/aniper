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
    scores = score_narratives(tweets, "pumpfun")

    # Check that it returns a dictionary with scores
    assert isinstance(scores, dict)
    assert len(scores) > 0
    
    # Check that some common narrative keywords are present
    common_keywords = {"pump", "doge", "moon", "solana", "eth"}
    assert any(keyword in scores for keyword in common_keywords)
    
    # All scores should be float values
    for score in scores.values():
        assert isinstance(score, (int, float))