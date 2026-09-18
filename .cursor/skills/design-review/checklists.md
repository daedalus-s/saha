# Design Review Checklists

Apply to every file in scope and to every substantive unit inside it (class, function, component, hook, store, route handler). Each bullet is a question; a "no" is a candidate finding to verify.

## A. Responsibility and cohesion

- Does the module have a single reason to change? Can it be described in one sentence without "and"?
- Are unrelated helpers co-located only because they were written at the same time? (Sign: a `utils`/`helpers` file whose functions share nothing.)
- Do functions do one thing at one level of abstraction? Mixed levels (parsing bytes next to business rules) are a smell.
- Are there god objects: a module every feature imports and every feature edits?
- Does a route handler / screen contain business logic that siblings delegate to a domain module?
- Is state kept in the narrowest scope that works (local → component → store → server)?

## B. Coupling and dependency direction

- Do dependencies point inward: entry points (`main.py` routes, `app/` screens) → domain modules (`extract/`, `search/`, `src/utils`, `src/store`) → shared models/types → nothing? Reverse arrows are findings.
- Any import cycles (the inventory script lists them)?
- Does the target import a sibling's private internals (underscore-prefixed names, non-`__init__` exports, deep relative paths) instead of its public surface?
- Does the mobile app hold or infer anything the backend owns (LLM keys, search keys, ranking logic that must be consistent server-side)?
- Does the backend know about presentation (colours, layout, UI strings not meant for the wire)?
- Are third-party libraries wrapped at one seam (e.g. `SearchProvider`, `request<T>()`) or called from many places?
- Would swapping one dependency (search provider, LLM, storage) require edits outside its adapter?

## C. Abstraction fit

- Does a new abstraction match an existing seam? New providers implement the existing `Protocol`; new API calls go through `api.*` in `src/api/client.ts`; new screens use the router conventions.
- Is there speculative generality: interfaces with one implementation and no test double, configuration for things that never vary, plugin hooks nobody uses?
- Is there a missing abstraction: the same shape of code repeated three or more times with small variations?
- Do abstractions leak: callers need to know about HTTP status codes, HTML structure, or library-specific exceptions to use them correctly?
- Are boolean parameters that switch behaviour better expressed as separate functions or an enum?

## D. Data modelling and contracts

- Are request/response shapes declared in the shared model module (`app/models.py`, `src/api/types.ts`) rather than inlined at the call site?
- Do wire field names follow the existing convention (see conventions file) on both ends?
- Is validation performed at the boundary (Pydantic model, route guard) rather than deep inside the domain code, and not duplicated at both?
- Are optional fields genuinely optional, or is `Optional`/`?` hiding a missing invariant?
- Are enumerations (scripts, providers, statuses) defined once and referenced, not re-typed as string literals?
- Is persisted local data (AsyncStorage stores) versioned or at least tolerant of shape changes?
- Are IDs/fingerprints computed in one place with one definition?

## E. Error handling and resilience

- Are errors mapped to the same HTTP statuses and `{"detail": ...}` shape as sibling routes? (400 bad input, 401 unauthorised, 502 upstream failed, 503 feature disabled.)
- Are exceptions caught at the boundary that can do something about them, not swallowed mid-stack?
- Are broad `except Exception` / bare `catch {}` blocks justified, and do they preserve the cause (`from exc`)?
- Do outbound network calls carry a timeout, size limit, and retry/backoff policy consistent with `extract/fetch.py`?
- Does the UI have a defined state for loading, empty, error, and partial results, matching sibling screens?
- Are user-facing error messages meaningful, and are internal details kept out of them?
- Are rate limits declared for new routes at a level consistent with their cost?

## F. Efficiency

- Independent awaits run concurrently (`asyncio.gather`, `Promise.all`) rather than sequentially?
- Repeated expensive work (fetches, LLM calls, transliteration) cached where siblings cache (`app/cache.py`) and with a sensible key/TTL?
- Any N+1 pattern: a loop issuing one request/query per item that a batch call could replace?
- Any work on render paths or in hot loops that could be memoised or hoisted (regex compilation, JSON parsing, large `.map` chains re-run every render)?
- Unbounded growth: lists, caches, or stores that never evict; recursion without a depth cap; page bodies read without a size cap?
- Large payloads: are responses returning fields the client never uses, or the client requesting data it discards?
- Are algorithmic choices proportionate (e.g. O(n²) similarity comparisons acceptable for n ≤ 50 hits; not for unbounded n)?

## G. Naming and conventions

- File names match sibling conventions (see conventions file) for the language and folder.
- Symbol case matches the language convention (the inventory script flags deviations).
- Names say what, not how: `groupVersions` not `processArray`; `SlokaVersion` not `DataItem`.
- Domain vocabulary is used consistently: *sloka*, *verse*, *version*, *script*, *fingerprint*, *hit*, *provider*. Synonyms (`stanza`, `line`, `variant`, `language` for script) are findings.
- Booleans read as predicates (`is_`, `has_`, `can_`, `should_`); async functions are not named as if synchronous.
- Constants are `UPPER_SNAKE` and live near their single point of use or in the module that owns the concept.
- Route names, request/response model names, and client method names line up (`/transliterate` ↔ `TransliterateRequest` ↔ `api.transliterate`).
- No abbreviations that siblings spell out, and vice versa.

## H. Testability and tests

- Is pure logic separated from I/O so it can be tested without network, filesystem, or LLM?
- Are seams mocked the way siblings mock them (mock search provider, `mock_pages`, `LLM_MODEL=none`) rather than inventing a new mocking approach?
- Does each non-trivial module have a test file following the sibling naming (`tests/test_<module>.py`, `<name>.test.ts`)?
- Do tests assert behaviour and contracts rather than implementation detail?
- Are edge cases covered that the domain implies: empty verses, mixed scripts, unsupported script, oversized page, provider failure, duplicate hits?
- Are fixtures shared via `conftest.py` / shared test helpers rather than copy-pasted?

## I. Duplication and reuse

- Before flagging something as "new", search the repo for the same logic under another name.
- Is the same regex, mapping table, or constant defined in more than one place (e.g. script lists on both API and app)? If duplication across the API boundary is intentional, is it documented and tested to stay in sync?
- Are there near-identical functions differing only in a literal that should be a parameter?

## J. Dead and stale code

- Unused exports, imports, parameters, feature flags, or environment variables.
- Commented-out code, TODOs with no owner or issue, debugging leftovers.
- Compatibility shims for versions no longer supported.

## K. Security and trust boundaries

- Secrets and provider keys exist only in backend settings; never in `app.config.ts`, `eas.json`, or client bundles.
- Every new data route is behind the `X-App-Key` middleware unless deliberately added to `OPEN_PATHS` with a reason.
- Outbound fetches respect robots, size caps, timeouts, and scheme allow-lists as in `extract/fetch.py`.
- HTML from fetched pages or LLM output is never rendered unescaped (API `/privacy`, `/terms`, PDF HTML builder).
- User input is bounded (query length, verse count) before it reaches a paid upstream call.
- Logging does not include secrets or full page bodies.

## L. Documentation and discoverability

- Would a new engineer find this code where the sibling layout implies it should be?
- Public functions and models carry a one-line docstring/comment when the name alone is not enough.
- `docs/architecture.md` and `README.md` still describe the system accurately after this change.
- New environment variables are in `.env.example` with a comment.
