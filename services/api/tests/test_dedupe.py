from app.extract.dedupe import are_duplicates
from app.transliterate import fingerprint


def test_are_duplicates_same_text():
    a = ["ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं"]
    b = ["ॐ भूर्भुवः स्वः तत्सवितुर्वरेण्यं"]
    assert are_duplicates(a, b, "devanagari", "devanagari")


def test_are_duplicates_whitespace_and_punctuation():
    a = ["राम राम राम राम"]
    b = ["राम, राम राम राम!"]
    assert are_duplicates(a, b, "devanagari", "devanagari")


def test_not_duplicates_different_slokas():
    a = ["ॐ भूर्भुवः स्वः"]
    b = ["श्री महागणपतये नमः श्री सिद्धिविनायकाय नमः"]
    assert not are_duplicates(a, b, "devanagari", "devanagari")


def test_matching_fingerprints_for_same_verses():
    a, _ = fingerprint(["ॐ भूर्भुवः स्वः"], "devanagari")
    b, _ = fingerprint(["ॐ भूर्भुवः स्वः"], "devanagari")
    c, _ = fingerprint(["श्री गणेशाय नमः श्री गणेशाय नमः"], "devanagari")
    assert a == b
    assert a != c
