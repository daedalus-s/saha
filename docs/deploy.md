# Deploy the Saha API

The API is a Docker image. Prefer **Render**; Fly.io is the alternative.

## Prerequisites

- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) (`GEMINI_API_KEY`)
- A long random `APP_KEY` (the mobile app sends this as `X-App-Key`)

Brave / Google CSE keys are optional and only needed if you set `SEARCH_PROVIDER` back to `brave` or `google_cse`.

## Render

1. Push this repo to GitHub.
2. In the Render dashboard, New → Blueprint, and select the repo. Root [`render.yaml`](../render.yaml) defines `saha-api`.
3. Set secret env vars in the dashboard: `GEMINI_API_KEY`, and copy the generated `APP_KEY`. Confirm `SEARCH_PROVIDER=gemini` and `LLM_MODEL=gemini/gemini-2.0-flash`.
4. After deploy, `https://<service>.onrender.com/health` should return `"status": "ok"`.
5. Privacy policy URL for App Store Connect: `https://<service>.onrender.com/privacy`
6. Terms URL: `https://<service>.onrender.com/terms`

Optional persistent disk mounted at `/app/.cache` keeps lyrics/meaning cache across deploys.

## Fly.io

From the repo root:

```bash
fly launch --config services/api/fly.toml --dockerfile services/api/Dockerfile --no-deploy
fly secrets set APP_KEY=... GEMINI_API_KEY=... LLM_MODEL=gemini/gemini-2.0-flash SEARCH_PROVIDER=gemini
fly deploy --config services/api/fly.toml --dockerfile services/api/Dockerfile
```

## Verify from a phone

The device cannot reach `localhost`. Use the public HTTPS URL as `EXPO_PUBLIC_API_URL` in EAS env / `app.config.ts`. Then:

```bash
curl -s https://YOUR_HOST/health
```

A 200 with `"status":"ok"` is enough to mark backend deploy healthy.
