#!/usr/bin/env node
/**
 * Sitemap generator — pure Node, zero browser dependency.
 *
 * Always produces build/sitemap.xml, overwriting any pre-existing file
 * (including public/sitemap.xml copied by CRA). This script MUST never fail
 * the build: on any error it degrades to the static-routes-only sitemap.
 *
 * Blog URLs: union of (a) fixed production slug mapping (committed) and
 * (b) slugs returned by the live /api/public/blog if reachable at build
 * time. Deduplicated. Guarantees newly-published articles enter the
 * sitemap on the next deploy without a code change.
 */
const fs = require("fs");
const path = require("path");

const BUILD_DIR = path.resolve(__dirname, "..", "build");
const PUBLIC_URL = process.env.PRERENDER_PUBLIC_URL || process.env.PUBLIC_URL || "https://funzionabene.it";
const API_URL = process.env.PRERENDER_API_URL || process.env.REACT_APP_BACKEND_URL;
const TIMEOUT_MS = 5000;

// ─── Static public routes (kept in sync with scripts/prerender.js) ──────
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

// ─── Immutable production blog slug mapping (synced with backend/migrations/blog_slug_migration.py) ──
// If an article is new (post-mapping) the API fetch below will add it on top.
const FIXED_BLOG_SLUGS = [
  "il-desiderio-sessuale-cos-e-come-cambia-e-quando-ascoltarlo",
  "eiaculazione-precoce-oltre-il-tabu-verso-la-cura",
  "vaginismo-quando-il-corpo-chiede-protezione",
  "disfunzione-erettile-ritrovare-la-fiducia-nel-proprio-corpo",
  "l-orgasmo-femminile-un-viaggio-non-una-destinazione",
  "comunicazione-e-intimita-come-parlarsi-davvero",
  "la-sessualita-nel-tempo-cambia-ma-non-finisce",
  "orientamento-sessuale-e-identita-di-genere-un-percorso-di-scoperta",
  "il-desiderio-dopo-il-parto-ritrovarsi-nel-corpo-che-cambia",
  "pornografia-e-intimita-reale-quando-lo-schermo-prende-il-sopravvento",
  "anorgasmia-quando-il-piacere-sembra-lontano",
  "sessualita-e-malattia-cronica-il-corpo-cambia-il-piacere-puo-restare",
  "dispareunia-quando-fare-l-amore-fa-male",
  "immagine-corporea-e-sessualita-amarsi-per-amarsi",
  "la-terapia-sessuologica-cos-e-davvero-e-a-chi-si-rivolge",
];

const log = (...a) => console.log("[sitemap]", ...a);

async function fetchJsonWithTimeout(url) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const r = await fetch(url, { headers: { Accept: "application/json" }, signal: ctrl.signal });
    clearTimeout(t);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    log(`WARN: ${url} unreachable (${e.message}) — falling back`);
    return null;
  }
}

async function collectBlogSlugs() {
  const set = new Set(FIXED_BLOG_SLUGS);
  if (!API_URL) {
    log("WARN: REACT_APP_BACKEND_URL not set — using fixed mapping only.");
    return Array.from(set);
  }
  const list = await fetchJsonWithTimeout(`${API_URL}/api/public/blog`);
  if (Array.isArray(list)) {
    let added = 0;
    for (const a of list) {
      if (a && typeof a.slug === "string" && a.slug.length > 0 && !set.has(a.slug)) {
        set.add(a.slug);
        added++;
      }
    }
    log(`API /public/blog returned ${list.length} articles; +${added} new slug(s) added.`);
  }
  return Array.from(set);
}

async function collectTherapistRoutes() {
  if (!API_URL) return [];
  const list = await fetchJsonWithTimeout(`${API_URL}/api/public/terapisti`);
  if (!Array.isArray(list)) return [];
  const out = list
    .filter((t) => t && t._id && t.documenti_verificati && !t.sospeso && !t.is_test)
    .map((t) => `/terapeuti/${t._id}`);
  log(`${out.length} therapist public routes.`);
  return out;
}

function buildXml(routes) {
  const now = new Date().toISOString().slice(0, 10);
  const seen = new Set();
  const unique = routes.filter((r) => (seen.has(r) ? false : (seen.add(r), true)));
  const urls = unique.map((r) =>
    `  <url><loc>${PUBLIC_URL}${r === "/" ? "" : r}</loc><lastmod>${now}</lastmod></url>`
  ).join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`;
}

(async function main() {
  if (!fs.existsSync(BUILD_DIR)) {
    console.error("[sitemap] build/ does not exist — run `yarn build` first.");
    process.exit(0);  // never fail the build
  }
  try {
    const blogSlugs = await collectBlogSlugs();
    const blogRoutes = blogSlugs.map((s) => `/blog/${s}`);
    const therapistRoutes = await collectTherapistRoutes();
    const routes = [...STATIC_ROUTES, ...blogRoutes, ...therapistRoutes];
    const xml = buildXml(routes);
    const outPath = path.join(BUILD_DIR, "sitemap.xml");
    fs.writeFileSync(outPath, xml, "utf8");
    log(`✅ sitemap.xml written (${routes.length} URLs: ${STATIC_ROUTES.length} static, ${blogRoutes.length} blog, ${therapistRoutes.length} therapist)`);
  } catch (e) {
    console.error("[sitemap] unexpected error:", e);
    // Fallback: static-only sitemap, never block the build
    try {
      const xml = buildXml(STATIC_ROUTES);
      fs.writeFileSync(path.join(BUILD_DIR, "sitemap.xml"), xml, "utf8");
      log(`WARN: fallback sitemap written with ${STATIC_ROUTES.length} static routes only`);
    } catch (e2) {
      console.error("[sitemap] fallback also failed:", e2);
    }
    process.exit(0);
  }
})();
