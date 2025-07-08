from brain.agents.performance_coach import _parse_metrics, _suggest_ticket_size


def test_ticket_size_adjustment():
    metrics = """
    # HELP trade_hit_total Successful trades
    trade_hit_total 92
    trades_submitted_total 100
    """
    hit, total = _parse_metrics(metrics)
    assert hit == 92 and total == 100

    new_size = _suggest_ticket_size(10, hit, total)
    assert new_size == 11  # +10 % as ratio > 0.9

    # ratio below 0.5 reduces size
    new_size2 = _suggest_ticket_size(10, 40, 100)
    assert new_size2 == 9 