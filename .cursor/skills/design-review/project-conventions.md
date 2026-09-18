# Saha: Architecture and Convention Baseline

The reference the review compares targeted code against. Code is the source of truth; when this file and the code disagree, review against the code and raise the drift as a finding.

## Monorepo layout

| Path | Role | Must not |
|---|---|---|
| `services/api` | FastAPI backend: search, extract, transliterate, translate | Know about UI |
| `apps/mobile` | Expo / React Native app (iOS first, Android buildable) | Hold LLM/search keys or call third-party APIs directly |
| `docs` | Privacy, terms, architecture, runbooks; `/privacy` and `/terms` are served from here by the API | Contain code |
| `scripts` | Repo-level tooling (icon generation) | Be imported by app or API |

Data flow (`docs/architecture.md`): `POST /search` → `POST /extract` per hit (parallel, incremental) → client groups by fingerprint → `POST /transliterate` (no LLM) → `POST /translate` (LLM) → PDF via `expo-print` / `expo-sharing`. The API is stateless apart from the on-disk cache.

## Backend (`services/api/app`)

### Layering

```
main.py            routes, middleware, rate limits, HTTP error mapping   (entry layer)
  └─ search/ extract/ transliterate.py translate.py                     (domain layer)
       └─ models.py  config.py  cache.py  scripts/detect.py             (shared layer)
```

- Routes in `main.py` are thin: validate, call one domain function, map exceptions to `HTTPException`. Business logic lives in the domain module.
- Domain packages expose their public surface from `__init__.py` (`search_sloka`, `extract_from_url`). Submodules are internal.
- All request/response models and domain models are Pydantic classes in `models.py`. Shared enumerations (`SUPPORTED_SCRIPTS`, `SCRIPT_LABELS`) live there too.
- Settings come from `config.get_settings()` (cached); modules accept an optional `Settings` for testability rather than reading env directly.
- Pluggable integrations use a `typing.Protocol` plus a `build_provider(settings)` factory (see `search/base.py`, `search/__init__.py`). A `Mock*` implementation exists for every provider and is selected by config in tests.

### Conventions

- Files, functions, variables: `snake_case`. Classes and Pydantic models: `PascalCase`. Module constants: `UPPER_SNAKE`. Private helpers are underscore-prefixed.
- Every module starts with `from __future__ import annotations`; imports are absolute (`from app.models import ...`).
- Type hints on all public functions; `X | None` rather than `Optional[X]`.
- Domain functions are `async` when they do I/O and plain `def` when pure.
- Error mapping in routes: `ValueError` → 400, missing/invalid key → 401 (middleware), upstream failure → 502, feature disabled (`RuntimeError`) → 503. Error body is `{"detail": "..."}`; always `raise ... from exc`.
- Every data route has `@limiter.limit(...)` sized to its cost and takes `request: Request` as the first parameter. Only `OPEN_PATHS` bypass `X-App-Key`.
- Outbound fetches (`extract/fetch.py`) enforce robots, byte-size cap, and timeout. New outbound calls must match.
- Repeated expensive work goes through `cache.py`.
- Wire field names are `snake_case` (`source_url`, `expanded_queries`, `target_script`).

### Tests (`services/api/tests`)

- `pytest`, files named `tests/test_<module>.py`, fixtures in `tests/fixtures/`.
- `conftest.py` sets `APP_KEY`, `SEARCH_PROVIDER=mock`, `LLM_MODEL=none`, `CACHE_DIR` so the API runs with no external services.
- API tests use FastAPI `TestClient` with the `X-App-Key` header; provider tests use the mock provider and `extract/mock_pages.py`.

Run: `cd services/api && pytest`.

## Mobile (`apps/mobile`)

### Layering

```
app/                 expo-router screens and layouts only               (entry layer)
  └─ src/components  presentational components
  └─ src/store       zustand stores (persisted with AsyncStorage)
  └─ src/utils       pure helpers (grouping, pdf HTML, scripts, fonts)
  └─ src/api         client.ts (single fetch wrapper) + types.ts        (shared layer)
  └─ src/theme.ts    colours and spacing tokens
```

- Screens live under `app/` using expo-router file conventions (`(tabs)/`, `[id].tsx`, `_layout.tsx`, `+not-found.tsx`). Screens compose components, stores, and utils; they do not contain reusable logic.
- All backend calls go through `api.*` in `src/api/client.ts`, which owns base URL, `X-App-Key`, JSON parsing, and error normalisation. Screens never call `fetch` directly.
- Response and domain types live in `src/api/types.ts`; screens do not declare their own copies.
- Stores: one file per concern (`saved.ts`, `history.ts`, `session.ts`); `create<State>()(persist(...))` with `createJSONStorage(() => AsyncStorage)` and a `saha-<name>` storage key. Exported hook is `use<Concern>`.
- Pure logic (`groupVersions`, `pdf`) lives in `src/utils` with a sibling `<name>.test.ts`.
- Components are function components with a local `type Props`, `StyleSheet.create` at the bottom, colours from `theme.ts`, fonts via `fontForScript(script)`.

### Conventions

- Files: `camelCase.ts` for utils/stores/api, `PascalCase.tsx` for components, router-mandated names under `app/`.
- Symbols: `camelCase` functions and variables, `PascalCase` components and types, `UPPER_SNAKE` module constants (`API_URL`, `APP_KEY`).
- Wire fields keep their backend `snake_case` names on app types (`source_url`, `source_domain`); app-only derived fields are `camelCase` (`alsoOn`, `savedAt`). Do not rename wire fields when mapping.
- `import type` for type-only imports; external imports first, then a blank line, then relative imports.
- No secrets in `app.config.ts`, `eas.json`, or `EXPO_PUBLIC_*` beyond the app key and API URL.
- The AI-generated meaning is always shown with `MeaningDisclaimer`; site translations are never copied.

### Tests

- `jest` via `npm test`; unit tests sit beside the util as `<name>.test.ts`. Components and screens are currently untested; new pure logic must ship with a test.

## Domain glossary

| Term | Meaning | Avoid |
|---|---|---|
| sloka / mantra | The named text the user searches for | hymn, poem |
| verse | One line/stanza string inside a version (`verses: list[str]`) | line, stanza |
| version | One extracted rendering of a sloka from one source URL (`SlokaVersion`) | variant, result, item (except `SavedItem`) |
| hit | One web search result (`SearchHit`) | link, result |
| script | Writing system identifier from `SUPPORTED_SCRIPTS` (`devanagari`, `tamil`, `iast`, …) | language (for the writing system) |
| fingerprint | SLP1-normalised hash used to group duplicate versions | hash, key |
| provider | A search backend implementing `SearchProvider` | engine, adapter, service |
| meaning | AI-generated English rendering of a verse | translation (in user-facing text) |

## Known drift to watch for

Findings that have historically appeared and are worth checking in any target:

- Script lists duplicated between `app/models.py` and `src/utils/scripts.ts` without a test keeping them aligned.
- Sequential `await` over independent provider calls in `search_sloka`.
- Screens declaring inline response types instead of importing from `src/api/types.ts`.
- New routes missing a rate limit or catching `Exception` without `from exc`.
