# Saha: App Store Compliance Profile

What the app does, in compliance terms: the user types a sloka/mantra name; the Expo app sends it to the Saha FastAPI backend; the backend forwards the query to a web search provider (Brave or Google CSE), fetches third-party pages, extracts verse text with an LLM (LiteLLM → OpenAI/Anthropic/Google), and on request sends verse text to the LLM again to generate an English meaning. The app stores recent searches and saved slokas on-device only (AsyncStorage) and exports PDFs through the system share sheet. No accounts, no purchases, no ads, no analytics SDKs, no push, no location, no camera.

## Data that leaves the device

| Data | Sent to | Third party behind it | Guideline hooks |
|---|---|---|---|
| Search query (user-typed text) | `POST /search` | Brave Search or Google Programmable Search | 5.1.1(i), 5.1.2(i), App Privacy: Search History |
| Source URL chosen by the app | `POST /extract` | Third-party web pages (fetched server-side) | 5.2.2 |
| Verse text (from a third-party page) | `POST /extract`, `POST /translate` | LLM provider via LiteLLM | 5.1.2(i) third-party AI clause, 1.1 (AI output) |
| IP address, timing, status | Host logs, rate limiter | Render / Fly host | 5.1.1(i) retention statement |

Nothing identifies the user; there is no user id, email, or device identifier collected. Search queries are still "data provided by the user" and belong in App Privacy labels and the 5.1.2(i) disclosure.

## Applicability map

| Area | Status | Why |
|---|---|---|
| 5.1.2(i) third-party sharing incl. AI | **Applies, met in code** | Queries and verse/page text go to search and LLM providers. `ConsentSheet` + `src/store/consent.ts` gate `api.search` and `api.translate`. Permission is revocable on Search. |
| 5.1.1(i) privacy policy | Applies, met in code | `docs/privacy.md` served at `GET /privacy`; tappable from the Search footer and the consent sheet. Enter the real host in ASC. |
| 5.2.2 third-party content | Applies, mitigated | Scripture treated as public domain, `source_url` shown, no copying of site translations, `extract/fetch.py` honours robots and size caps, review notes drafted in `docs/app-store.md`. Keep documentation ready for an IP query. |
| 1.1.1 religious content | Applies | Present texts neutrally; extract/translate prompts forbid ranking or disparaging traditions; disclaimer on every meaning and in PDFs. |
| 2.1 completeness | Applies, guarded | Production EAS profile throws if `EXPO_PUBLIC_API_URL` is missing or loopback. Reviewer build must use EAS secrets pointing at the hosted API. |
| 4.2 minimum functionality | Applies, met | Transliteration, grouping, saved items, PDF export are native value beyond fetched text. |
| 4.3(b) saturated/low-effort | Applies | "Reference" category; listing must state the differentiators (multi-script transliteration, side-by-side, PDF). |
| Privacy manifest | Applies, declared | `ios.privacyManifests` in `app.config.ts` declares Search History and Other User Content (not linked, not tracking, App Functionality). Re-check merged `PrivacyInfo.xcprivacy` after prebuild. |
| Export compliance | Met | `ITSAppUsesNonExemptEncryption: false`; HTTPS only. Re-check if a crypto lib is added. |
| ATS | Met | Only default `http://127.0.0.1` for dev; production must be HTTPS. |
| App Privacy labels | Applies | Search History / User Content: App Functionality, not linked, not tracking. Consider "Other Usage Data" for server logs if the host retains IPs beyond transient security use. |
| Age rating | Applies | 4+ is defensible: no unrestricted web browsing (only extracted text is shown), no UGC, no chat. Re-answer the current questionnaire (4+, 9+, 13+, 16+, 18+). |
| 1.2 UGC | N/A | Nothing is published to other users; PDF sharing is via the OS share sheet. Becomes applicable if community notes/comments are added. |
| 4.8 Sign in with Apple, 5.1.1(v) account deletion | N/A | No accounts. Applicable the moment any login is added. |
| 3.1.1 IAP | N/A | Free, no digital goods. Applicable if premium features, tips, or donations are added (donations: 3.2.1(vi)). |
| ATT / tracking | N/A | No ads or analytics SDKs. Adding any tracker requires ATT + labels + SDK manifests. |
| 5.1.4 Kids | N/A | Not directed at children; privacy policy says so. |
| Push, location, camera, mic, contacts, Face ID | N/A | Packages not installed. |
| 2.5.2 OTA updates | N/A | `expo-updates` not installed; EAS channels exist but no runtime update client. |

## Where things live

| Artefact | Path |
|---|---|
| App config, Info.plist keys | `apps/mobile/app.config.ts` |
| Build/submit profiles | `apps/mobile/eas.json` |
| Client API calls (all off-device sends) | `apps/mobile/src/api/client.ts` (`api.search`, `api.extract`, `api.transliterate`, `api.translate`) |
| First send of user input | `apps/mobile/app/(tabs)/index.tsx` (search, gated by consent), `apps/mobile/app/sloka/[id].tsx` (meaning, gated by consent) |
| AI disclaimer | `apps/mobile/src/components/MeaningDisclaimer.tsx`, `DISCLAIMER` in `src/theme.ts`, PDF in `src/utils/pdf.ts` |
| Third-party / AI consent | `apps/mobile/src/components/ConsentSheet.tsx`, `apps/mobile/src/store/consent.ts` |
| Local persistence | `apps/mobile/src/store/{saved,history,session}.ts` |
| Privacy / terms text | `docs/privacy.md`, `docs/terms.md`, served by `services/api/app/main.py` |
| Store listing, labels, review notes | `docs/app-store.md` |
| Backend third-party calls | `services/api/app/search/{brave,google_cse}.py`, `extract/fetch.py`, `extract/llm_extract.py`, `translate.py` |
| Backend caching / logging | `services/api/app/cache.py`, host logs |

## Recommended 5.1.2(i) shape

Implemented: `ConsentSheet` + `src/store/consent.ts`. Gate `api.search` and `api.translate` on `accepted`. Continue / Not now. Revocable on Search. Do not regress this.

## Review history

- 17 Sep 2026 remediation: in-app `ConsentSheet` + `consent.ts` (AI-001); production URL/key required on EAS production profile (CFG-007); tappable `/privacy` and `/terms`; `ios.privacyManifests` declared (CFG-005). Remaining INFO: empty `ascAppId` until the ASC record exists; privacy URL in the listing is filled at submit time from the deployed host.
- Initial profile: scanner reports REQUIRED `AI-001` (no consent before third-party send) and `CFG-007` (localhost fallback with no production env), VERIFY `CFG-005` (no app-level privacy manifest block), INFO placeholders (`replace-after-eas-init`, `<your-api-host>`, empty `ascAppId`).
