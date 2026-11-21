# Web App Setup — Vectora AI

This document describes how to set up the Vectora AI web application for local development and production deployment.

---

## Prerequisites

| Tool | Required Version | Install |
|------|----------------|---------|
| Node.js | 26.x | [nodejs.org](https://nodejs.org) or `nvm install 26` |
| npm | 11.x | Included with Node 26 |

Verify:
```bash
node --version   # v26.x.x
npm --version    # 11.x.x
```

---

## Clone and Install

```bash
git clone <repo-url>
cd mosqscan/web

npm install
```

---

## Environment Variables

Copy the example file and populate values for your environment:

```bash
cp .env.example .env.local
```

### Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_APP_VERSION` | ❌ | `1.0.0` | Displayed in the UI footer |
| `NEXT_PUBLIC_MAX_IMAGE_SIZE_MB` | ❌ | `20` | Client-side upload size hint |
| `NEXT_PUBLIC_MAX_VIDEO_SIZE_MB` | ❌ | `100` | Client-side upload size hint |
| `NEXT_PUBLIC_CONFIDENCE_THRESHOLD` | ❌ | `0.65` | Mirrored from backend for UI display only |

> [!IMPORTANT]
> `NEXT_PUBLIC_*` variables are embedded in the client bundle at build time. Do **not** place secrets in these variables. All sensitive auth operations are handled server-side by the backend.

---

## Local Development

Start the development server:

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000).

The dev server supports:
- Hot module replacement (HMR)
- Fast Refresh for React components
- API route proxying to the backend (configured via `next.config.js`)

### Connecting to a Local Backend

Ensure the backend is running (see [docker-deployment.md](docker-deployment.md)) and set:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Running Tests

```bash
# Unit and component tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

---

## Linting and Formatting

```bash
npm run lint       # ESLint
npm run lint:fix   # Auto-fix
npm run format     # Prettier
```

---

## Production Build

```bash
npm run build
```

This generates an optimised production build in `.next/`. To preview locally:

```bash
npm start
```

### Build Output

| Item | Location |
|------|----------|
| Static assets | `.next/static/` |
| Server bundle | `.next/server/` |
| Public files | `public/` |

---

## Docker Build (Web)

The web app is containerised as part of the full Compose stack. To build independently:

```bash
docker build -t vectora-web:latest ./web
```

Environment variables are injected at runtime via Docker Compose or Kubernetes ConfigMaps — **not** baked into the image at build time for production. Use Next.js [runtime configuration](https://nextjs.org/docs/app/building-your-application/configuring/environment-variables) or server-side rendering for sensitive values.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Module not found` on `npm run dev` | `node_modules` not installed | Run `npm install` |
| API calls fail with CORS error | Backend URL mismatch | Set `NEXT_PUBLIC_API_BASE_URL` correctly |
| Node version mismatch | Using Node < 26 | Switch with `nvm use 26` |
| Build fails with type errors | TypeScript strict violations | Fix types or check `tsconfig.json` |
