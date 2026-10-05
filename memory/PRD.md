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
- 2026-02-21 — **Fase C audit legale**: rimozione testimonianze fittizie (data/HomePage), rimozione pannello stats fittizi LoginPage, riformulazione claim "end-to-end" (5 occorrenze FE + 1 BE), riformulazione "Prima piattaforma italiana" (7 occorrenze), riformulazione "1 su 8 ammessi", correzione citazione fonte VR (76%/9×) con wording che chiarisce "studi sulla realtà virtuale, non risultati di FunzionaBene", riformulazione "ogni trimestre" → "avvisi automatici 60/30 gg prima scadenza assicurazione" (fatto operativo verificabile). Documento completo in `/app/memory/RIMOZIONI_LEGALI.md`. Testato con screenshot smoke + 5 assertion check su ChiSiamo page.

### In progress
- **Fase D** — Blog slug migration + redirect HTTP 301 su `/blog/<ObjectId>` → `/blog/<slug>` (NEXT).

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
