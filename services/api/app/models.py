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


class SearchHit(BaseModel):
    url: str
    title: str
    snippet: str = ""
    source_domain: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    script: str = Field(default="devanagari", max_length=32)


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


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    expanded_queries: list[str] = []
    versions: list[SlokaVersion] = []


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
