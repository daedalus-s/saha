# Architecture

## Data flow

1. The app `POST /search { query, script }`. With `SEARCH_PROVIDER=gemini` (default), the API asks Gemini for the lyrics in the selected script and returns them as a `SlokaVersion` (plus a synthetic hit). Brave / Google CSE remain available behind `SEARCH_PROVIDER`.
2. If the response includes `versions`, the app shows them immediately. Otherwise it `POST /extract { url }` in parallel for each web hit (mock/Brave path).
3. The app groups versions by fingerprint (and near-duplicate similarity) and lets the user filter by script.
4. `POST /transliterate` maps verses through `indic-transliteration` (no LLM). Tamil uses superscript-numeral mode so Sanskrit consonants Tamil cannot write are preserved.
5. `POST /translate` asks the LLM for a verse-by-verse English meaning. We generate this ourselves rather than copying a site translation.
6. The app builds HTML and prints a PDF with `expo-print`, then shares it with `expo-sharing`.

Gemini lyrics are labelled AI-generated. Web extract remains incremental when a search provider returns URLs.

## Scripts

`devanagari`, `tamil`, `telugu`, `kannada`, `malayalam`, `gujarati`, `bengali`, `iast`, `itrans`, `latin`.

## Auth

Every mutating/data route requires header `X-App-Key`. `/health`, `/privacy`, `/terms`, and OpenAPI docs are open. Rate limits apply per IP.
