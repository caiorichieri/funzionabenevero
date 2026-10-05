# RCA — FunzionaBene (portugues-writer-2) deploy failure: Fase C/D release

## Summary
The deploy fails at **build_image**. The real cause is the **Fase D SEO prerender** step
(`frontend/scripts/prerender.js`, wired as a `postbuild` hook on `yarn build` in
`frontend/package.json`). It uses **`puppeteer-core`**, which does **not** bundle a browser —
it requires a **system Chromium** and hard-exits if absent:

```
$ node scripts/prerender.js
[prerender] FATAL: Chromium not found at /usr/bin/chromium. Install it or set CHROMIUM_PATH.
error Command failed with exit code 1.
```

The CRA build itself succeeds every time ("The build folder is ready to be deployed"); the
failure is always this postbuild prerender.

## What the deployer (I) already did — and what it proved
The build runs `yarn build` (→ prerender) in **TWO independent places**, and both need Chromium:

1. **Docker `frontend-build` stage** in `Dockerfile.cloudbuild` (cloud build step #2 `docker-build`).
2. **A separate Cloud Build step #8 `frontend-build-push`**, which executes
   `build-frontend-artifacts.sh` directly inside the builder image
   `customer-apps-node-base:v0.4.0` and runs its OWN `yarn build` to push assets to R2
   (the `FRONTEND_PREBUILT_DIR` reuse branch was NOT taken, so it rebuilds).

Manifest fixes applied (2 attempts, the per-deploy cap):
- Attempt 1: added `apt-get install chromium …` to the `frontend-build` stage → failed:
  `/bin/sh: apt-get: not found` → **the frontend base image is Alpine (apk), not Debian.**
- Attempt 2: switched to Alpine `apk add --no-cache chromium nss freetype harfbuzz ca-certificates ttf-freefont`
  and symlinked the binary to `/usr/bin/chromium`, in BOTH `Dockerfile` and `Dockerfile.cloudbuild`.
  → **step #2 `docker-build` now PASSES.** The failure moved forward to step #8
  `frontend-build-push`, which still hits the identical `Chromium not found` because
  `build-frontend-artifacts.sh` was not given the Chromium install.

So: the Chromium approach is correct and proven for the Docker stage. One build path remains.

## Remaining work

### (A) Manifest-level — the immediate next blocker (within deployer authority, but I am at the 2-edit cap)
`build-frontend-artifacts.sh` (one of the deployment manifest files) must install Chromium
before it runs `yarn build`. The step's builder is `customer-apps-node-base:v0.4.0` (Alpine).
Insert, right after the `cd "${SOURCE_DIR}/frontend"` line (before the `yarn install`/`yarn build`):

```sh
# Prerender (postbuild hook) uses puppeteer-core → needs a system Chromium.
if [ -z "${FRONTEND_PREBUILT_DIR}" ]; then
  apk add --no-cache chromium nss freetype harfbuzz ca-certificates ttf-freefont || true
  [ -e /usr/bin/chromium ] || ln -s "$(command -v chromium-browser || echo /usr/bin/chromium-browser)" /usr/bin/chromium
  export CHROMIUM_PATH=/usr/bin/chromium
fi
```

### (B) SOURCE-level — the deeper design issue E1 MUST resolve (no manifest can fix this)
`prerender.js` runs at **build time** and, per its own code, **fails hard** on unreachable API,
empty page, or a route whose `#root` renders < 800 chars. At build time it talks to
`BACKEND_URL` = the **currently-live production backend** (the previous deploy) and the
**un-migrated production DB** — because this release's new backend + the Mongo slug migration
only go live *after* the build (promote/mongo steps run later in the pipeline). Consequences:

- `GET ${BACKEND_URL}/api/public/blog` returns the current posts **without `slug`** (migration
  applied to preview DB only so far), so `listBlogSlugs()` falls back to `_id` → `/blog/<ObjectId>` routes.
- `BlogPostPage` detects the ObjectId and fetches the **new** endpoint
  `GET /api/public/blog/by-id/{id}` — which **does not exist on the live/old backend yet** → 404.
- If that route then renders an error/empty state (`#root` innerLen < 800), `renderRoute()` throws,
  `failures > 0`, and prerender calls `die(...)` → build fails **again**, even with Chromium present.

In short: the prerender has a **build-time dependency on post-deploy backend/DB state**. Even after
fix (A) lands, the build may still fail on blog-detail route rendering for this specific release.

**Recommended source changes (pick one or combine):**
1. Make prerender **resilient**: treat blog-detail (and therapist) route failures as
   **non-fatal** (log + skip) instead of `die()`, so SSR is best-effort and the build never
   blocks on data that isn't live yet. The static routes already render fine.
2. **Gate** the whole prerender behind an env flag (e.g. `PRERENDER_ENABLED`) and/or point it at a
   build-time-reachable data source, so a release that changes endpoints/data can deploy first and
   prerender on a subsequent build once the backend+DB are live.
3. Ensure the API the prerender targets is the **new** backend (not the old live one) — i.e. decouple
   prerender from the deploy ordering — if full SSR of new routes at build time is a hard requirement.

## Scope / impact
- **Live app is UNAFFECTED.** Failed runs are never promoted; `portugues-writer-2.emergent.host`
  (and funzionabene.it) still serve the last good run `f46459eb`.
- Template: `fastapi_react_mongo_shadcn_base_image` (farm), frontend_type `cloudflare`, tier_0.
- Failed runs: 528507de… (initial report), 2ad7e97d… (apt-get attempt), 9df628ff… (apk attempt — docker-build passed, frontend-build-push failed).

## Verification done
- Build logs: confirmed the exact `[prerender] FATAL: Chromium not found` on step #2 (before fix)
  and step #8 (after fix), and `apt-get: not found` proving Alpine.
- Source read in eph sandbox: `frontend/package.json` (`"postbuild": "node scripts/prerender.js"`)
  and `scripts/prerender.js` (puppeteer-core, `CHROMIUM = process.env.CHROMIUM_PATH || "/usr/bin/chromium"`,
  hard `die()` on fetch/render failure).
- Not reproduced end-to-end: the eph sandbox has no app secrets and cannot reach the live
  backend/DB, so the build-time API/render behavior (item B) is diagnosed from the code + logs,
  not executed.
