# CHANGELOG — funzionabene.it

## 2026-02 — Bug Fix: Checkout Registration Consent (P0)
- **File**: `/app/frontend/src/components/public/BookingSheet.jsx`
- **Issue**: Nuovi utenti che si registravano dal BookingSheet pubblico ricevevano l'errore backend "I consensi obbligatori (privacy e termini) sono richiesti" anche spuntando il checkbox.
- **Root cause**: Il payload di `POST /api/auth/register` inviava solo `consenso_privacy:true`, senza `consenso_termini:true`. Il backend `auth.py` esige entrambi.
- **Fix**:
  1. `handleRegister` ora invia sia `consenso_privacy:true` sia `consenso_termini:true`.
  2. Label del checkbox aggiornato: include link a Privacy Policy e Termini di Servizio.
  3. Messaggio d'errore locale aggiornato: "Devi accettare Privacy Policy e Termini di Servizio".
- **Test**: Verificato end-to-end via `bug_testing_agent` (iteration_25) — 100% backend + 100% frontend, flusso avanza allo step OTP.

## 2026-02 — Blocco 1: Legal Architecture + Informed Consent
- **File**: `/app/backend/routers/informed_consents.py`, `/app/frontend/src/pages/public/ConsensoInformatoPage.jsx`
- **New feature**: Informed Consent to psychological/sexological treatment via magic-link email.
- Consent is issued PATIENT → THERAPIST (not to Bidoc SRL, which is only marketplace/intermediary).
- Automatic email trigger on first booking with a new therapist.
- One consent per (paziente, terapeuta) pair. New therapist → new consent required.
- Video call access blocked (HTTP 412) if no active consent for that therapist.
- Footer updated: Bidoc SRL = "piattaforma tecnologica di intermediazione", not healthcare provider.
- DPO registered: Caio Silvestre Richieri (SLVCAI76D16Z602F, caio@friulion.it).
- Admin email renamed: admin@ → hr@funzionabene.it (seed handles graceful rename).

## 2026-02 — Blocco 2: Cancellations + Refunds + Reviews
- **Files**: `/app/backend/routers/cancellations.py`, `/app/backend/routers/reviews.py`, `/app/frontend/src/pages/patient/ReviewPage.jsx`
- **Cancellation policy** (configurable via env vars CANCEL_HOURS_FULL/CANCEL_HOURS_PARTIAL/CANCEL_PARTIAL_PCT):
  - ≥24h → 100% refund
  - 12-24h → 50% refund
  - <12h → 0% (no-show)
- **Patient endpoint** `POST /api/appuntamenti/{id}/cancella` with automatic Stripe refund.
- **Reviews with admin moderation**: patient submits → status=pending → admin approve/reject → only approved visible on public profile.
- Auto email invite 30 min after session end to leave a review.

## 2026-02 — Blocco 3: Tech Debt Cleanup
- **Fix lint errors**: 4 apostrofi non-escaped, 1 unused eslint disable directive. Project code: 0 lint errors.
- **New tests**: 17 pytest tests for Blocco 1+2 features (consent, cancellations, reviews).
- **pytest.ini** with markers (smoke/integration/slow).
- **run_smoke_tests.sh**: fast smoke suite (18 tests, ~3s) for CI.
- **.github/workflows/ci.yml**: GitHub Actions for lint + smoke tests.
- **Automated MongoDB backup**: `backup_service.py` + scheduler (daily 03:00 UTC, monthly on day 1, cleanup weekly). Requires B2_KEY_ID/B2_APP_KEY/B2_BUCKET_NAME env vars (Backblaze B2).


## 2026-02-21 — Admin UI: Recensioni Moderation + Component Splits
- **New page**: `/app/frontend/src/pages/admin/RecensioniPage.jsx` — admin can list all pending reviews, approve or reject (with optional motivo), sorted by creation date.
- **Sidebar badge**: `Sidebar.jsx` now polls `/api/admin/reviews/count-pending` every 60s and shows red badge on the "Recensioni" nav item when pending > 0.
- **Route**: `/admin/recensioni` added to `routes.js` under the admin protected group.
- **Refactor `ChatPanel.jsx`** (203 → 108 lines): extracted `chat/ConversationList.jsx` (list) and `chat/MessageThread.jsx` (thread + composer). Pure structural split, same behavior; parent still owns state and polling.
- **Refactor `OnboardingSection.jsx`** (324 → 205 lines): extracted `onboarding/StepHeader.jsx`, `onboarding/DocumentsStep.jsx`, `onboarding/PhoneVerifyStep.jsx`, `onboarding/DprStep.jsx`. Step components are presentational; parent owns state and API calls.
- **Tests**: Smoke tests still pass 15/15. Backend E2E validated via curl (login, list pending, count, approve, unauth 401). Frontend validated via Playwright screenshot flow (badge appears, approve removes row).

## 2026-02-22 — SEO Pilar 3: Full page-level meta tags + Dynamic Sitemap
- **Dynamic sitemap** (backend): new `GET /api/sitemap.xml` in `server.py` returns XML with 20 static public pages + every verified therapist (`/terapeuti/{id}`) + every published blog post (`/blog/{id}`) with proper `lastmod`, `changefreq`, `priority`. Replaces the static frontend `sitemap.xml` (which is kept as fallback).
- **robots.txt**: updated to reference both `/api/sitemap.xml` (primary, dynamic) and `/sitemap.xml` (fallback, static). Added explicit `Allow: /api/sitemap.xml` despite the general `Disallow: /api/`.
- **`<SEO>` component** applied to every public page:
  - **HomePage** — MedicalBusiness JSON-LD (name, priceRange €49-€90, medicalSpecialty Psychology/Sexology, availableLanguage it/en).
  - **BlogPostPage** — Article JSON-LD (headline, image, datePublished, dateModified, author, publisher, mainEntityOfPage) — fully dynamic per post.
  - **TerapistaPublicPage** — Person JSON-LD (name, jobTitle, image, worksFor, knowsLanguage, hasCredential albo) — fully dynamic per therapist.
  - **FAQPage** — FAQPage JSON-LD (dynamic from `/api/public/faq` + fallback).
  - **AreeInterventoPage, ChiSiamoPage, ContattiPage, SeduteImmersive, IlNostroMondoPage, BlogPublicPage, QuestionnairePage** — unique `<title>`, `<meta description>`, `<link canonical>`, Open Graph + Twitter Card tags.
- **Tests**: E2E Playwright verified: every page has unique title + description; dynamic pages emit correct JSON-LD schema; 15/15 backend smoke tests pass. Dynamic sitemap validated via `curl` (returns 20 static + 1 therapist).
- **Files touched**:
  - `/app/backend/server.py` — `@api_router.get("/sitemap.xml")` (~60 LOC).
  - `/app/frontend/public/robots.txt` — sitemap references.
  - `/app/frontend/src/pages/public/HomePage.jsx`, `AreeInterventoPage.jsx`, `BlogPublicPage.jsx`, `BlogPostPage.jsx`, `TerapistaPublicPage.jsx`, `ChiSiamoPage.jsx`, `FAQPage.jsx`, `ContattiPage.jsx`, `SeduteImmersive.jsx`, `IlNostroMondoPage.jsx`, `QuestionnairePage.jsx` — added `<SEO>` wrappers.
- **Fix (`sw.js`)**: `clients.openWindow(url)` → `self.clients.openWindow(url)` to satisfy `no-undef`.


## 2026-02-22 — Emergent Object Storage migration (deploy blocker fix)
- **New**: `/app/backend/storage_service.py` — thin wrapper around Emergent Object Storage (`INTEGRATION_PROXY_URL` + `EMERGENT_LLM_KEY`). Session-scoped `storage_key` initialized once at FastAPI startup, then reused globally.
- **Therapist verification documents** (CV/Assicurazione/Laurea):
  - `POST /api/terapisti/me/documenti/{tipo}` now uploads to `funzionabene/terapisti_docs/{user_id}/{tipo}-{uuid}{ext}` in Object Storage and persists `storage_path` in Mongo (`documenti.{tipo}.storage_path`).
  - `GET /api/admin/terapisti/{id}/documenti/{tipo}/download` reads from Object Storage with legacy on-disk fallback for pre-migration files.
- **Ambassador photos** (public landing "Sessualità e Disabilità"):
  - `POST /api/admin/ambassadors/{id}/foto` now uploads to `funzionabene/ambassadors/{amb_id}-{uuid}{ext}` and stores `foto_storage_path` in Mongo.
  - `GET /api/media/ambassadors/{filename}` reads from Object Storage with legacy on-disk fallback.
  - E2E validated: upload 322-byte JPG → 200 OK on public URL → identical bytes retrieved.
- **Google Search Console verification** — added `<meta name="google-site-verification" content="%REACT_APP_GSC_VERIFICATION%">` in `public/index.html`. Value driven by `REACT_APP_GSC_VERIFICATION` env var (currently empty; user fills it in when claiming the domain in GSC).
- **Deploy blocker resolved**: the `ephemeral-upload-storage` lint rule no longer fires — all user uploads now survive pod restarts. Legacy on-disk fallback preserved for the (empty in prod) demo assets.
- **Tests**: 15/15 backend smoke tests pass; E2E flow validated via curl (admin login → create ambassador → upload photo → fetch public URL → delete). SEO pages still render correctly (verified via Playwright).


## 2026-02-22 — Fluxo "Attiva Candidato" ponta-a-ponta (P1 feito)
- **Estados novos** em `approval_status` para terapeutas:
  - `"lead"` — candidatura recebida via `/candidatura-terapeuta` (sem conta user).
  - `"in_onboarding"` — admin ativou o candidato, user criado suspenso, aguarda onboarding.
  - `"pronto_per_review"` — terapeuta finalizou docs + telefone + assinatura DPR 445, admin precisa rever.
  - `"approvato"` — admin aprovou docs, terapeuta público e pode receber pacientes.
- **Backend** (`/app/backend/routers/terapisti.py` + `auth.py`):
  - `POST /api/admin/terapisti/candidato/{lead_id}/attiva` — Admin ativa lead. Cria user `terapeuta` com `is_active=false`, gera token (7 dias) em `password_reset_tokens` (purpose=`therapist_activation`), envia email de ativação (`send_therapist_activation_email`).
  - `POST /api/terapisti/me/onboarding-completato` — Chamado após assinar DPR 445; guard-checka docs+telefone+firma, muda status para `"pronto_per_review"` e envia email ao admin (`send_therapist_ready_for_review_email` → `ADMIN_REVIEW_EMAIL`, default `hr@funzionabene.it`).
  - `GET /api/auth/attivazione-terapeuta/verifica?token=...` — Endpoint público que valida o token e retorna nome/email/cognome do candidato.
  - `POST /api/auth/attivazione-terapeuta/completa` — Consome token, define password, `is_active=true`, auto-login (seta cookies e retorna user).
  - `PATCH /api/admin/terapisti/{id}/verifica` — Adicionado: quando o admin marca `verificato=true` a suspensão é levantada (`sospeso=false`, `user.is_active=true`) e o welcome email é enviado.
- **Frontend**:
  - `/app/frontend/src/pages/AttivaAccountPage.jsx` (novo) — Página `/attiva-account?token=...` com validação de token, formulário de senha, força visual, auto-login e redirect para `/terapeuta`.
  - `/app/frontend/src/routes.js` — Route pública `/attiva-account`.
  - `/app/frontend/src/pages/admin/TerapistiPage.jsx` — Botão "Attiva" (só visível quando `approval_status="lead"`), badges novos `IN ONBOARDING` e `DA RIVEDERE` (pulsante amarelo), handler `handleAttivaCandidato`.
  - `/app/frontend/src/components/therapist/OnboardingSection.jsx` — Após `POST /autocertificazione-dpr445` chama automaticamente `/onboarding-completato` para disparar o email ao admin.
  - `robots.txt` — `Disallow: /attiva-account` (fluxo privado).
- **Emails novos** (`email_service.py`):
  - `send_therapist_activation_email(email, activation_url, nome)` — CTA laranja "Attiva il mio profilo", lista dos passos de onboarding, aviso 7 dias.
  - `send_therapist_ready_for_review_email(admin_email, nome, terapista_email, terapista_id)` — Notifica admin para rever o candidato.
- **Login gate** (`auth.py`): terapeutas com `approval_status ∈ {"approvato","verified","in_onboarding","pronto_per_review"}` conseguem logar; `"lead"`/`"pending"` continuam bloqueados.
- **Testes**: E2E via curl validado — candidatura pública → admin activa → link magic verify → completa activation → login com nova senha. 15/15 smoke tests continuam a passar. Frontend validado com Playwright (badges, botão Attiva, página `/attiva-account` estados válido/inválido).


## 2026-02-22 — Blog seed automático (bug fix produção)
- **Root cause**: em produção `/blog` e `/admin/blog` estavam vazios porque os 15 artigos "sessuologia-html-v1" existiam apenas na base de dados de preview e não havia mecanismo de seed automático.
- **Fix**: exportei os 15 artigos existentes para `/app/backend/data/blog_seed.json` (27 KB) e adicionei `_seed_blog_articles()` como função idempotente no startup do FastAPI.
  - Só semeia se `seed_source="sessuologia-html-v1"` não existir (admin pode apagar/editar sem re-seed).
  - Parseia datas ISO → datetime, força `stato="pubblicato"` como default.
  - Testado: 2 restarts consecutivos → continua 15 artigos (sem duplicação).
- **Bug secundário fixado**: o endpoint `GET /api/sitemap.xml` filtrava blog posts por `pubblicato=True` (campo inexistente); o campo correto é `stato="pubblicato"`. Agora o sitemap inclui 15 blog posts + 1 terapeuta verificado.
- 15/15 smoke tests continuam a passar.

