# Saha mobile app (Expo)

Expo **SDK 57** (matches current Expo Go). Use Node 20.19.4+, 22.13+, or 24.3+.

If a portable Node 20 is unpacked at `.tools/node-v20`, `npm start` falls back to it when your default Node is too old.

```bash
cp .env.example .env
npm install
npm start
```

Do not add `expo-print` (or other packages without an `app.plugin.js`) to the `plugins` array in `app.config.ts`.

On a physical device, set `EXPO_PUBLIC_API_URL` to the hosted API (`https://saha-api-lbbn.onrender.com`) or your computer's LAN IP. Android emulator: `http://10.0.2.2:8000`.

See [`../../docs/eas.md`](../../docs/eas.md) for EAS builds and [`../../docs/app-store.md`](../../docs/app-store.md) for App Store submission.
