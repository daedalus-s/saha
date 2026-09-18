# Architecture

## Data flow

1. The app `POST /search { query }`. The API expands the query with script suffixes, calls Brave or Google CSE, merges and de-duplicates URLs, and returns ranked hits.
2. The app `POST /extract { url }` in parallel for each hit. The API fetches the page (robots + size + timeout), extracts main content, asks the LLM (or heuristic fallback) for JSON verses, detects script, and returns a `SlokaVersion` with an SLP1 fingerprint.
3. The app groups versions by fingerprint (and near-duplicate similarity) and lets the user filter by script.
4. `POST /transliterate` maps verses through `indic-transliteration` (no LLM). Tamil uses superscript-numeral mode so Sanskrit consonants Tamil cannot write are preserved.
5. `POST /translate` asks the LLM for a verse-by-verse English meaning. We generate this ourselves rather than copying a site translation.
6. The app builds HTML and prints a PDF with `expo-print`, then shares it with `expo-sharing`.

The two-phase search keeps the API stateless and lets results appear incrementally.

## Scripts

`devanagari`, `tamil`, `telugu`, `kannada`, `malayalam`, `gujarati`, `bengali`, `iast`, `itrans`, `latin`.

## Auth

Every mutating/data route requires header `X-App-Key`. `/health`, `/privacy`, `/terms`, and OpenAPI docs are open. Rate limits apply per IP.
