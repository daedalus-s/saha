# App Store Connect listing, TestFlight, and review

Complete [`apple-developer.md`](apple-developer.md) and a production EAS build first. The production binary must talk to a **live HTTPS API** (`EXPO_PUBLIC_API_URL` EAS secret). Keep the backend up for the entire review window.

## 1. Create / submit the app record

```bash
cd apps/mobile
eas build --platform ios --profile production
eas submit --platform ios --profile production
```

EAS can create the App Store Connect app. If you prefer to create it by hand:

- Name: **Saha**
- Primary language: English (U.S.)
- Bundle ID: `com.saha.sloka`
- SKU: `saha-ios-001`

After the record exists, paste the numeric Apple ID into `apps/mobile/eas.json` `submit.production.ios.ascAppId` (or let `eas submit` create it).

## 2. Listing copy

| Field | Suggested value |
| --- | --- |
| Name | Saha |
| Subtitle | Slokas, scripts, and meaning |
| Category | Reference (secondary: Lifestyle) |
| Age rating | 4+ on the current questionnaire (no unrestricted web, no user-generated chat) |
| Privacy policy URL | `https://` plus the deployed API host, path `/privacy` (must open without login) |
| Support URL | the GitHub repo or a simple page |
| Description | Saha looks up Hindu sloka or mantra lyrics by name in a script you choose (via Gemini), transliterates the verses into another Indic script, can generate an English meaning, and exports a PDF. Lyrics and meanings are AI-generated and labelled as such. Differentiators: multi-script transliteration, side-by-side layout, on-device saved items, PDF export. |

## 3. App Privacy labels

In App Store Connect → App Privacy:

- Data collected: **Search History / User Content** (the sloka name typed) — used for **App Functionality**, **not linked to identity**, **not used for tracking**.
- Consider **Other Usage Data** for host IP logs if they are retained beyond transient security use (not linked, not tracking, App Functionality).
- No contact info, location, purchases, or identifiers for ads.

## 4. Screenshots

iPhone only (set the device family to iPhone in `app.config.ts` so iPad screenshots are not required):

- 6.7" display — 3–5 shots: Search (include the data-sharing sheet once), Results with script chips, Detail with transliteration, PDF share sheet
- 6.1" display — same set

Capture from the **submitted** production or TestFlight build, not a localhost Expo Go session.

## 5. Review notes (paste into App Review Information)

> Saha looks up Hindu scripture (slokas/mantras) by name. On first search (and on Show meaning if the user has not already agreed) it shows a disclosure sheet: the typed name and selected script are sent to a third-party AI (Gemini) to return lyrics; Show meaning sends verse text to a third-party AI provider. The user must tap Continue before any of those sends; Not now cancels. Permission can be withdrawn on the Search screen. Lyrics are labelled “AI-generated lyrics; verify with a printed edition.” English meanings are labelled “AI-generated meaning; verify with a scholar.” There is no user login. Demo: accept the sheet, pick Devanagari, then type “Hanuman Chalisa” on the Search screen. Privacy policy: the `/privacy` path on the same host as the API.

This addresses guideline 5.1.2(i) via the disclosure sheet. Lyrics are generated, not scraped from a third-party site.

Demo account: none (stateless). Backend must be live during review.

## 6. TestFlight

After processing, add internal testers (App Store Connect users) and install on a real iPhone. Check the consent sheet (Continue / Not now / withdraw), search, lyrics, transliteration, meaning, PDF share, and saved items. Fix crash/font issues, then cut a new build if needed (`eas build` + `eas submit`).

## 7. Submit for review

Select the processed build, complete the version, and Submit. Typical first review is 24–48 hours.

## 8. Privacy manifest check (once per SDK bump)

```bash
cd apps/mobile
npx expo prebuild -p ios --no-install
```

Inspect `ios/Saha/PrivacyInfo.xcprivacy` (name may vary). Confirm Search History / Other User Content appear. App-level types are declared in `app.config.ts` `ios.privacyManifests`. Only add `NSPrivacyAccessedAPITypes` if the **app** itself calls a required-reason API.

## Android

Keep `eas build --platform android --profile preview` green. Google Play listing is out of v1 scope.
