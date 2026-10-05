# PRD — FunzionaBene (piattaforma di sessuologia online)

**Dominio**: funzionabene.it  
**Operatore**: BIDOC SRL (P.za I Maggio 2/int.2, Spilimbergo PN · P.IVA 01985930930)  
**Modello**: piattaforma tecnologica di intermediazione tra pazienti e professionisti sanitari iscritti all'Albo. Riscossione in nome e per conto dei terapeuti via Mandato all'Incasso con Rappresentanza (NON datore di prestazione sanitaria).

## Original problem statement
Costruire una piattaforma psi/sessuologia completa che gestisca: terapisti (onboarding + verifica), pazienti, appuntamenti, videochiamate, fatturazione elettronica italiana (TD01/TD04 FatturaPA), rimborsi Stripe, GDPR, SEO, PWA, firma elettronica contratti e autocertificazioni DPR 445/2000. Lingua italiana. Mobile-first.

## Tech stack
- Frontend: React 19, react-router v6, framer-motion, lucide-react, Tailwind + shadcn/ui, react-helmet-async
- Backend: FastAPI (Python 3.11), motor (Mongo async), APScheduler, ReportLab, httpx, resend-py
- DB: MongoDB
- Infrastructure: supervisor + kubernetes ingress Emergent
- SSR/Pre-rendering: Puppeteer in `frontend/scripts/prerender.js` + sirv-cli (postbuild) — 47 route pubbliche snapshottate
- Integrazioni: Stripe, Daily.co (SFU, NON E2EE — cfr. RIMOZIONI_LEGALI.md), Resend (webhooks firmati svix), Twilio Verify (SMS) + Alpha Sender "Funzbene", Emergent Object Storage, Emergent LLM key per Claude/Nano Banana

## Core requirements
- Lingua: italiano (unico pubblico), stringhe italiane in tutti i template email/SMS
- Fiscal engine: Fattura TD01 + Nota di Credito TD04, marca da bollo €2 se importo ≥ €77,47, PDF con watermark BD "Bidoc" heart, XML FatturaPA, ZIP export admin
- GDPR: registro trattamenti T-01…T-07, DPIA, DPA integrato nel contratto collaborazione, retention per categoria, pseudonimizzazione in reportistica
- Firma elettronica: DPR 445/2000 autocertificazione + contratto collaborazione + consenso informato (gated flow con `MandatoAcceptanceGate` + `TherapistDocsGate`)
- Session management: video call room Daily.co con `nbf`/`exp` (15' pre + 15' post), token JWT scadenza, auto-complete `in_corso → completato` via sweep APScheduler
- Payments: Stripe Checkout con rimborsi (100% ≥ 24h, parziali < 24h), transizioni `payment_transactions`
- SEO: canonical, OG, JSON-LD (Organization + MedicalBusiness + WebSite + FAQPage + Person per terapisti), sitemap, meta description per route, pre-rendering statico

## Current status (checkpoint 2026-02)
Vedi `CHANGELOG.md` per lo storico completo.

### Ultime cose fatte
- 2026-02-21 — **Fix prerender resiliency** (post-RCA deploy `9df628ff`):
  - `scripts/prerender.js` reso best-effort: Chromium mancante o PRERENDER_ENABLED=false → `exit 0` con warning (build non fallisce più). Static routes fatali, dinamiche (blog/terapisti) best-effort. Articoli senza `slug` saltati (mai `/blog/<ObjectId>` generati). Sitemap elenca solo route pre-renderizzate con successo.
  - Risolto build-time vs post-deploy ordering flaw: al deploy iniziale il backend vecchio non ha i nuovi endpoint `/public/blog/by-id/` → listBlogSlugs vede articoli senza slug → 0 blog pre-renderizzati, build passa comunque. Al secondo deploy slug sono live → pre-render completo.
  - Verifica locale: yarn build senza env var → 23 static OK; con env var → 47/47 (23 static + 15 blog slug + 9 terapisti), 0 ObjectId pre-renderizzati.
- 2026-02-21 — **Fase D Blog Slug Migration + 301** (vecchia versione, superseded dal fix prerender):
  - 15 articoli in collection `articoli` hanno ora campo `slug` (kebab-case, idempotente, backup collection `articoli_backup_20261005_123109`).
  - Index unique sparse creato su `articoli.slug`.
  - Nuovi endpoint backend: `GET /api/public/blog/slug/{slug}` (primary lookup) e `GET /api/public/blog/by-id/{id}` (legacy, restituisce `redirect_to_slug`).
  - BlogPostPage.jsx: rilevamento ObjectId → chiamata `/by-id/`, `navigate(slug, { replace: true })`. Canonical SEMPRE sullo slug.
  - BlogPublicPage.jsx: tutti i link `to={/blog/${a.slug || a._id}}` (preserva compatibilità).
  - Prerender: snapshots solo con URL slug (zero ObjectId pre-renderizzati).
  - Sitemap: URL slug.
  - Fix bonus: rimosso canonical hardcoded in `public/index.html` (era `funzionabene.it/`) che causava canonical doppio su tutte le pagine pre-renderizzate.
  - 47/47 route pre-renderizzate con canonical corretto, verificato empiricamente sul preview (slug + ObjectId URL entrambi renderizzano correttamente, redirect client-side ok).
  - Opzione (a) middleware FastAPI 301 **NON possibile** nell'ingress Emergent (`/blog/*` va al frontend, backend non lo vede). Preparato `/app/memory/nginx_blog_301.conf` per futuro VPS self-hosted.
- 2026-02-21 — **Fase C audit legale (iter 1+2)**: rimozione testimonianze fittizie, stat panel LoginPage, claim "end-to-end" (frontend + backend GDPR), "Prima piattaforma italiana" x7, "1 su 8 ammessi", numeri VR 76%/9× rimossi completamente (studio Garcia-Palacios 2007 su fobie, non pertinente alla sessuologia), riformulazione claim "verificato" terapisti, "ogni trimestre" → "avvisi automatici 60/30 gg". Doc completo in `/app/memory/RIMOZIONI_LEGALI.md`.

### In progress
- **Deploy di C+D in produzione** (NEXT — eseguire ora).

### Backlog
- Deploy di C+D (DOPO verifica utente di C+D).
- **Fase B** — testi UX "48h", wording Waitlist (post-deploy).
- Stripe webhook `checkout.session.completed` fallimenti (P1 — investigare dopo deploy).
- Record pazienti orfani (P2).
- Scansione contenuti blog (`articoli` collection, 15 doc) per promesse mediche (P2 — non toccare, segnalare).
- Rating/stelle su profilo pubblico terapista (P3 — 1 review approvata nel DB ma nessuna UI).
- WhatsApp Business API fallback (P1 — plan in `/app/memory/WHATSAPP_MIGRATION_PLAN.md`).
- Storico sessioni paziente (P2).
- Coach Sessuale AI Claude Sonnet 5 (P2).
- Web Push VAPID (P2).
- Specializzazione tag "sessualità-disabilità" (P3).
- Fix `subprocess.run` blocking in `backup_service.py:57` → `asyncio.create_subprocess_exec` (P3).
- SDI electronic invoicing automation via Openapi.com (P3).
- Refactoring: `TerapistiPage.jsx` (899 LOC), `TerapistaProfile.jsx` (553 LOC), `cruscotto_pdf.py` (151 LOC) (P3).

## Credenziali test
- Admin: `hr@funzionabene.it` / `@Bidoc2026!`
