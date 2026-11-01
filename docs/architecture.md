# Architecture

## Data flow

1. The app `POST /search { query, script }`. With `SEARCH_PROVIDER=gemini` (default), the API asks Gemini 3.8 Flash for the lyrics in the selected script and returns them as a `SlokaVersion` (plus a synthetic hit). A name typed in Tamil is detected and sent as Tamil so the model can resolve the work; other Indic scripts also get an IAST hint. Lyrics still come back in the selected script. If the name is unknown or matches several works, the response includes `suggestions` (and `ambiguous` when more than one work fits) instead of lyrics. A work longer than one reply is returned 80 verses at a time (`has_more`, `next_offset`); the app requests `POST /lyrics/continue` until the text is complete or 4,000 verses are loaded, and the screen virtualizes the lines. Brave / Google CSE remain available behind `SEARCH_PROVIDER`; an empty web result uses the same suggestion list when an LLM is configured.
2. If the response includes `versions`, the app shows them immediately. Otherwise it `POST /extract { url }` in parallel for each web hit (mock/Brave path).
3. The app groups versions by fingerprint (and near-duplicate similarity) and lets the user filter by script.
4. `POST /transliterate` maps verses through `indic-transliteration` (no LLM). Tamil uses superscript-numeral mode so Sanskrit consonants Tamil cannot write are preserved.
5. `POST /translate` asks the LLM for a verse-by-verse meaning in a supported language (`en`, `hi`, `ta`, `te`, `kn`, `ml`, `gu`, `bn`). We generate this ourselves rather than copying a site translation.
6. The app builds HTML and prints a PDF with `expo-print`, then shares it with `expo-sharing`.

Gemini lyrics are labelled AI-generated. Web extract remains incremental when a search provider returns URLs.

## Scripts

`devanagari`, `tamil`, `telugu`, `kannada`, `malayalam`, `gujarati`, `bengali`, `iast`, `itrans`, `latin`.

## Auth

Every mutating/data route requires header `X-App-Key`. `/health`, `/privacy`, `/terms`, and OpenAPI docs are open. Rate limits apply per IP.
