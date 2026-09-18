# App Store Compliance Rule Catalogue

Each row: what Apple requires, how to check it in this repository, and which scanner rule (if any) covers it. **Check** values: *Scanner* (rule id), *Manual* (reviewer reads code/UX), *ASC* (App Store Connect setting outside the repo). Guideline numbers follow the [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/); revisions land several times a year (recent ones: Nov 2025 added 5.1.2(i) third-party AI wording and 4.1(c); Feb 2026 brought anonymous chat under 1.2; Jun 2026 rewrote 4.3(b) and 1.2 responsibilities).

## Part A: Submission-blocking technical requirements

| Requirement | How to check | Check |
|---|---|---|
| Bundle identifier set and matches App Store Connect | `ios.bundleIdentifier` in app config equals the ASC record | Scanner CFG-001, ASC |
| Export compliance declared | `ios.infoPlist.ITSAppUsesNonExemptEncryption` present; `false` only if the app uses no custom crypto beyond HTTPS/OS APIs | Scanner CFG-002/003 |
| App Transport Security intact | No `NSAllowsArbitraryLoads: true`; no plain `http://` endpoints in mobile code | Scanner CFG-004, SRC-002 |
| Privacy manifest (`PrivacyInfo.xcprivacy`) | App declares `NSPrivacyCollectedDataTypes` for data it collects and `NSPrivacyAccessedAPITypes` with approved reason codes for any required-reason API it calls; each listed third-party SDK ships its own signed manifest. Expo generates the merged manifest at prebuild; app-level entries go in `ios.privacyManifests` | Scanner CFG-005, SRC-009, SRC-014; Manual: inspect prebuild output |
| Purpose strings for protected resources | Every `NS*UsageDescription` implied by an installed package exists and states the specific in-app use | Scanner DEP-001, CFG-009 |
| Production build profile | EAS `production`: no `developmentClient`, not `internal` distribution, auto-increment build number | Scanner EAS-001/002 |
| Build reaches a real backend | Production env sets `EXPO_PUBLIC_API_URL`/`EXPO_PUBLIC_APP_KEY`; localhost fallback cannot ship | Scanner CFG-007 |
| No secrets in the client | No provider keys, LLM keys, or tokens in source, `app.config.*`, `eas.json`, or `.env` committed for the app | Scanner SRC-001; Manual |
| Built with the currently required Xcode/iOS SDK | EAS build image satisfies Apple's minimum SDK announcement for the year | Manual / ASC |
| Icons, launch screen, orientation, device family | Assets present; `supportsTablet` decision matches screenshots supplied | Scanner CFG-006; ASC |

## Part B: Guidelines by section

### 1. Safety

| # | Requirement | How to check | Check |
|---|---|---|---|
| 1.1 / 1.1.1 | No objectionable content; nothing defamatory, discriminatory, or mean-spirited, including about religion | Review UI copy, listing copy, and how AI output is constrained (prompt + disclaimer); confirm no ranking/disparaging of traditions | Manual |
| 1.1.6 | No false information or misleading features | AI meanings labelled as generated and not "official" | Manual, Scanner SRC-010/012 |
| 1.1.7 | No manipulative ratings prompts | Only `SKStoreReviewController` (`expo-store-review`) | Scanner SRC-008 |
| 1.2 | User-generated content: filtering, reporting, blocking, published contact, developer responsibility for violating content (Jun 2026); anonymous chat is UGC (Feb 2026) | Applies only if users can publish content to other users | Manual |
| 1.5 | Developer contact information in app or metadata | Support URL + contact email in listing; privacy/terms name a contact | Manual, ASC |
| 1.6 | Data security: appropriate safeguards | HTTPS only, app key not treated as a secret, rate limiting, input caps | Scanner SRC-001/002; Manual |

### 2. Performance

| # | Requirement | How to check | Check |
|---|---|---|---|
| 2.1 | App completeness: no crashes, no placeholders, no beta labels, working demo path, review notes | Placeholder strings; production env; graceful error states; `docs/app-store.md` review notes current | Scanner SRC-003, CFG-007/008; Manual |
| 2.3 | Accurate metadata: description, screenshots, keywords, age rating; no other-platform references (2.3.10); hidden features disclosed (2.3.1) | Compare `docs/app-store.md` to the build; screenshots taken from the submitted build | Scanner SRC-004, DOC-006/007; Manual |
| 2.4.1 | iPad compatibility if `supportsTablet` is true | Layout QA on iPad or set to false | Scanner CFG-006 |
| 2.5.1 | Public APIs only, no private frameworks | Dependencies are standard Expo/RN modules | Manual (dependency review) |
| 2.5.2 | Self-contained; downloaded code (OTA JS) may not change primary purpose or unlock features | `expo-updates` channel policy | Scanner EAS-004; Manual |
| 2.5.4 | Background modes only for declared purposes | `UIBackgroundModes` justified | Manual |
| 2.5.6 | Web browsing via WebKit only; app is not a browser | WebView usage | Scanner DEP-009, SRC-011 |
| 2.5.13 / 2.5.14 | Face ID and recording require purpose strings and consent | Purpose strings; recording indicator | Scanner DEP-001 |

### 3. Business

| # | Requirement | How to check | Check |
|---|---|---|---|
| 3.1.1 | Digital content/features sold only via In-App Purchase; no external purchase links or CTAs (unless an entitlement applies) | External payment SDKs; `openURL` to buy/donate pages | Scanner DEP-006, SRC-005 |
| 3.1.2 | Subscriptions: clear terms, restore, no misleading trials | Only if IAP present | Scanner DEP-007; Manual |
| 3.1.5 | Physical goods/services may use external processors | Only if selling physical goods | Manual |
| 3.2.1(vi) | Donations only to approved nonprofits via Apple Pay/IAP rules | Any donate flow | Scanner SRC-005; Manual |
| 3.2.2 | No arbitrary "tips", no paid review manipulation, no loan traps | Any monetisation | Manual |

### 4. Design

| # | Requirement | How to check | Check |
|---|---|---|---|
| 4.0 | Meets basic design expectations; no broken links, poor UX | Walk each screen in the build | Manual |
| 4.1 / 4.1(c) | No copycat icon/name/brand of another developer | Icon and name review | Manual |
| 4.2 | Minimum functionality: more than a website wrapper; useful without other apps | Native features beyond fetched content (transliteration, saved items, PDF) | Scanner DEP-009; Manual |
| 4.3(b) | Not indistinguishable from existing apps; low-effort/saturated-category apps may be refused or removed (Jun 2026) | Listing copy states the differentiators; feature set is not a trivial variant | Manual |
| 4.5.4 | Push notifications only with consent, not required for use, no spam | Only if `expo-notifications` | Scanner DEP-002 |
| 4.7 | Mini apps / HTML5 games scope | N/A unless downloading executable content | Manual |
| 4.8 | Login services: if any third-party/social login is offered, Sign in with Apple (or a privacy-equivalent option) must be offered too | Login SDKs vs Apple auth SDK | Scanner DEP-005 |

### 5. Legal

| # | Requirement | How to check | Check |
|---|---|---|---|
| 5.1.1(i) | Privacy policy link in app metadata and inside the app; covers data collected, how it is used, retention/deletion, third parties, and confirms third parties give equal protection | `docs/privacy.md` content; served publicly (`/privacy`) without app key; linked from the app | Scanner DOC-001/002/003, API-001/002; Manual (in-app link) |
| 5.1.1(ii) | Permission requested before collecting data, with purpose strings; app works if denied | Permission flows | Scanner DEP-001/002; Manual |
| 5.1.1(iii) | Data minimisation: collect only what the feature needs | Logging of queries/page text; caches keyed by content not identity | Scanner SRC-006/007; Manual |
| 5.1.1(v) | If the app supports account creation, it must offer in-app account deletion | Auth code vs delete flow | Scanner ACC-001 |
| 5.1.1(ix) | Highly regulated fields need institutional developer accounts | N/A unless finance/health/etc. | Manual |
| 5.1.2(i) | Data may not be used or shared beyond disclosed purposes; **must clearly disclose sharing with third parties, including third-party AI, and obtain explicit permission first** | Trace user input leaving the device to search/LLM providers; find a disclosure + consent before first send; privacy policy names providers | Scanner AI-001/002, DOC-003; Manual (flow) |
| 5.1.2(ii)/(iii) | No repurposing data, no building profiles from collected data | Backend caching/log usage | Manual |
| App Tracking Transparency | Tracking across apps/sites requires ATT prompt and `NSUserTrackingUsageDescription` | Tracking/ads SDKs | Scanner DEP-003 |
| 5.1.4 | Kids category / children's data rules | Only if targeting children | Manual |
| 5.1.5 | Location only with consent and clear purpose | `expo-location` | Scanner DEP-001 |
| 5.2.1 | Only content you own or are licensed to use (fonts, icons, text) | Font licences (Noto = OFL), icon origin | Manual |
| 5.2.2 | Third-party sites/services: may not use their content without authorization; provide documentation on request | Scripture treated as public domain, attribution shown, no copying of site translations/commentary, robots respected, review notes prepared | Scanner SRC-012/013; Manual |
| 5.2.3 | No downloading media from third-party sources without authorization | N/A unless fetching audio/video | Manual |
| 5.6 | Developer Code of Conduct: honest metadata, responsive to reviewers, no manipulation | Review notes and communications | Manual |

## Part C: App Store Connect requirements (outside the repo)

| Item | Requirement | Source of truth in repo |
|---|---|---|
| Privacy policy URL | Public HTTPS URL, no login | API `/privacy`; `docs/app-store.md` |
| App Privacy "nutrition labels" | Every data type the app or its SDKs collect, with linked/tracking flags; includes server-side collection triggered by the app | `docs/app-store.md` §3 must match code |
| Age rating questionnaire | Answer the current questionnaire (tiers 4+, 9+, 13+, 16+, 18+); unrestricted web access and user-generated content questions | `docs/app-store.md` |
| Review notes and demo | How to exercise every feature; demo account if any login | `docs/app-store.md` §5 |
| Support URL and contact | Reachable page and email | `docs/app-store.md` |
| Agreements, tax, banking | Active before submission | `docs/apple-developer.md` |
| Screenshots | From the submitted build, correct device sizes, no other-platform UI | `docs/app-store.md` §4 |
| Encryption export | Matches `ITSAppUsesNonExemptEncryption` | `app.config.ts` |

## Severity mapping used by the scanner

- **BLOCKER**: Part A failures that stop upload/processing or guarantee rejection, credentials in the bundle.
- **REQUIRED**: unmet guideline text (5.1.x, 4.8, 3.1.1, 2.1 placeholders, missing purpose strings, missing disclaimers).
- **VERIFY**: manifest completeness, logging content, consent-flow ordering, SDK behaviour, anything needing device or ASC confirmation.
- **INFO**: placeholders in docs/config, empty ASC ids, retired age tiers, platform mentions.
