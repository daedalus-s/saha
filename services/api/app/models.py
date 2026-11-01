from pydantic import BaseModel, Field, HttpUrl


# Keep in sync with apps/mobile/src/utils/scripts.ts (see tests/test_scripts.py).
SUPPORTED_SCRIPTS = (
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

SCRIPT_LABELS = {
    "devanagari": "Devanagari",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "kannada": "Kannada",
    "malayalam": "Malayalam",
    "gujarati": "Gujarati",
    "bengali": "Bengali",
    "iast": "Roman (IAST)",
    "itrans": "Roman (ITRANS)",
    "latin": "Roman",
}

# code, English label, script used to write the meaning.
# Keep in sync with apps/mobile/src/utils/languages.ts.
MEANING_LANGUAGES = (
    ("en", "English", "latin"),
    ("hi", "Hindi", "devanagari"),
    ("ta", "Tamil", "tamil"),
    ("te", "Telugu", "telugu"),
    ("kn", "Kannada", "kannada"),
    ("ml", "Malayalam", "malayalam"),
    ("gu", "Gujarati", "gujarati"),
    ("bn", "Bengali", "bengali"),
)


class SearchHit(BaseModel):
    url: str
    title: str
    snippet: str = ""
    source_domain: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    script: str = Field(default="devanagari", max_length=32)


class LyricsContinueRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    script: str = Field(default="devanagari", max_length=32)
    offset: int = Field(ge=0, le=4000)
    title: str | None = Field(default=None, max_length=200)
    previous_tail: list[str] = Field(default_factory=list, max_length=2)


class LyricsContinueResponse(BaseModel):
    verses: list[str] = []
    has_more: bool = False
    next_offset: int = 0
    title: str = ""


class ExtractRequest(BaseModel):
    url: HttpUrl
    query: str | None = Field(default=None, max_length=200)


class SlokaVersion(BaseModel):
    title: str
    script: str
    verses: list[str]
    source_url: str
    source_domain: str
    fingerprint: str
    normalized: str
    deity: str | None = None
    category: str | None = None
    also_on: list[str] = []
    ai_generated: bool = False
    has_more: bool = False
    next_offset: int = 0


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    expanded_queries: list[str] = []
    versions: list[SlokaVersion] = []
    suggestions: list[str] = []
    ambiguous: bool = False


class ExtractResponse(BaseModel):
    version: SlokaVersion | None = None
    error: str | None = None


class TransliterateRequest(BaseModel):
    verses: list[str] = Field(min_length=1)
    source_script: str
    target_script: str


class TransliterateResponse(BaseModel):
    verses: list[str]
    source_script: str
    target_script: str


class TranslateRequest(BaseModel):
    verses: list[str] = Field(min_length=1)
    source_script: str
    target_language: str = "en"
    title: str | None = None


class TranslatedVerse(BaseModel):
    verse: str
    meaning: str


class TranslateResponse(BaseModel):
    verses: list[TranslatedVerse]
    target_language: str
    disclaimer: str = "AI-generated meaning; verify with a scholar."
