# EAS and preview builds

The mobile app lives in `apps/mobile`. Builds are done with [Expo EAS](https://docs.expo.dev/build/introduction/). You do **not** need a Mac; cloud builders sign iOS binaries.

## One-time setup

```bash
npm install -g eas-cli
cd apps/mobile
npx expo login          # or eas login
eas init                # creates the Expo project and writes the projectId into app.config.ts
```

Set EAS secrets (Production / Preview):

- `EXPO_PUBLIC_API_URL` — `https://<your-api-host>`
- `EXPO_PUBLIC_APP_KEY` — same value as the API `APP_KEY`

```bash
eas secret:create --name EXPO_PUBLIC_API_URL --value https://saha-api.onrender.com --scope project
eas secret:create --name EXPO_PUBLIC_APP_KEY --value <the-app-key> --scope project
```

## Profiles (`eas.json`)

| Profile | Use |
| --- | --- |
| `development` | Dev client, internal distribution |
| `preview` | Release build, internal / TestFlight-like QA on device |
| `production` | App Store / Play Store binary |

## Preview on a device

```bash
cd apps/mobile
eas build --platform ios --profile preview
```

Install the resulting artifact on a registered device (or via the Expo dashboard QR). Confirm:

1. Search box loads
2. A search hits the hosted `/search` (Charles / server logs)
3. `/health` is reachable from the phone’s network

Android (kept buildable, not submitted in v1):

```bash
eas build --platform android --profile preview
```

## Production

Production builds **fail at config time** if `EXPO_PUBLIC_API_URL` is missing or is a loopback address, and if `EXPO_PUBLIC_APP_KEY` is missing. Do not put the host in `eas.json`; set EAS secrets:

```bash
eas secret:create --name EXPO_PUBLIC_API_URL --value https://YOUR_DEPLOYED_API --scope project
eas secret:create --name EXPO_PUBLIC_APP_KEY --value <the-app-key> --scope project
```

Then:

```bash
eas build --platform ios --profile production
eas submit --platform ios --profile production
```

Confirm the review device can `GET https://YOUR_DEPLOYED_API/health` and that `/privacy` opens without an app key.

See [`apple-developer.md`](apple-developer.md) and [`app-store.md`](app-store.md) for the store-side steps.
