"""Pull main textual content out of an HTML page."""

from __future__ import annotations

import re

import trafilatura


def clean_html(html: str, url: str | None = None) -> str:
    extracted = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        include_links=False,
        favor_recall=True,
    )
    if extracted and extracted.strip():
        return _normalize_whitespace(extracted)

    # Fallback: strip tags roughly if trafilatura finds nothing
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return _normalize_whitespace(text)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
