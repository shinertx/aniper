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

    assert set(scores.keys()) == {"cat", "dog", "political", "retro"}
    # 5 tweets total → simple frequency
    assert scores["cat"] == pytest.approx(2 / 5, abs=1e-3)
    assert scores["dog"] == pytest.approx(1 / 5, abs=1e-3)
    assert scores["political"] == pytest.approx(1 / 5, abs=1e-3)
    assert scores["retro"] == pytest.approx(1 / 5, abs=1e-3) 