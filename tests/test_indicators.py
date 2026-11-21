from agribot import indicators as ind


def test_sma_and_returns():
    vals = [1, 2, 3, 4, 5]
    assert ind.sma(vals, 5) == 3
    assert ind.sma(vals, 6) is None
    assert ind.pct_return(vals, 4) == 4.0


def test_rsi_extremes():
    assert ind.rsi(list(range(1, 40))) == 100.0
    assert ind.rsi(list(range(40, 1, -1))) < 1


def test_atr_constant_range():
    high = [11.0] * 30
    low = [9.0] * 30
    close = [10.0] * 30
    assert abs(ind.atr(high, low, close) - 2.0) < 1e-9


def test_macd_sign_follows_trend():
    up = [100 * 1.01 ** i for i in range(100)]
    line, _sig, _hist = ind.macd(up)
    assert line > 0


def test_donchian_excludes_last_bar():
    high = [1, 2, 3, 10]
    low = [0, 1, 2, 9]
    assert ind.donchian(high, low, 3) == (3, 0)
