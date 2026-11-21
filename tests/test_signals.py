from agribot.signals import analyze
from agribot.universe import get

from .helpers import make_history, trend


def test_uptrend_is_long_with_levels():
    s = analyze(get("oro"), make_history(trend(step=0.002, wiggle=0.01)))
    assert s.direction == "LONG"
    assert s.score >= 25
    assert s.stop < s.price < s.target1 < s.target2


def test_downtrend_is_short():
    s = analyze(get("grano"), make_history(trend(step=-0.002, wiggle=0.01)))
    assert s.direction == "SHORT"
    assert s.stop > s.price > s.target1


def test_flat_market_is_neutral():
    closes = [100 + (1 if i % 2 else -1) for i in range(399)] + [100.0]
    s = analyze(get("mais"), make_history(closes))
    assert s.direction == "NEUTRO"
    assert s.stop is None
