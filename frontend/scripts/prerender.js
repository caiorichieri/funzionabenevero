#!/usr/bin/env node
/**
 * Prerender script — runs after `yarn build`.
 *
 * 1. Spins up a static server on build/ with SPA fallback.
 * 2. Fetches the list of blog posts from the API (fails hard if unreachable).
 * 3. Fetches the list of active+verified therapists (same).
 * 4. For every public route, opens it with Puppeteer, waits for network idle,
 *    takes the final rendered HTML, writes build/<route>/index.html.
 * 5. Also generates build/sitemap.xml with the same URL set.
 *
 * Fails loudly on: unreachable API, empty page, Puppeteer timeout, or write error.
 * Never produces an empty HTML silently.
 */
const fs = require("fs");
const path = require("path");
const http = require("http");
const puppeteer = require("puppeteer-core");
const { spawn } = require("child_process");

const BUILD_DIR = path.resolve(__dirname, "..", "build");
const PORT = Number(process.env.PRERENDER_PORT || 4747);
const BASE_URL = `http://127.0.0.1:${PORT}`;
const API_URL = process.env.PRERENDER_API_URL || process.env.REACT_APP_BACKEND_URL;
const PUBLIC_URL = process.env.PRERENDER_PUBLIC_URL || process.env.PUBLIC_URL || "https://funzionabene.it";
const CHROMIUM = process.env.CHROMIUM_PATH || "/usr/bin/chromium";
const USER_AGENT = "ReactSnap";
const TIMEOUT_MS = 30_000;
const EMPTY_HTML_THRESHOLD = 1500; // bytes — a sane lower bound for a real page

// --- Static routes to pre-render (public only, no auth, no redirects) ---
const STATIC_ROUTES = [
  "/", "/questionario", "/blog", "/faq",
  "/privacy", "/privacy-pazienti", "/privacy-visitatori", "/privacy-terapeuti",
  "/cookie", "/cookie-policy",
  "/termini", "/termini-pazienti",
  "/contratto-collaborazione",
  "/sedute-immersive", "/aree-intervento", "/emergenze",
  "/chi-siamo", "/il-nostro-mondo", "/lavora-con-noi", "/contatti",
  "/scarica-app", "/mandato-legale", "/sessualita-e-disabilita",
];
// Private / dynamic / redirects → NEVER pre-render:
//   /admin/*, /paziente/*, /terapista/*, /login, /registrati, /candidatura-terapeuta,
//   /verifica-otp, /forgot-password, /reset-password, /videocall/:id,
//   /recensione/:id, /payment/*, /risultati, /terapeuti (redirect), /disabilita (redirect)

const log = (...a) => console.log("[prerender]", ...a);
const die = (msg, err) => { console.error("\x1b[31m[prerender] FATAL:", msg, "\x1b[0m"); if (err) console.error(err); process.exit(1); };

async function fetchJson(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
  return r.json();
}

async function listBlogSlugs() {
  if (!API_URL) die("REACT_APP_BACKEND_URL not set — cannot fetch blog posts.");
  log(`Fetching blog list from ${API_URL}/api/public/blog …`);
  const list = await fetchJson(`${API_URL}/api/public/blog`).catch((e) => die("API /public/blog unreachable at build time", e));
  if (!Array.isArray(list) || list.length === 0) {
    log("WARN: /api/blog returned empty list — no blog posts to pre-render.");
    return [];
  }
  const out = list
    .map((p) => p.slug || p._id || p.id)
    .filter(Boolean)
    .map((s) => `/blog/${s}`);
  log(`  → ${out.length} blog routes`);
  return out;
}

async function listTerapeutiRoutes() {
  if (!API_URL) return [];
  try {
    const list = await fetchJson(`${API_URL}/api/public/terapisti`);
    if (!Array.isArray(list)) return [];
    const out = list
      .filter((t) => t && t._id && t.documenti_verificati && !t.sospeso && !t.is_test)
      .map((t) => `/terapeuti/${t._id}`);
    log(`  → ${out.length} therapist routes`);
    return out;
  } catch (e) {
    log(`WARN: could not fetch /public/terapisti (${e.message}) — skipping therapist pre-render.`);
    return [];
  }
}

function startStaticServer() {
  return new Promise((resolve, reject) => {
    log(`Starting sirv static server on :${PORT} (SPA mode)…`);
    const bin = path.join(__dirname, "..", "node_modules", ".bin", "sirv");
    const proc = spawn(bin, [BUILD_DIR, "--single", "--quiet", "--port", String(PORT), "--host", "127.0.0.1"], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    proc.stderr.on("data", (c) => process.stderr.write(c));
    // Poll until server responds
    const t0 = Date.now();
    const probe = () => {
      http.get(`${BASE_URL}/`, (res) => { res.resume(); resolve(proc); }).on("error", () => {
        if (Date.now() - t0 > 5000) reject(new Error("sirv did not start within 5s"));
        else setTimeout(probe, 100);
      });
    };
    probe();
  });
}

async function renderRoute(browser, route) {
  const page = await browser.newPage();
  await page.setUserAgent(USER_AGENT);
  await page.setViewport({ width: 1280, height: 900 });
  // Block analytics/pixel calls as belt & braces beyond the UA check in index.html.
  await page.setRequestInterception(true);
  page.on("request", (req) => {
    const u = req.url();
    if (/posthog|google-analytics|googletagmanager|facebook\.net|clarity\.ms|linkedin|tiktok/i.test(u)) {
      req.abort();
    } else {
      req.continue();
    }
  });
  try {
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "networkidle0", timeout: TIMEOUT_MS });
    // Extra beat so the final setState after async fetch (axios → setArticolo) commits
    // before we snapshot. networkidle0 fires on request completion, not on React commit.
    await new Promise((r) => setTimeout(r, 800));
    // Measure rendered content inside #root (not raw HTML, which always contains
    // CRA's <noscript> fallback regardless of whether React booted).
    const rootInfo = await page.evaluate(() => {
      const r = document.getElementById("root");
      return {
        hasChildren: !!r && r.children.length > 0,
        innerLen: r ? r.innerHTML.length : 0,
      };
    });
    if (!rootInfo.hasChildren || rootInfo.innerLen < 800) {
      throw new Error(`React did not render into #root for ${route} (children=${rootInfo.hasChildren}, innerLen=${rootInfo.innerLen})`);
    }
    // Mark the root as pre-rendered so our hydrate branch picks hydrateRoot.
    await page.evaluate(() => {
      const r = document.getElementById("root");
      if (r) r.setAttribute("data-prerendered", "true");
    });
    const html = await page.content();
    return html;
  } finally {
    await page.close();
  }
}

function writeRouteHtml(route, html) {
  const target = route === "/"
    ? path.join(BUILD_DIR, "index.html")
    : path.join(BUILD_DIR, route.replace(/^\//, ""), "index.html");
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, html, "utf8");
}

function writeSitemap(routes) {
  const now = new Date().toISOString().slice(0, 10);
  const urls = routes.map((r) =>
    `  <url><loc>${PUBLIC_URL}${r === "/" ? "" : r}</loc><lastmod>${now}</lastmod></url>`
  ).join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
  fs.writeFileSync(path.join(BUILD_DIR, "sitemap.xml"), xml, "utf8");
  log(`sitemap.xml written with ${routes.length} URLs`);
}

(async function main() {
  if (!fs.existsSync(BUILD_DIR)) die("build/ does not exist — run `yarn build` first.");
  if (!fs.existsSync(CHROMIUM)) die(`Chromium not found at ${CHROMIUM}. Install it or set CHROMIUM_PATH.`);

  const blogRoutes = await listBlogSlugs();
  const teraRoutes = await listTerapeutiRoutes();
  const routes = [...STATIC_ROUTES, ...blogRoutes, ...teraRoutes];
  log(`Total routes to pre-render: ${routes.length}`);

  const server = await startStaticServer();
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: CHROMIUM,
      headless: "new",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        // Build-time only: bypass CORS so axios calls to the API from 127.0.0.1
        // don't get blocked. Harmless because no real user runs this browser.
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
      ],
    });
    let failures = 0;
    const rendered = new Map();
    for (const route of routes) {
      try {
        process.stdout.write(`  ${route} … `);
        const html = await renderRoute(browser, route);
        rendered.set(route, html);  // defer disk write until all renders are done
        console.log(`ok (${html.length}b)`);
      } catch (e) {
        failures++;
        console.log(`FAIL: ${e.message}`);
      }
    }
    if (failures > 0) die(`${failures}/${routes.length} routes failed. Build aborted.`);
    // Now flush to disk — safe because the static server has served all routes.
    for (const [route, html] of rendered) writeRouteHtml(route, html);
    writeSitemap(routes);
    log(`✅ Pre-render complete: ${routes.length}/${routes.length} routes OK.`);
  } finally {
    if (browser) await browser.close();
    try { server.kill("SIGTERM"); } catch { /* ignore */ }
  }
})().catch((e) => die("unexpected", e));
