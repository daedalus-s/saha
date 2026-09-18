from app.transliterate import fingerprint, transliterate_text, transliterate_verses


GAYATRI = "ॐ भूर्भुवः स्वः"


def test_devanagari_to_iast_round_contains_om():
    iast = transliterate_text(GAYATRI, "devanagari", "iast")
    assert "bh" in iast.lower() or "bhu" in iast.lower()
    back = transliterate_text(iast, "iast", "devanagari")
    assert "भू" in back or "भु" in back


def test_devanagari_to_telugu():
    telugu = transliterate_text("राम", "devanagari", "telugu")
    assert telugu
    assert telugu != "राम"


def test_devanagari_to_tamil():
    tamil = transliterate_text("राम", "devanagari", "tamil")
    assert tamil
    # Tamil code block
    assert any("\u0b80" <= ch <= "\u0bff" for ch in tamil)


def test_transliterate_verses_preserves_count():
    verses = ["राम राम", "सीता राम"]
    out = transliterate_verses(verses, "devanagari", "iast")
    assert len(out) == 2


def test_fingerprint_stable():
    a, _ = fingerprint(["राम राम"], "devanagari")
    b, _ = fingerprint(["राम  राम"], "devanagari")
    assert a == b


def test_tamil_target_uses_superscripted_scheme():
    from app.transliterate import _tamil_target_scheme

    assert "superscript" in _tamil_target_scheme()

