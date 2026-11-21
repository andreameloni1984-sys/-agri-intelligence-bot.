from agribot.universe import find_commodities, find_sectors


def keys(text):
    return [c.key for c in find_commodities(text)]


def test_aliases():
    assert keys("oro long o short?") == ["oro"]
    assert keys("Che ne pensi di GOLD e silver") == ["oro", "argento"]
    assert keys("caffè e cacao") == ["caffe", "cacao"]
    assert keys("gas naturale") == ["gas"]


def test_brent_not_wti():
    assert keys("com'è messo il petrolio brent?") == ["brent"]
    assert keys("petrolio") == ["wti"]
    assert keys("wti vs brent") == ["wti", "brent"]


def test_no_false_positive():
    assert keys("ciao come stai") == []


def test_sectors():
    assert {c.key for c in find_sectors("e le agricole?")} == {"grano", "mais", "soia"}
