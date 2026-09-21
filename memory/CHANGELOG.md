# CHANGELOG — funzionabene.it

## 2026-02 — Test E2E in Preview per caioricchieri@gmail.com
- **Script**: `/app/backend/scripts/e2e_caio_test.py` (test end-to-end completo) e `/app/backend/scripts/fire_reminder_now.py` (test manuale reminder).
- **Cosa fa**: crea terapeuta+paziente demo, prenota una sessione 17 min nel futuro, marca come pagato, genera fattura, aspetta 3 min, poi rimborsa e genera Nota di Credito. Tutto invia email a `caioricchieri@gmail.com`.
- **Bugfix scoperto durante il test**:
  - `send_signature_receipt_email` falliva quando `pdf_bytes=b""` con errore Resend "Attachment must have content or path". Fix: allegato omesso quando vuoto (email va comunque).
  - In `_mark_payment_paid` e `create_refund` l'import era `from object_storage` (modulo inesistente) → catturato dal try/except, PDF veniva perso. Fix: `from storage_service import get_object`.
- **Risultato test**:
  - Fattura `FZ-2026-0001` (PDF 2636 bytes) generata + emailed
  - Nota di Credito `NC-2026-0001` (PDF 2668 bytes) generata + emailed
  - Email inviate (Resend API OK): 4 emails a caio (prenotazione confermata, fattura, reminder 15-min, nota di credito)



## 2026-02 — Fix Ulteriore Orario Sessione (Frontend Force Rome TZ) (P0)
- **File nuovo**: `/app/frontend/src/lib/dateFormat.js` (helper `formatItalianDateTime/Time/Date`).
- **File aggiornati**: `TerapistaDashboard.jsx`, `PazienteDashboard.jsx`, `PazienteHome.jsx`, `BookingSheet.jsx`, `PrenotaSubitoModal.jsx`.
- **Root cause residua**: dopo il fix precedente (server → Europe/Rome), il frontend usava ancora `new Date(iso).toLocaleString("it-IT")` che rispetta il **timezone del browser**. Se il terapeuta o il paziente accedeva da un device con TZ non italiana, l'ora appariva sfalsata.
- **Fix**: tutte le formattazioni frontend di `data_ora` ora usano `Intl.DateTimeFormat("it-IT", { timeZone: "Europe/Rome", ... })` — l'ora italiana è **sempre** mostrata, indipendentemente dal fuso del device. Anche i confronti "oggi/domani" nella card "Prossima Sessione" ora usano il fuso Europe/Rome.



## 2026-02 — Fix Critici Post-Test Produzione (P0)
Bug segnalati dopo un test in produzione: (1) email 15min non arrivata, (2) link "Entra" con orario sbagliato, (3) rimborso poco visibile.

### Fix 1 — Reminder 15 min persi ad ogni deploy
- **File**: `/app/backend/booking_service.py`.
- **Root cause**: `AsyncIOScheduler()` usava il jobstore in memoria di default → **ad ogni redeploy tutti i reminder programmati venivano persi**.
- **Fix**: usa `MongoDBJobStore(database=DB_NAME, collection="apscheduler_jobs")`. I lavori pianificati sopravvivono ai restart/deploy.
- Test: dopo restart la collection `apscheduler_jobs` è creata, i job sono persistiti.

### Fix 2 — Orari sbagliati (2h off) nell'email/dashboard terapeuta
- **File**: `/app/backend/email_service.py` (`_format_data_ora_it`), `/app/backend/routers/calendario.py` (dashboard terapeuta + admin calendario).
- **Root cause**: `data_ora` è salvato in UTC (es. `2026-02-15T08:50:00+00:00` per le 09:50 Rome inverno / 10:50 Rome estate) ma il backend renderizzava **le ore UTC direttamente** in email e nel dashboard. Il paziente aveva prenotato le 09:50 e vedeva orari sbagliati.
- **Fix**: tutte le formattazioni server-side ora convertono UTC → `Europe/Rome` prima di mostrare l'ora, gestendo automaticamente ora solare/legale.
- Test: `_format_data_ora_it("2026-02-15T08:50:00+00:00")` → "Domenica 15 febbraio 2026 · **09:50**" (inverno +1). `"2026-08-15T08:50:00+00:00"` → "Sabato 15 agosto 2026 · **10:50**" (estate +2).

### Fix 3 — Pulsante Rimborsa poco visibile + gestione errori 422
- **File**: `/app/frontend/src/pages/admin/PagamentiPage.jsx`.
- **Change**: pulsante "Rimborsa" ora ha sfondo rosso chiaro con bordo (era solo testo con underline). Il tab "In attesa" resta il posto giusto. Uso di `formatApiError` per evitare React #31 su 422.
- **UX Bonus**: il toast di successo ora mostra il numero della Nota di Credito generata (es. "Rimborso eseguito · Nota di Credito NC-2026-0001 generata e inviata al paziente").



## 2026-02 — Feature: Fattura al Pagamento + Nota di Credito (P0 fiscale)
- **File**: `/app/backend/fatturazione.py`, `/app/backend/routers/fatture.py`, `/app/backend/routers/payments.py`, `/app/backend/routers/appuntamenti.py`.

### Change 1 — Fattura sanitaria emessa immediatamente al pagamento
- **Prima**: la fattura veniva emessa quando il terapeuta marcava la sessione come `completato`.
- **Ora**: `_mark_payment_paid()` (chiamato dal webhook `checkout.session.completed`) genera la fattura sanitaria + invia email al paziente **subito dopo il pagamento**. L'appuntamento diventa `confermato` come prima.
- **Fallback preservato**: `update_stato_appuntamento` continua a chiamare `_generate_fattura_paziente` (idempotent) per appuntamenti legacy pagati prima di questa modifica, ma **non invia più l'email** se la fattura esisteva già (evita duplicati).

### Change 2 — Nota di Credito automatica su rimborso
- **Nuovo XML FatturaPA TD04** (`generate_xml_nota_credito_sanitaria`) con `DatiFattureCollegate` che referenzia numero + data della fattura originale (art. 26 DPR 633/72).
- **Numerazione separata**: nuovo contatore `NC-{year}-{NNNN}` in `next_fattura_number`.
- **`_generate_nota_credito_paziente(fattura_id, motivo)`**: emette la NC per l'intero importo della fattura originale, PDF + XML in Object Storage, marca la fattura originale come `stornata: True` con riferimento a `nota_credito_numero`. Idempotent.
- **Integrato in `POST /admin/refunds`**: dopo il rimborso Stripe genera automaticamente la NC e la invia al paziente via email.
- **Endpoint manuale**: `POST /admin/fatture/{fattura_id}/nota-credito` per casi eccezionali.

### Test E2E via script Python:
- Fattura: `FZ-2026-0001` € 80
- NC: `NC-2026-0001` € -80 con `TipoDocumento=TD04` + `<DatiFattureCollegate><IdDocumento>FZ-2026-0001</IdDocumento>...`
- Fattura originale marcata `stornata: True`, `nota_credito_numero: NC-2026-0001`
- Idempotency: chiamate ripetute restituiscono la stessa NC



## 2026-02 — Fix: Pulsanti Email + Banner Detrazione 730 (P1)
- **File**: `/app/backend/email_service.py`, `/app/frontend/src/pages/admin/FatturePage.jsx`.

### Fix 1 — Pulsanti email invisibili (neri) in alcuni client
- **Issue**: I pulsanti CTA nelle email usavano `background:linear-gradient(...)` che **non è supportato da molti client email** (Outlook, Gmail plain, Yahoo, ecc.). Fallback → sfondo trasparente → il pulsante appariva come testo nero senza cornice.
- **Fix**: Sostituito il gradiente con **colore solido `#F58A1F`** (arancione del sito) su:
  - Email attivazione terapeuta ("Attiva il mio profilo →")
  - Email password reset ("Imposta nuova password")
  - Email firma contratto ("Vai alla piattaforma per firmare →")
- Testo nero (`#0A0A0A`) su fondo arancione: alto contrasto e leggibile su tutti i client email.

### Fix 2 — Banner "Detraibile 730" mostrato anche al terapeuta
- **Issue**: Il banner *"Queste fatture sono detraibili al 19%..."* appariva su `/terapeuta/fatture` — ma le fatture del terapeuta sono quelle **da lui emesse**, non ricevute → detrazione non applicabile.
- **Root cause**: la condizione di visibilità era `!isAdmin`, che comprende anche i terapeuti (che condividono lo stesso componente `FatturePage isAdmin={false}`).
- **Fix**: Nuova condizione `user.role === "paziente"` letta da `useAuth()`. Il banner ora appare **solo** sulla pagina fatture del paziente.



## 2026-02 — Feature: Admin Gestisce Documenti Terapeuta (P1)
- **File**: `/app/backend/routers/terapisti.py` (nuovi endpoint admin), `/app/frontend/src/pages/admin/TerapistiPage.jsx`.
- **Backend**:
  - `POST /api/admin/terapisti/{id}/documenti/{tipo}` — admin carica/sostituisce CV, laurea, assicurazione (PDF/PNG/JPG, max 10MB → Emergent Object Storage). Traccia `uploaded_by="admin"` per audit.
  - `DELETE /api/admin/terapisti/{id}/documenti/{tipo}` — admin rimuove il documento.
- **Frontend Admin (Modal "Modifica Terapeuta")**: nuova sezione **"Documenti Terapeuta"** con 3 righe (CV / Laurea / Assicurazione RC). Ogni riga mostra: badge verde/rosso a seconda dello stato, filename+size, pulsante "Carica" o "Sostituisci", download link e trash. Docs caricati dall'admin sono marcati con "caricato da admin" per trasparenza.
- **Test E2E via curl**:
  - POST cv (808B PDF) → 200 · `documenti.cv` popolato con `uploaded_by="admin"`.
  - DELETE cv → 200 `{"tipo":"cv"}`.
- **UI verificata via screenshot**: sezione visibile e usabile dall'admin.



## 2026-02 — Feature: Foto Terapeuta Gestibile da Admin (P1)
- **File**: `/app/backend/routers/terapisti.py` (nuovi endpoint admin), `/app/frontend/src/pages/admin/TerapistiPage.jsx`.
- **Backend**:
  - `POST /api/admin/terapisti/{id}/foto` — admin carica/sostituisce la foto di qualunque terapeuta (JPG/PNG/WEBP, max 5MB → Emergent Object Storage).
  - `DELETE /api/admin/terapisti/{id}/foto` — admin rimuove la foto.
- **Frontend Admin**:
  - Nuova sezione "Foto Profilo" in cima al modal di modifica terapeuta con preview 80×80, pulsante "Carica foto/Cambia foto" e X per rimuovere.
  - Riutilizza `PhotoCropperModal` per il ritaglio 1:1 (output JPEG 512×512).
  - Placeholder rosso "Manca foto" quando assente + hint "senza foto non puoi approvare il terapeuta".
  - Ricarica automaticamente la lista dopo upload/delete.
- **Test E2E via curl**: admin POST foto → 200 + `foto_url`; admin DELETE foto → 200 `{"message":"Foto rimossa"}`. UI verificata via screenshot.



## 2026-02 — Feature: Photo Cropper 1:1 + Foto Obbligatoria per Approvazione (P1)
- **File**: `/app/frontend/src/components/shared/PhotoCropperModal.jsx` (nuovo), `/app/frontend/src/pages/therapist/TerapistaProfile.jsx`, `/app/frontend/src/pages/admin/TerapistiPage.jsx`, `/app/backend/routers/terapisti.py`.
- **Feature 1 — Cropper 1:1**: Nuovo modal (`PhotoCropperModal`) basato su `react-easy-crop` con crop quadrato (aspect=1), maschera circolare, zoom slider, drag-to-pan. All'apertura del file il cropper compare, l'utente centra la foto e conferma. L'output è **JPEG 512×512 quality 0.85** (≈ 40–80KB), uniforme su tutto il sito.
- **Feature 2 — Foto obbligatoria per approvazione**: L'endpoint `PATCH /admin/terapisti/{id}/verifica` ora rifiuta con HTTP 400 quando `foto_url` è vuoto ("Il terapeuta non ha ancora caricato la foto profilo…"). L'admin UI mostra un badge rosso "Manca foto" e disabilita il pulsante di approvazione (con tooltip esplicativo) fino a quando il terapeuta non carica la foto.
- **Dipendenza aggiunta**: `react-easy-crop@6.2.3`.
- **Test E2E via curl**:
  - Approvazione senza foto → HTTP 400 con messaggio in italiano.
  - Approvazione con `foto_url` popolato → HTTP 200 `{"message":"Aggiornato"}`.



## 2026-02 — Feature: Foto Profilo Terapeuta (P1)
- **File**: `/app/backend/routers/terapisti.py` (nuovi endpoint), `/app/backend/server.py` (serve endpoint aggiornato), `/app/frontend/src/pages/therapist/TerapistaProfile.jsx` (UI upload).
- **Feature**: Il terapeuta può ora caricare / cambiare / rimuovere la propria foto profilo direttamente dalla pagina "Il mio Profilo".
- **Backend**:
  - `POST /api/terapisti/me/foto`: upload multipart (JPG/PNG/WEBP, max 5MB). File salvato su **Emergent Object Storage** in `funzionabene/terapisti_photos/{filename}`. Aggiorna `foto_url`, `foto_filename`, `foto_storage_path` sul doc terapeuta.
  - `DELETE /api/terapisti/me/foto`: rimuove i riferimenti alla foto (senza cancellare l'oggetto storage, permette rollback rapido).
  - `GET /api/media/therapists/{filename}`: ora legge da Object Storage con fallback legacy al disk (per foto seed).
  - Prefisso `/api/terapisti/me/` già in `_SIGNATURE_ALLOWLIST_PREFIXES`, quindi upload possibile anche durante l'onboarding.
- **Frontend**: nuova sezione "Foto profilo" in cima ai "Dati Personali" con preview 96×96, pulsante Camera "Carica foto/Cambia foto", icona X per rimuovere. Validazione client-side (formato + 5MB) + messaggio errore leggibile.
- **Test**: E2E via curl — upload 520B JPG → salvato in storage → `foto_url` popolato → `GET /api/media/therapists/{f}` → HTTP 200 image/jpeg. DELETE → `foto_url` diventa null.



## 2026-02 — Bug Fix: Badge "Da Rivedere" Non Spariva Dopo Approvazione (P1)
- **File**: `/app/backend/routers/terapisti.py` (endpoint `PATCH /admin/terapisti/{id}/verifica`), `/app/backend/server.py` (migrazione idempotente in `seed_data`).
- **Issue**: Admin cliccava sul check verde per verificare i documenti del terapeuta ma il badge "Da rivedere" restava per sempre nell'elenco admin.
- **Root cause**: L'endpoint di verifica aggiornava `approval_status="approvato"` solo in `db.users`, non in `db.terapisti`. Il frontend legge da `db.terapisti`, quindi il badge restava a `pronto_per_review`.
- **Fix**:
  1. L'endpoint verifica ora setta `approval_status="approvato"` anche in `db.terapisti`.
  2. Aggiunta migrazione idempotente in `seed_data()`: al boot allinea i terapeuti con `documenti_verificati=True` ma `approval_status != "approvato"` (recupera lo stato in produzione).
- **Test**: curl end-to-end su terapeuta di prova → `PATCH .../verifica {"verificato":true}` → risposta 200, status passa da `pronto_per_review` → `approvato`, `sospeso=False`.



## 2026-02 — UX: Blocco Disponibilità + Messaggio Post-Salvataggio (P1)
- **File**: `/app/frontend/src/pages/therapist/TerapistaProfile.jsx`.
- **Change 1**: Il messaggio "Profilo salvato con successo!" ora, se il terapeuta non è ancora `approvato`, mostra: *"Il tuo profilo è stato salvato con successo. A breve un amministratore verificherà i tuoi dati e documenti. Riceverai un'email di conferma dell'approvazione."* Per terapeuti già approvati resta il messaggio breve.
- **Change 2**: La sezione **"Disponibilità Settimanale"** è nascosta e sostituita da un banner ambrato *"In attesa di approvazione"* finché `approval_status !== "approvato"`. Impedisce al terapeuta di configurare orari prima che l'admin verifichi i documenti.
- **Test**: Smoke test frontend OK (HTTP 200, nessun errore di compilazione).


## 2026-02 — Bug Fix: Green Screen on Save Profile (P0)
- **Files**: `/app/frontend/src/lib/apiError.js` (new), `/app/frontend/src/pages/therapist/TerapistaProfile.jsx`, `/app/frontend/src/pages/patient/PazienteDashboard.jsx`, `/app/frontend/src/components/therapist/MandatoAcceptanceGate.jsx`.
- **Issue**: Nuovi terapeuti che salvavano il profilo con Partita IVA o IBAN non validi vedevano tela verde/bianca invece del messaggio d'errore.
- **Root cause**: FastAPI 422 restituisce `detail` come **array di oggetti Pydantic** (`{type, loc, msg, input, ctx, url}`). Il frontend faceva `setError(err.response.data.detail)` e poi lo renderizzava come figlio JSX → **React error #31** (crash del componente).
- **Fix**: Nuovo helper `formatApiError(err, fallback)` che appiattisce array/oggetti Pydantic in stringhe leggibili nel formato `"campo: messaggio"`. Applicato in 3 componenti critici del flusso di onboarding + save profilo.
- **Test**: Riprodotto 422 via curl con `partita_iva:"12345678900"` (checksum errato) → detail è array → helper restituisce `"partita_iva: Value error, Partita IVA italiana non valida: checksum errato."`. Save con payload valido: OK.


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


## 2026-02-22 — Reinvia Link Attivazione + Blog CMS Migliorato

### Reinvia Link Attivazione
- **Backend**: `POST /api/admin/terapisti/{id}/reinvia-attivazione` — invalida tokens antigos, cria novo token (7 dias), re-envia o email de ativação. Só funciona para status `"in_onboarding"` ou `"pronto_per_review"`. Regista `ultimo_reinvio_attivazione_{at,by}` no doc do terapeuta.
- **Frontend** (`TerapistiPage.jsx`): novo botão "Reinvia link" (com ícone Mail) visível para status `in_onboarding` e `pronto_per_review`; handler com confirm dialog que avisa que os links anteriores serão invalidados.
- Testado E2E via curl: candidatura → attiva → reinvia → verifica novo token → completa com nova senha.

### Blog CMS — Editor Migliorato
- **Backend**:
  - `POST /api/blog/upload-image` — upload de imagem (JPG/PNG/WEBP/GIF, max 5 MB) para Emergent Object Storage em `funzionabene/blog/{uuid}{ext}`. Cria doc em `db.blog_media` com `storage_path`.
  - `GET /api/media/blog/{filename}` — endpoint público que lê o `storage_path` do Mongo e serve o binário do Object Storage com cache 24h.
- **Frontend** (`admin/BlogPage.jsx`):
  - Modal do editor agora **max-w-6xl** com layout **split-view** (source HTML à esquerda, live preview sanitizada à direita, `sanitizeHtml` + `prose` styles).
  - **Toolbar completa**: Bold, Italic, H2, H3, P, lista, link, citação, imagem inline. `wrapSelection` e `insertAtCursor` mantêm o cursor onde o usuário está.
  - Botão **"Immagine di copertina"** com upload dedicado (usa mesmo endpoint) + preview + botão remover.
  - Botão **"Immagine"** na toolbar insere `<figure><img src="{obj-storage-url}" alt="" /></figure>` no cursor após upload.
  - Contador de caratteres em live.
  - Preview modal de artigo publicado agora renderiza HTML sanitizado (antes mostrava plain text com `whitespace-pre-wrap`).
- Testado: upload de imagem 322 bytes → obj storage → URL público → 200 OK; screenshot do editor split-view valida a renderização correta de `<h2>`, `<strong>`, `<em>`, `<ul>` etc.
- 15/15 smoke tests continuam a passar.


## 2026-02-22 — Contatore "Da Rivedere" in Sidebar + Modelli Articoli Blog

### Contatore Da Rivedere (sidebar admin)
- **Backend**: novo endpoint `GET /api/admin/terapisti/count-da-rivedere` que retorna `{count: N}` para terapeutas com `approval_status="pronto_per_review"`.
- **Frontend** (`Sidebar.jsx`): a voce "Terapisti" agora tem `badgeKey: "terapistiPending"`. O poll (a cada 60s) chama os dois endpoints em paralelo (recensioni + terapisti da rivedere). Screenshot confirma o badge vermelho com "1" quando existe um terapeuta em espera de revisão.

### Modelli Articoli Blog (3 templates pre-fatti)
- **Novo file** `/app/frontend/src/data/blogTemplates.js` com 3 templates HTML:
  - **Case Study** — struttura clinica anonima: quadro iniziale → cornice teorica → percorso → momento di svolta → risultati → riflessioni.
  - **Guida Clinica** — di cosa parliamo → come si manifesta → cause (psicologiche/fisiologiche/relazionali) → come si affronta → quando rivolgersi a uno specialista.
  - **Ricerca / Approfondimento** — il fenomeno → cosa dice la ricerca (studi + meta-analisi) → implicazioni cliniche → conclusioni → riferimenti.
- **Frontend** (`admin/BlogPage.jsx`): novo card horizontal "Parti da un modello (opzionale)" com 3 botões (cor gradient laranja/giallo). Só aparece quando `!editing`. Um click pre-preenche titolo, contenuto (~1500-2000 caratteri de HTML pronto) e tags. Confirma antes de sobrescrever se o utilizador já tiver escrito algo.
- Screenshot valida: click em "Guida Clinica" → 1899 caratteres inseridos + preview renderiza `<h2>`, listas, sezioni corretamente.

15/15 smoke tests continuam a passar. Cleanup do terapeuta de teste feito.


## 2026-02-22 — Analizzatore SEO in tempo reale (Yoast-style)
- **Nuovo componente** `/app/frontend/src/components/admin/BlogSeoAnalyzer.jsx` (self-contained, zero backend calls, zero librerie extra):
  - Score 0-100 con cerchio colorato (verde ≥70, amber ≥50, rosso <50).
  - Input "focus keyword" — abilita 4 check aggiuntivi.
  - **10 check totali** che si aggiornano ad ogni keystroke:
    1. Focus keyword nel titolo (peso 15)
    2. Focus keyword nel primo paragrafo (peso 10)
    3. Focus keyword in almeno un H2 (peso 10)
    4. Densità della keyword 0.5-2.5% (peso 15, penalizza troppo bassa e troppo alta = keyword-stuffing)
    5. Lunghezza titolo 30-60 caratteri (peso 10, avviso se troncato oltre 60)
    6. Lunghezza meta description 120-160 (peso 10; usa `excerpt` o primo paragrafo come proxy)
    7. Lunghezza contenuto ≥300 parole (peso 15, ottimo se ≥600)
    8. Struttura headings — almeno 2 H2 (peso 10)
    9. Almeno un'immagine con alt text (peso 10)
    10. Almeno un link nel contenuto (peso 5)
  - Ogni check ha icona (CheckCircle2 / AlertCircle / XCircle) e messaggio in italiano naturale ("Titolo un po' lungo (61). Google può troncarlo dopo 60.").
- **Integrazione** (`admin/BlogPage.jsx`): l'analyzer è nella colonna destra del modal, sopra la live preview. Sempre visibile durante la scrittura.
- Testato: template "Guida Clinica" + keyword "anorgasmia" → score 55 con breakdown corretto di tutti i 10 check.
- Zero impact backend, zero call di rete. 15/15 smoke tests continuam a passar.


## 2026-02-22 — Home narrative rework + hide "Mandato Legale" + endereço BIDOC
- **Homepage**: sostituita la sezione "Professionisti, umani" (che listava 3 terapeuti reali) con una nuova sezione narrativa **"Non 'prendiamo tutti'. Scegliamo, uno per uno."** con:
  - 3 pilastri illustrati da mascotte (`pensativo`, `sereno`, `abbraccio` in tema `light`, animation `breathe`): "Chi sa ascoltare davvero", "Iper-specializzato in sessuologia", "Che ti accoglie come sei".
  - Frase finale d'impatto: *"Solo 1 su 8 dei professionisti che si candidano viene ammesso."*
  - CTA principale al questionario + link secondario "Come scegliamo i professionisti" a `/chi-siamo`.
  - Rimosso lo state `terapisti` + il fetch a `/api/public/terapisti` (non più necessari).
- **Footer** (`PublicLayout.jsx`): rimosso il link "Mandato legale" dalla sezione Legale.
- **Endereço BIDOC** aggiornato da `Via Mazzini, 62` a `P.za I Maggio, 2/interno 2` in:
  - `frontend/src/data/legalInfo.js` (fonte unica per il frontend).
  - Backend Python: `server.py`, `fatturazione.py`, `signature_pdf.py`, `registro_pdf.py`, `invoice_pdf.py`, `email_service.py`, `routers/fatture.py`, `routers/legal_signature.py`.
  - Documenti legali sorgente in `/app/memory/legal/*.md` (7 file: privacy visitatori/pazienti/terapeuti, cookie, termini pazienti, contratto collaborazione, PIANO).
- **Azione richiesta dopo il deploy**: l'admin deve andare in `/admin/contratti` e cliccare "Ripubblica" per ognuno dei 6 documenti legali per rigenerare la versione con il nuovo indirizzo (il seed è idempotente: se esiste già una versione non la sovrascrive).
- 15/15 smoke tests continuano a passar.


## 2026-02-22 — Banner Trasparenza (Coesione Italia 21-27 · UE · Regione FVG) nel footer
- **Nova imagem**: `/app/frontend/public/assets/coesione-italia-fvg.webp` (60 KB, striscia orizzontale con 4 loghi: Coesione Italia 21-27 FVG, Cofinanziato UE, Repubblica Italiana, Regione Autonoma FVG).
- **Frontend** (`PublicLayout.jsx`): banner inserito nel footer tra il link "Scarica l'app" e la linha `border-t` que separa os dados BIDOC.
  - Larghezza: `w-full` em mobile (100% do container com padding), `md:w-2/5` em desktop (40% do container `max-w-7xl`).
  - Link: `<a href="https://www.bidoc.it/trasparenza" target="_blank" rel="noopener noreferrer">` com hover opacity + title tooltip.
  - Alt text descrittivo per accessibilità e SEO.
  - `loading="lazy"` per performance.
- 15/15 smoke tests continuam a passar.


## 2026-02-22 — Bug fix: onboarding therapist não conseguia salvar dados do profilo
- **Root cause**: o middleware `therapist_signature_gate` (server.py:1199) bloqueava todos os POST/PUT/PATCH/DELETE em `/api/*` para terapeutas sem os 4 contracts obrigatórios firmados — mas o allowlist só continha `/api/auth/`, `/api/contracts/`, `/api/legal-documents/`, `/api/upload/`. Isso criava um **catch-22**: para chegar à página de firma dos contracts o terapeuta precisava primeiro preencher o profilo, verificar telefone e assinar DPR 445, mas todos esses endpoints eram bloqueados com HTTP 403.
- **Sintoma reportato pelo usuário**: "vem uma tela verde e não salvo os dados"  — na verdade era o erro 403 `"Devi firmare i documenti obbligatori..."` mas o frontend mascarava mal o feedback visual.
- **Fix**: adicionadas 2 novas entradas ao `_SIGNATURE_ALLOWLIST_PREFIXES`:
  - `/api/terapisti/me/` (documenti upload, telefono verify, DPR 445, onboarding-completato)
  - `/api/terapisti/profilo/me` (save profile data — é o endpoint que estava em uso)
- **Validado E2E**: candidatura → attiva → complete signup → PUT profilo com payload completo → HTTP 200 → dados persistem (bio, albo, prezzo, partita_iva, iban confirmados via GET subsequente).
- 15/15 smoke tests continuam a passar.
- **Ação necessária depois do deploy**: nenhum, o fix é retroativo — qualquer terapeuta preso em onboarding em produção agora conseguirá salvar dados.

