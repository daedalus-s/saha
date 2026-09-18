from app.scripts.detect import detect_script


def test_detect_devanagari():
    assert detect_script("श्री गणेशाय नमः") == "devanagari"


def test_detect_tamil():
    assert detect_script("ஸ்ரீ ராம ஜெயம்") == "tamil"


def test_detect_telugu():
    assert detect_script("శ్రీ రామ జయం") == "telugu"


def test_detect_kannada():
    assert detect_script("ಶ್ರೀ ಗಣೇಶಾಯ ನಮಃ") == "kannada"


def test_detect_malayalam():
    assert detect_script("ശ്രീ ഗണേശായ നമഃ") == "malayalam"


def test_detect_gujarati():
    assert detect_script("શ્રી ગણેશાય નમઃ") == "gujarati"


def test_detect_bengali():
    assert detect_script("শ্রী গণেশায় নমঃ") == "bengali"


def test_detect_iast():
    assert detect_script("oṃ namo bhagavate vāsudevāya") == "iast"


def test_detect_latin_fallback():
    assert detect_script("Hanuman Chalisa") == "latin"


# Frozen list shared with apps/mobile/src/utils/scripts.ts (labels include latin).
FROZEN_SCRIPTS = (
    "devanagari",
    "tamil",
    "telugu",
    "kannada",
    "malayalam",
    "gujarati",
    "bengali",
    "iast",
    "itrans",
    "latin",
)


def test_supported_scripts_match_frozen_list():
    from app.models import SCRIPT_LABELS, SUPPORTED_SCRIPTS

    assert SUPPORTED_SCRIPTS == FROZEN_SCRIPTS
    assert set(SCRIPT_LABELS) == set(FROZEN_SCRIPTS)
