# Deploy the Saha API

The API is a Docker image. Prefer **Render**; Fly.io is the alternative.

## Prerequisites

- Brave Search API key **or** Google Programmable Search Engine key + CX
- An LLM provider key if you want extraction/translation (`LLM_MODEL` not `none`)
- A long random `APP_KEY` (the mobile app sends this as `X-App-Key`)

## Render

1. Push this repo to GitHub.
2. In the Render dashboard, New → Blueprint, and select the repo. Root [`render.yaml`](../render.yaml) defines `saha-api`.
3. Set secret env vars in the dashboard: `BRAVE_API_KEY` (or `GOOGLE_CSE_KEY` + `GOOGLE_CSE_CX`), `OPENAI_API_KEY` (or Anthropic/Gemini), and copy the generated `APP_KEY`.
4. After deploy, `https://<service>.onrender.com/health` should return `"status": "ok"`.
5. Privacy policy URL for App Store Connect: `https://<service>.onrender.com/privacy`
6. Terms URL: `https://<service>.onrender.com/terms`

Optional persistent disk mounted at `/app/.cache` keeps extraction/translation cache across deploys.

## Fly.io

From the repo root:

```bash
fly launch --config services/api/fly.toml --dockerfile services/api/Dockerfile --no-deploy
fly secrets set APP_KEY=... BRAVE_API_KEY=... OPENAI_API_KEY=... LLM_MODEL=gpt-4o-mini SEARCH_PROVIDER=brave
fly deploy --config services/api/fly.toml --dockerfile services/api/Dockerfile
```

## Verify from a phone

The device cannot reach `localhost`. Use the public HTTPS URL as `EXPO_PUBLIC_API_URL` in EAS env / `app.config.ts`. Then:

```bash
curl -s https://YOUR_HOST/health
```

A 200 with `"status":"ok"` is enough to mark backend deploy healthy.
