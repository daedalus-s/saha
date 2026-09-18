"""Fixture pages so SEARCH_PROVIDER=mock works end-to-end without crawling."""

from __future__ import annotations

from urllib.parse import urlparse

from app.models import ExtractResponse, SlokaVersion
from app.transliterate import fingerprint

PAGES: dict[str, dict] = {
    "hanuman-chalisa-devanagari": {
        "title": "Hanuman Chalisa",
        "script": "devanagari",
        "deity": "Hanuman",
        "category": "chalisa",
        "verses": [
            "श्रीगुरु चरन सरोज रज निज मनु मुकुर सुधारि",
            "बरनउँ रघुबर बिमल जसु जो दायकु फल चारि",
            "बुद्धिहीन तनु जानिके सुमिरौं पवनकुमार",
            "बल बुद्धि बिद्या देहु मोहिं हरहु कलेस बिकार",
        ],
    },
    "hanuman-chalisa-telugu": {
        "title": "Hanuman Chalisa",
        "script": "telugu",
        "deity": "Hanuman",
        "category": "chalisa",
        "verses": [
            "శ్రీగురు చరన సరోజ రజ నిజ మను ముకుర సుధారి",
            "బరనఉఁ రఘుబర బిమల జసు జో దాయకు ఫల చారి",
            "బుద్ధిహీన తను జానికే సుమిరౌం పవనకుమార",
            "బల బుద్ధి బిద్యా దేహు మోహిఁ హరహు కలేస బికార",
        ],
    },
    "hanuman-chalisa-tamil": {
        "title": "Hanuman Chalisa",
        "script": "tamil",
        "deity": "Hanuman",
        "category": "chalisa",
        "verses": [
            "ஶ்ரீகு³ரு சரந ஸரோஜ ரஜ நிஜ மநு முகுர ஸுதா⁴ரி",
            "ப³ரநஉம் ரகு⁴ப³ர பி³மல ஜஸு ஜோ தா³யகு ப²ல சாரி",
            "பு³த்³தி⁴ஹீந தநு ஜாநிகே ஸுமிரௌம் பவநகுமார",
            "ப³ல பு³த்³தி⁴ பி³த்³யா தே³ஹு மோஹிம் ஹரஹு கலேஸ பி³கார",
        ],
    },
}


def mock_extract(url: str) -> ExtractResponse | None:
    path = urlparse(url).path.rstrip("/").split("/")[-1]
    data = PAGES.get(path)
    if data is None:
        return None
    verses = list(data["verses"])
    digest, normalized = fingerprint(verses, data["script"])
    domain = (urlparse(url).hostname or "example.org").removeprefix("www.")
    version = SlokaVersion(
        title=data["title"],
        script=data["script"],
        verses=verses,
        source_url=url,
        source_domain=domain,
        fingerprint=digest,
        normalized=normalized,
        deity=data.get("deity"),
        category=data.get("category"),
    )
    return ExtractResponse(version=version, error=None)
