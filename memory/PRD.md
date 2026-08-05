# FunzionaBene.it — PRD

## Descrizione Progetto
Piattaforma integrata per clinica di sessuologia: gestionale admin + sito pubblico con prenotazione sessioni online. Mercato italiano, tutto in lingua italiana.

**Sito:** funzionabene.it  
**Focus:** Sessuologia / salute sessuale  
**Data inizio:** Aprile 2026

---

## Architettura Tecnica
- **Backend:** Python FastAPI + MongoDB (motor async)
- **Frontend:** React 19 + Tailwind CSS + shadcn/ui + Phosphor Icons
- **Auth:** JWT (httpOnly cookies) + OTP email
- **Email (placeholder):** Resend (transazionale) + Brevo (marketing)
- **Pagamenti (Fase 2):** Nexi XPay
- **Video (Fase 2):** Daily.co
- **Design (Feb 2026):** Sfondo mustarda **#E9D628** (corpo), **#D4C123** (header & footer leggermente più scuri). Cards bianche pure. Testo nero **#0A0A0A**. **Bottoni primari**: gradiente arancione→giallo (`from-[#F58A1F] to-[#F5D419]`), testo nero bold, `rounded-2xl`, soft shadow. Bottoni secondari: outline nero 1.5px. **Mascotte filled**: paleta harmonica completa — `abbraccio` arancione #F58A1F, `sereno` bianco, `embrulhado` pesca #F5C0A8, `peludo` sage verde #C8E0A8, `ovo` azzurro polvere #B8D5E0, `coppia` corallo #E89B9F, `saltitante` terracotta #D4906E, `pensativo` lavanda #C8B5E0, `curioso` azzurro cielo #8FC8D8. Tutti con contorni neri eleganti. Sidebar gestionale rimasta scura con accenti mustarda.
- **Font:** Outfit (titoli) + Figtree (body)
- **CHANGELOG Feb 2026:** Pivot estetico completo: mustarda/gradiente arancione/mascotte colorati su tutto il sito (pubblico + autenticato).

---

## Utenti (Ruoli)
| Ruolo | Accesso |
|---|---|
| **admin** | Dashboard admin completa, gestione tutto |
| **terapeuta** | Proprio profilo, pazienti assegnati, sessioni |
| **paziente** | Proprio profilo, sessioni prenotate |

---

## ✅ FASE 1 — COMPLETATA (Aprile 2026)

### Autenticazione
- [x] Login multi-ruolo (admin/terapeuta/paziente)
- [x] Registrazione con OTP email (dev mode: codice in response)
- [x] Verifica OTP con scadenza 10 minuti
- [x] JWT con refresh token (httpOnly cookies)
- [x] Seed automatico: admin + demo terapeuta + demo paziente
- [x] Logout
- [x] Protezione rotte per ruolo

### Gestione Terapisti
- [x] CRUD completo profili terapisti
- [x] Dati Albo italiano (numero, ordine, data iscrizione)
- [x] Assicurazione professionale (compagnia, polizza, scadenza)
- [x] Alert scadenza assicurazione (30/60 giorni)
- [x] Autocertificazione elettronica (firma + timestamp + IP)
- [x] Specializzazioni, lingue, bio, anni esperienza
- [x] Disponibilità settimanale (giorno + orari)
- [x] Prezzo sessione

### Gestione Pazienti
- [x] CRUD completo pazienti
- [x] Anagrafe completa (nome, CF, nascita, genere, contatti)
- [x] Validazione Codice Fiscale (algoritmo italiano backend + frontend)
- [x] Note cliniche riservate
- [x] Assegnazione terapeuta
- [x] Consenso GDPR

### Appuntamenti
- [x] CRUD appuntamenti
- [x] Stati: prenotato → confermato → completato / cancellato
- [x] Supporto online/in presenza
- [x] Vista per ruolo (admin vede tutto, terapeuta i propri, paziente i propri)

### Dashboard Admin
- [x] Stats: terapisti, pazienti, sessioni oggi/totali
- [x] Alert terapisti in attesa approvazione
- [x] Alert articoli blog in revisione
- [x] Alert terapisti senza autocertificazione
- [x] Alert scadenze assicurazione imminenti
- [x] Azioni rapide

### Dashboard Terapista
- [x] Panoramica sessioni (oggi/prossime/totali)
- [x] Checklist completamento profilo
- [x] Alert autocertificazione mancante
- [x] Lista prossime sessioni

### Dashboard Paziente
- [x] Panoramica sessioni (prenotate/completate/totali)
- [x] Gestione profilo personale
- [x] Lista prossime sessioni

### Blog
- [x] API completa (CRUD + approva/rifiuta)
- [x] UI Admin: lista articoli, filtri (Tutti/In Revisione/Pubblicati/Rifiutati), approva, rifiuta, anteprima, elimina, crea articolo
- [x] UI Terapista: scrivere articoli, invio per approvazione, stato bozza/pubblicato/rifiutato
- [x] Banner informativo flusso approvazione

### Sistema Slot Disponibilità
- [x] API slot: `GET /api/terapisti/{id}/slots?settimane=N`
- [x] Generazione slot da disponibilità settimanale (50 min cadauno)
- [x] Controllo conflitti con appuntamenti esistenti
- [x] Formato date in italiano (es. "Lunedì 21/04/2026 09:00")
- [x] Pronto per il sito pubblico (Fase 3)

---

## ✅ FASE 2 — SITO PUBBLICO COMPLETATA (Febbraio 2026)

### Layout pubblico (PublicLayout)
- [x] Header sticky con navigation (Home / Questionario / Blog / FAQ) + CTA gold
- [x] Mobile menu responsive
- [x] Footer con sezioni legali (Privacy, Cookie, GDPR)
- [x] Tema dark/warm premium (Gold #D4A017 + Steel Blue #6B8FA3)
- [x] Tipografia Cormorant Garamond (serif) + Outfit (sans)

### Homepage (/)
- [x] Hero con background texture + CTA "Inizia il Questionario"
- [x] Trust signals (SSL/GDPR, Albo, 98% soddisfazione)
- [x] Sezione "Come funziona" (3 step)
- [x] Sezione Valori (Riservatezza, Specialisti verificati, Nessun giudizio)
- [x] Therapists preview grid (caricato da /api/public/terapisti)
- [x] CTA band finale

### Questionario (/questionario)
- [x] 5 step (età, genere, problemi multi, orari multi, preferenza terapeuta)
- [x] Progress bar animata, auto-advance per single-select
- [x] Animazioni framer-motion tra step
- [x] POST /api/public/matching con scoring → salva in sessionStorage

### Risultati Matching (/risultati)
- [x] Top 3 terapeuti con badge compatibilità %
- [x] Card premium con foto placeholder, specializzazioni, tariffa, link al profilo

### Profilo pubblico terapeuta (/terapeuti/:id)
- [x] Layout 2 colonne: sidebar (Albo, esperienza, lingue, prezzo) + bio/formazione
- [x] Calendario slot 14 giorni (da /api/terapisti/{id}/slots, Italian days)
- [x] Click slot → apre BookingSheet

### BookingSheet (flusso prenotazione)
- [x] Step 1 Review (riepilogo slot + prezzo)
- [x] Step 2 Auth tabs (Registrati / Accedi)
- [x] Step 3 OTP verification (con otp_dev mostrato in modalità dev)
- [x] Step 4 Pagamento MOCKATO (UI carta di credito)
- [x] Step 5 Success + redirect area paziente
- [x] Skip auth steps se utente già loggato come paziente

### Blog pubblico (/blog + /blog/:id)
- [x] Layout editoriale (hero article + grid)
- [x] Post singolo con reading column, autore, CTA questionario

### FAQ (/faq)
- [x] Accordion animato
- [x] 7 FAQ di fallback se DB vuoto
- [x] Integrazione con /api/public/faq

### Backend public endpoints (no auth)
- [x] GET /api/public/terapisti (solo autocertificati)
- [x] GET /api/public/terapisti/{id}
- [x] POST /api/public/matching (scoring: genere×30 + specializzazioni×20 + disponibilità×10-15 → normalizzato a 70-99%)
- [x] GET /api/public/blog (solo pubblicati)
- [x] GET /api/public/faq
- [x] POST /api/public/prenota (richiede auth paziente)
- [x] GET /api/terapisti/{id}/slots (public, con Italian day names)

**Test status:** 15/15 backend tests passed, 100% frontend flows validated (iteration_3.json)

---

## 🔄 FASE 3 — INTEGRAZIONI REALI (NEXT)

### Fase 2 — Sito Pubblico Premium ✅ COMPLETATA (19/04/2026)

**Homepage redesign completa:**
- [x] Hero: "Parla di tutto. Anche di quello." con badge "Prima clinica italiana di sessuologia immersiva"
- [x] Sezione Sedute immersive (mai uso delle sigle VR/AR — sempre "immersiva")
- [x] Aree di intervento: 12 cards in homepage + pagina dedicata con 20 temi in 9 categorie
- [x] Perché FunzionaBene: 5 cards differenzianti (Iper-specialisti, Sedute immersive, Parla senza filtri, Riservatezza, Verificati)
- [x] Testimonianze: 6 anonimizzate con disclaimer GDPR
- [x] A cosa serve / Non serve (stile Serenis, onestà radicale)
- [x] CTA band finale

**Nuove pagine:**
- [x] `/sedute-immersive` — landing dedicata con stats, step-by-step, use cases, FAQ e riferimenti scientifici (Riva, Freeman, Diemer, Wiederhold, Optale)
- [x] `/aree-intervento` — tutte le 20 aree organizzate in 9 categorie colorate
- [x] `/emergenze` — 8 numeri d'emergenza con warning (112, TP, 1522, Gay Help Line, Samaritans 800.861.061, 114, 1500, 800.915.150)
- [x] `/chi-siamo` — storia, missione, valori, team philosophy, "perché solo sessuologia"

**Terapisti arricchiti:**
- [x] 4 terapisti demo aggiuntivi con diversità reale:
  - Alessandro Conti (M, 55y, 28 anni esperienza, ansia prestazione/disfunzione erettile, €79)
  - Giulia Marchetti (F, 38y, 9 anni, anorgasmia/vaginismo/mindfulness, €65)
  - Marco Fontana (M, 32y, 5 anni, LGBTQIA+/identità/poliamore, €55)
  - Chiara Esposito (F, 45y, 18 anni, traumi/EMDR/menopausa, €85)
- [x] Foto profissionali generate via OpenAI gpt-image-1 (Emergent LLM key)
- [x] Endpoint `/api/media/therapists/{filename}` per servire immagini
- [x] Foto integrate in: HomePage preview, MatchingResultsPage card, TerapistaPublicPage hero

**Navigation aggiornata:**
- Home · Immersive · Aree · **Chi siamo** · Blog · FAQ
- Footer con "Numeri d'emergenza" in rosso allerta
- [x] **Cabeçalho aggiornato**: rimosso subtitle "clinica psicologica", font del logo aumentato (text-3xl sm:text-4xl)
- [x] **FAQ prezzi corretti**: da 70-120€ a **49-90€** per seduta
- [x] **Pagine legali** complete in italiano conforme GDPR:
  - `/privacy` — Privacy Policy (trattamento dati sanitari, categoria speciale art.9, diritti art.15-22)
  - `/cookie` — Cookie Policy con toggle interattivi per salvare preferenze
  - `/termini` — Termini e Condizioni (con policy disdette 24h, diritto recesso, responsabilità)
- [x] **Cookie Consent Banner** GDPR-compliant:
  - Appare alla prima visita (localStorage `fb_cookie_consent`)
  - 3 opzioni: "Personalizza" (toggle granulari) / "Solo essenziali" / "Accetta tutti"
  - Solo cookie essenziali funzionano di default finché l'utente non acconsente
  - Utility `cookieConsent.js` per leggere/scrivere preferenze
- [x] Footer aggiornato con link alle 3 pagine legali

### Miglioramenti UX/Funzionali ✅ COMPLETATI (19/04/2026)
- [x] **Logo personalizzata** (cuore gold+steel blue su nero) sostituisce il placeholder in tutto il sito
- [x] **Codice Fiscale auto-calcolato** via backend `/api/utils/compute-cf` (python-codicefiscale)
  - Supporta sia nati in Italia (comune) sia all'estero (paese ISO)
  - Campo UI con indicatore "Calcolato automaticamente" (Sparkles icon)
  - User può editare manualmente se il calcolo non è corretto
- [x] **Chat privata paziente↔terapista** completa con `ChatPanel.jsx`
  - Lista conversazioni a sinistra, messaggi a destra
  - Polling 5s per nuovi messaggi
  - Badge "non letti" per conversazioni con messaggi nuovi
  - Disponibile nel PazienteDashboard e TerapistaDashboard
  - Attiva automaticamente dopo prima prenotazione (stato="confermato")
- [x] **Email automatici post-booking**
  - Email conferma prenotazione (paziente + terapista) — template premium dark+gold
  - Reminder 1 giorno prima (APScheduler)
  - Reminder 1 ora prima (APScheduler)
  - Template Italiano con data formattata ("Lunedì 20 aprile 2026 · 09:00")
- [x] Stato appuntamento cambiato da `prenotato` → `confermato` on booking (attiva subito la chat)

### Dati Fiscali Paziente ✅ COMPLETATA (19/04/2026)
- [x] Dataset italiano hardcoded (110 province + ~175 paesi esteri ISO)
- [x] Form "Completa i tuoi dati" con: anagrafe, luogo nascita (Italia/estero toggle), CF (validazione checksum backend), telefono, indirizzo residenza (via/città/CAP/provincia)
- [x] Step "dati-fiscali" nel BookingSheet **PRIMA** del pagamento
- [x] Backend computa automaticamente flag `dati_fiscali_completi` su update
- [x] Skip dello step se paziente già ha tutti i dati
- [x] Step success senza pulsante dashboard (solo "Chiudi")

### Integrazione Daily.co ✅ COMPLETATA (19/04/2026)
- [x] `daily_service.py` backend (create room + meeting token + presenze)
- [x] Auto-creazione stanza privata al momento della prenotazione
- [x] Endpoint `/api/appuntamenti/{id}/video-token` (token con nbf/exp scoped)
- [x] Endpoint `/api/appuntamenti/{id}/presenze` (logs Daily per prova presenza)
- [x] Frontend `VideoCallPage` fullscreen con iframe Daily (tema premium dark+gold)
- [x] Pulsante "Entra" in PazienteDashboard + TerapistaDashboard (visibile 15 min prima → 15 min dopo)
- [x] Ownership: terapista = is_owner=true (può gestire partecipanti), paziente = guest

### Integrazione Nexi XPay
- [ ] Checkout sessioni online
- [ ] Gestione rimborsi
- [ ] Storico pagamenti

### Integrazione Skebby SMS OTP + Document Upload ✅ COMPLETATA (19/04/2026)
- [x] `sms_service.py` con Skebby REST API (login session + token alphanumeric sender)
- [x] POST `/api/sms/send-otp` (stored in `db.sms_otp`, fallback `otp_dev` se Skebby fallisce)
- [x] POST `/api/sms/verify-otp` → setta `telefono`, `telefono_verificato`, `telefono_verificato_at` sull'utente
- [x] **Paziente flow**: SMS OTP step aggiunto nel BookingSheet tra "payment" e "success", con checkbox privacy art. 9 GDPR
- [x] `/api/public/prenota` richiede `telefono_verificato_at` entro 60 min
- [x] **Terapeuta flow**: `OnboardingSection.jsx` con 3 step (upload CV/Assicurazione/Laurea → SMS OTP → autocertificazione DPR 445/2000)
- [x] POST `/api/terapisti/me/documenti/{tipo}` multipart, tipi: cv/assicurazione/laurea, max 10MB, estensioni PDF/PNG/JPG
- [x] POST `/api/terapisti/me/autocertificazione-dpr445` richiede tutti docs + telefono verificato
- [x] **Admin vetting**: GET `/api/admin/terapisti/{id}/documenti` + `/download`, PATCH `/verifica` toggla `documenti_verificati`
- [x] Filtro public (`/public/terapisti`, matching) ora usa `documenti_verificati=true` come gate di visibilità pubblica
- [x] Admin TerapistiPage: badge Pubblico/Non pubblico, toggle verifica, pannello documenti espandibile con download
- [x] **Testing iteration_5.json: 23/23 backend + 9/9 frontend PASS**
- [ ] **NOTA**: Skebby credenziali attuali restituiscono 404 — utente deve verificare API credentials in dashboard Skebby (potrebbero differire dalle credenziali di login web)

### Integrazione Daily.co ✅ COMPLETATA
- [x] Generazione link videochiamate
- [x] Log sessioni (prova avvenimento)
- [x] Tracking durata

### Email Automatiche (Resend)
- [ ] OTP email reali
- [ ] Conferma prenotazione
- [ ] Reminder 1 giorno prima (con link video)
- [ ] Reminder 1 ora prima
- [ ] Sistema recupero pazienti (Brevo)

### Chat privata paziente ↔ terapeuta
- [x] API /api/conversazioni + /api/messaggi già presenti
- [ ] UI chat nelle dashboard (paziente + terapeuta)
- [ ] Real-time (WebSocket o polling)

---

## 🔧 REFACTORING BACKLOG
- [ ] Split server.py (1043 linee) in router modulari: auth.py, public.py, terapisti.py, pazienti.py, appuntamenti.py, blog.py, faq.py, messaggi.py
- [ ] Aggiungere endpoint dedicato GET /api/public/blog/{id} (attualmente BlogPostPage filtra client-side)
- [ ] Test files pytest in /app/backend/tests

---

## Credenziali Test
Vedi: /app/memory/test_credentials.md

## Note GDPR
- Dati sanitari = categoria speciale (art. 9 GDPR)
- Consenso esplicito al momento della registrazione
- Diritto all'oblio implementabile
- Server idealmente in Europa (Hetzner/DigitalOcean Frankfurt)

---

## 🆕 CHANGELOG — Feb 17, 2026
- [x] Mascotte component: aggiunta prop `maxHeight` (constrain altezza + object-contain) per evitare distorsioni con mascotte di proporzioni verticali (es. `embrulhado`).
- [x] HomePage "Come funziona" → Step 01 ora usa `size=80 maxHeight=80` uniforme con gli altri 2 step. Layout dei 3 card finalmente allineato.
- [x] AppSection ("La tua app") → fix chips fluttuanti: rimosso `brand-card` (che li rendeva alti 415px), sostituito con pill bianche compatte (162-195 × 50px) con `whitespace-nowrap` e `inline-flex`. Ora si vedono come piccoli toast galleggianti intorno al telefono.
- [x] Confermato in preview: testi Step 01/02/03 + link discreto "Hai bisogno di parlare subito? → Prenota uno specialista disponibile ora" — già implementati dalla sessione precedente.
- [x] **Mascote VR colorida** (Feb 17, 2026): gerada via Nano Banana (Gemini image editing) variante `vr-brand.png`. Corpo `#C79C50` (laranja-dourado do logo), óculos VR `#78949E` (cinza-azul do logo). Cleanup pós-geração com PIL para remover checkerboard fake e ter transparência real. Aplicada à seção "Il nostro differenziale" da HomePage.

---

## 🛡️ FASE A — Code Quality (Feb 18, 2026)
- [x] **Cookie consent security**: migrado `cookieConsent.js` de `localStorage` para cookie real com `Secure`, `SameSite=Strict`, `Path=/`, `Max-Age=180d`. Removidos `console.warn` (3 ocorrências).
- [x] **Nested ternaries refactor** (Code Smell):
  - `BlogPage.jsx`: extraído `STATO_LABEL` map + `getSaveButtonLabel()` helper
  - `TerapistiPage.jsx`: extraído `getInsuranceExpiryColor()` + `getSaveButtonLabel()` helpers + `THIRTY_DAYS_MS` const
- [x] Validado via screenshot + cookie inspection (secure=true, sameSite=Strict, localStorage vazio).

### Falsos positivos do code review (não aplicados)
- **`is None` em Python**: as 15 ocorrências sinalizadas são uso CORRETO conforme PEP 8 (`is`/`is not` deve ser usado com singletons como `None`). Não alteradas.
- **Hooks "missing deps"** em `AuthContext.jsx` e `ChatPanel.jsx`: as deps sinalizadas (`API`, `axios`, `data`, `setUser`, `res`) são module-level imports/constants ou setters do `useState` (estáveis). Não precisam estar no array.

---

## 🔐 GDPR — Audit Consent Log (Feb 18, 2026)
- [x] **Backend**: collection `audit_consents` + endpoint `POST /api/audit/consent` (público, write-once) e `GET /api/admin/audit/consents` (admin, paginado, max 200).
- [x] **Dados gravados**: `policy_version`, `policy_hash` (SHA-256 de version+prefs), `prefs` (essential/analytics/marketing), `ip_anonymized` (último octeto IPv4 zerado / IPv6 truncado em /48), `user_agent` (300 chars), `language`, `page_url`, `created_at` (UTC).
- [x] **Imutabilidade**: nenhum endpoint de PATCH/DELETE exposto.
- [x] **Frontend**: `setCookiePreferences()` dispara fire-and-forget POST com `keepalive: true` após persistir cookie. Não bloqueia UX. Falha silenciosa para não afetar o consentimento.
- [x] **Verificado**: smoke test admin lista entry com IP anonimizado (`203.0.113.42` → `203.0.113.0`) + e2e do banner real fez POST automaticamente.

---

## 📋 Dati legali aziendali (Feb 18, 2026)
- [x] Creato `/app/frontend/src/data/legalInfo.js` come fonte centralizzata (TITOLARE, DPO, WHATSAPP, emails).
- [x] **Titolare**: BIDOC SRL — Via Mazzini, 62 · Spilimbergo (PN) · P.IVA 01985930930. "Funzionabene" è marchio registrato di BIDOC SRL.
- [x] **DPO**: Caio Silvestre Richieri — Via Circonvallazione Sud, 80 · Codroipo (UD) · C.F. SLVCAI76D16Z602F · P.IVA 03157410303 · privacy@funzionabene.it.
- [x] **Phone = WhatsApp**: +39 345 112 4503 (già correctly set, ora centralizzato).
- [x] Aggiornati: `ContattiPage.jsx` (Sede + nuova sezione DPO), `PublicLayout.jsx` (Footer), `PrivacyPage.jsx` (Sezione 1 Titolare + nuova Sezione 2 DPO, sezioni 3-10 rinumerate).

---

## 💳 STRIPE PAYMENTS INTEGRATION (Feb 18, 2026)

### Architecture
- **Flow A** (Claimable sandbox) — sandbox provisionato via `POST /stripe/sandboxes`.
- Chiavi in `backend/.env`: `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_ACCOUNT_ID`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_MODE=test`.
- **Onboarding URL** (per claim + KYC produzione):
  https://dashboard.stripe.com/onboard_sandbox/YWNjdF8xVTBMdFZBZnZaYU55bWpMLDE3ODYzNzM3OTIv100sh4g4waP

### Modello di business
- **70% terapeuta, 30% BIDOC SRL** (`PLATFORM_FEE_PERCENT=30`).
- **Split registrato in DB** (`payment_transactions.therapist_amount` + `platform_fee_amount`). Payouts al terapeuta sono **manuali** per ora (BIDOC fa bonifico mensile + segna `payout_status="paid"`). Migrazione a Stripe Connect Express è possibile senza breaking changes.
- **Prezzo per terapeuta** (`prezzo_sessione` in `terapisti`). Nessun price catalog Stripe — usa `price_data` inline per checkout dinamico.
- **Tax mode: DIY**. Razionale: la psicoterapia in IT è **esente IVA** ex art. 10 DPR 633/72 comma 1 n. 18. Il terapeuta emette fattura sanitaria separatamente (Sistema TS). Stripe processa solo il pagamento — non calcola tasse.

### Endpoints
- `POST /api/payments/checkout/booking` (auth: paziente) — crea appuntamento PENDING + Stripe Checkout Session + payment_transaction. Ritorna `checkout_url`.
- `GET /api/payments/status/{session_id}` (public) — polling status; fallback a Stripe API se webhook ritarda.
- `POST /api/stripe/webhook` (public, sig-verified) — gestisce `checkout.session.completed/expired/failed`, `charge.refunded`.
- `GET /api/therapist/earnings` (auth: terapeuta) — riepilogo incassi (paid_out, pending_payout, sessions_count, platform_fee_total).

### Frontend
- `BookingSheet.jsx` — flusso: review → auth → OTP → dati fiscali → **verifica SMS** → **Stripe Checkout redirect**.
- `PaymentSuccessPage.jsx` (`/payment/success`) — polling `/api/payments/status/{session_id}` fino a paid.
- `PaymentCancelPage.jsx` (`/payment/cancel`) — messaggio calmo + CTA torna-home.

### Business logic
- Appuntamento passa `in_attesa_pagamento` → `confermato` **solo dopo payment_status=paid**.
- Daily.co room + email di conferma create **solo dopo pagamento riuscito**.
- `_mark_payment_paid()` idempotente — chiamata sia da webhook che da polling è safe.

### Test verificati (curl + Python)
- ✅ Sandbox provisionato (sk_test_51U0LtV...).
- ✅ Checkout URL generato per €90 (con URL Stripe reale).
- ✅ Split 30/70 salvato correttamente (€27 / €63).
- ✅ Simulazione paid → appuntamento confermato + email + idempotency.
- ✅ `/therapist/earnings` ritorna €63 pending per la terapista Maria.
- ✅ `/payment/cancel` UI renderizza con mascote `sereno`.

### NOTE PER PRODUZIONE
- L'utente deve completare **KYC** (Know Your Customer) su Stripe usando l'onboarding URL sopra.
- Il **preview webhook** funziona in preview; alla deploy in produzione servirà il **webhook production** (Emergent lo auto-inietta al re-deploy dopo KYC).
- Utente può cambiare tax mode a "Stripe Tax" o "Stripe managed" chiedendo qui.

---

## 📜 MANDATO ALL'INCASSO CON RAPPRESENTANZA — Fase 1 (Feb 18, 2026)

### Architettura fiscale
- BIDOC SRL opera in **mandato all'incasso con rappresentanza** (artt. 1703 e ss. c.c.) per conto del terapeuta.
- Il terapeuta è **l'unico titolare della prestazione sanitaria**. BIDOC è solo intermediario finanziario/tecnico.
- **Fattura sanitaria** emessa a nome del terapeuta (P.IVA del terapeuta + iscrizione Albo). Esente IVA ex art. 10 DPR 633/72 c.1 n.18.
- **Marca da bollo €2,00** obbligatoria per fatture ≥ €77,47 (DPR 642/1972) — calcolata automaticamente in `payment_transactions.marca_da_bollo_required/amount`.
- **Fattura di commissione** mensile BIDOC → terapeuta (30% + IVA 22%) — Fase 2.

### Sistema Tessera Sanitaria — Opposizione
- Paziente può opporsi alla trasmissione ex art. 3 D.M. 31/07/2015.
- Checkbox al momento del pagamento ("Mi oppongo alla trasmissione…").
- Registrato in `payment_transactions.opposizione_ts` (bool).
- Copy inforativo: opposizione non impedisce detrazione via 730 ordinario.

### Contratti editabili (immutable versioning)
- Nuova collection `contracts` — schema versionato. Ogni versione ha `content_hash` SHA-256.
- Admin può creare **nuove versioni**, ma **mai modificare** una versione passata.
- Endpoints:
  - `GET /api/admin/contracts` (admin) — tutte le versioni
  - `POST /api/admin/contracts` (admin) — crea nuova versione, demotisce la precedente
  - `GET /api/contracts/current/{kind}` (public) — versione attiva
  - `POST /api/contracts/accept` (auth) — accetta versione (write-once, con IP anonimizzato)
  - `GET /api/contracts/my-acceptances` (auth) — le mie accettazioni
  - `GET /api/admin/contracts/{id}/acceptances` (admin) — audit trail per versione
- Seed automatico all'avvio: v1 del "Mandato all'incasso con Rappresentanza" (default text 2.6KB, integralmente editabile).

### Terapeuta — Gate di accettazione
- Componente `MandatoAcceptanceGate.jsx` avvolge `TerapistaDashboard`.
- Se il terapeuta non ha accettato la **versione corrente** (match by `content_hash`), il modal blocca il dashboard.
- Pulsante "Accetto il mandato" **disabilitato** finché il terapeuta non scorre l'intero documento.
- Al click, POST `/api/contracts/accept` → dashboard sblocca.

### Admin — Editor visuale
- Pagina `/admin/contratti` con card della versione attiva (con hash) + storico versioni + audit modal.
- Modal editor: title + textarea HTML + anteprima live + pulsante "Pubblica nuova versione".

### Test verificati
- ✅ Contract seed automatico al primo boot
- ✅ Terapeuta login → modal aparece + botão desabilitado
- ✅ Scroll até fim → botão habilita → click → aceitação registrada com content_hash
- ✅ Login seguinte → modal NÃO aparece (hash matches)
- ✅ Admin /admin/contratti renderiza card v#1 com hash + botões Nuova versione/Accettazioni

### Aggiornamenti legali
- `TerminiPage.jsx` interamente riscritto: nuovo §1 "Ruolo di BIDOC SRL — Mandato all'incasso", §4 fattura sanitaria, §5 Sistema TS opposizione, §6 Stripe pagamenti.
- `PrivacyPage.jsx` — nuovo §8.bis "Trasmissione al Sistema TS" con diritto di opposizione + istruzioni.
- `BookingSheet.jsx` — step payment redesenhado: rimosso mock card, aggiunto disclosure mandato + checkbox opposizione TS + button "Continua · €X" → SMS OTP → Stripe.

---

## 🔑 Password Reset Flow (Feb 18, 2026)

### Backend (`server.py`)
- Endpoint `POST /api/auth/forgot-password` — public, generic response, timing-equalized. Genera token single-use di 32 byte URL-safe (256 bits) tramite `secrets.token_urlsafe`. Persiste **solo SHA-256 hash** in `password_reset_tokens`. Invia email via Resend. TTL 30 minuti.
- Endpoint `POST /api/auth/reset-password` — atomic single-use claim via `find_one_and_update` (`used_at: null, expires_at > now`). Timing-safe compare tramite `hmac.compare_digest`. Aggiorna `users.password_hash` (bcrypt) + `password_changed_at`.
- Segue OWASP Forgot Password Cheat Sheet: no user enumeration, hashed tokens, single-use, expiring, generic errors.
- Startup indexes: `token_hash` unique + `expires_at` TTL.

### Email template (`email_service.py`)
- `send_password_reset_email(email, reset_url, nome)` — HTML gradient warm brand-consistent, CTA arancione, disclosure 30-min/one-use, senza logging del raw token.

### Frontend
- `/forgot-password` — form email, generic success message, mascote sereno.
- `/reset-password?token=…` — password + confirm, **strength meter live 0-5**, generic error, no auto-login post-reset, `history.replaceState` per rimuovere token dall'URL, redirect a `/login`.
- Link "Password dimenticata?" aggiunto nella LoginPage.

### Test verificati
- ✅ `forgot-password`: identical response per email esistente e non esistente
- ✅ `reset-password` con token fake → 400 genérico
- ✅ Token reale (inserito nel DB con hash conosciuto) → reset OK
- ✅ Login con nuova password funziona
- ✅ **Second use dello stesso token → 400** (single-use enforcement)
- ✅ Indexes creati: unique(token_hash) + TTL(expires_at)

---

## 📄 `/mandato-legale` — Public Contract Page (Feb 18, 2026)
- Nuova pagina pubblica accessible dal footer ("Legale > Mandato legale")
- Fetches `/api/contracts/current/mandato_all_incasso` e ne renderizza il contenuto HTML corrente
- Mostra: versione #, data effettiva, hash SHA-256, box introduttivo per il paziente
- Auto-aggiornata quando l'admin pubblica una nuova versione — traccia audit invariata
- Modellata su `miodottore.it/contratto-quadro`

---

## 🧪 E2E Test Report (iteration_6.json — Feb 18, 2026)
- **Backend: 100% (14/14)** — auth, password reset, mandato, Stripe checkout accounting (30/70 + marca da bollo), contratti CRUD, GDPR audit, legal endpoints
- **Frontend: 93% (14/15)** — only miss is a test-script limitation (not a real bug)
- **retest_needed: False**

### Code review comments applied
- ✅ **[SECURITY]** Open-redirect mitigation: Stripe success/cancel URLs now built server-side from trusted allow-list (`funzionabene.it`, `www.funzionabene.it`, `FRONTEND_URL`, `REACT_APP_BACKEND_URL`). Client-supplied `origin_url` accepted only if in allow-list; otherwise fallback to env. Verified via curl attack — attacker `origin_url=evil.example.com` correctly rejected.

### Deferred to backlog
- server.py 2339 linhas → split in routers (Fase C refactor)
- PLATFORM_FEE_PERCENT → env/DB config (P2)

---

## 📱 SMS OTP: Skebby → Twilio Verify (Feb 18, 2026)

### Problema
- Skebby `/login` e `/token` endpoints retornavam 404 (deprecated ou credenciais quebradas)
- Suporte Skebby inacessível, sistema de crédito bloqueado
- `funzionabene.it` produção estava com SMS OTP silenciosamente quebrado — pacientes **não conseguiam completar prenotazioni** (P0 bug)

### Solução
Migrado para **Twilio Verify** (serviço dedicado de OTP):
- Twilio gerencia geração/expiração/rate-limiting do código server-side
- Anti-fraude embutido (SMS pumping protection)
- Sem IP whitelist necessária
- Verify Service SID: `VA18ca7fc18bf49a7ba556ecf477f018cf`
- Trial $15 grátis (~300 SMS antes de precisar de upgrade)

### Mudanças
- **`.env`**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID` adicionados; `SKEBBY_*` comentadas
- **`sms_service.py`**: reescrito com `send_sms_otp(phone, otp='', context='')` (otp ignorado — Twilio gera) e nova função `verify_sms_otp(phone, code)`
- **`server.py`**: endpoint `/sms/verify-otp` simplificado — delega verificação ao Twilio (sem armazenar código localmente)
- **`db.sms_otp`**: mantida só para audit trail (provider, timestamps), sem mais armazenar codes
- **`requirements.txt`**: `twilio==9.10.9`

### E2E Test (real)
- ✅ SMS enviado para +393518230667 → chegou em segundos
- ✅ Código `602779` verificado com sucesso (Status: approved, Valid: True)
- ✅ Second-use do mesmo código → 404 (single-use enforcement por Twilio)

### PARA PRODUÇÃO
1. Adicionar as 3 vars `TWILIO_*` no dashboard Emergent (Environment Variables)
2. Fazer upgrade da conta Twilio (adicionar cartão de crédito) — trial só permite SMS a números pré-verificados
3. Redeploy do funzionabene.it

---

## 💰 FASE 2 — Payouts & Fatture (Feb 18, 2026)

### Backend endpoints
- `GET /api/admin/payouts?payout_status=pending|paid` — lista transações pagas com summary por terapeuta (pending_amount, paid_amount, sessions_count)
- `POST /api/admin/payouts/mark-paid` — batch mark de bonifici como pagos (payout_reference opcional)
- `GET /api/admin/fattura-sanitaria/{tx_id}` — PDF (esente IVA art.10 DPR 633/72 + marca da bollo €2 se ≥ €77,47)
- `GET /api/admin/fattura-commissione/{terapeuta_id}/{year}/{month}` — PDF consolidado mensal (30% + IVA 22%)
- `_mark_payment_paid` corrigido: agora seta `paid_at` também em payment_transactions

### PDFs (reportlab)
- **Fattura sanitaria**: Prestatore/Paziente, sessione, tot, marca da bollo, disclaimer opposizione TS + mandato all'incasso
- **Fattura commissione**: Emittente BIDOC, Destinatario terapeuta, tabela sessões, imponibile + IVA 22% + tot dovuto

### Frontend
- Nova pagina `/admin/pagamenti` com sidebar item "Pagamenti":
  - Summary cards (Da pagare, Già pagato, Terapeuti)
  - Filter tabs (Da pagare / Pagati / Tutti)
  - Tabela com seleção múltipla + bulk "Segna pagati" com riferimento bonifico
  - Download PDF sanitaria per riga + PDF commissione mensal per terapeuta

### Test agent (iteration_7)
- Backend: 15/15 ✅ (após fix do bug menor de paid_at)
- Frontend: 100% ✅


---

## ✅ FASE 5 — Cruscotto Executive + IBAN (Feb 2026)

### Backend (`server.py`)
- **`TerapistaProfileInput.iban`** (Optional[str]) — accettato da `PUT /api/terapisti/{id}` e persistito su `db.terapisti`.
- **`GET /api/admin/cruscotto`** — endpoint aggregato con KPI direzionali per Admin:
  - `revenue.current_month` / `revenue.previous_month` / `revenue.delta_percent` (aggregate su `payment_transactions.paid_at`, `payment_status="paid"`, boundary da `month_start` a `next_month_start`).
  - `pending_payouts.total_cents` / `count` (paid && payout_status ≠ paid).
  - `sessions_month.completed` / `booked` / `completion_rate`.
  - `revenue_6m` — array di 6 bucket mensili (label mese abbreviato, gross_cents, count).
  - `top_therapists` — Top 5 per ricavi lordi (nome + gross + sessions).
  - `iban_missing` — terapisti con sessioni pagate NON ancora bonificate e senza IBAN (attivabile: `pending_cents > 0`).

### Frontend (`/admin`)
- **`AdminDashboard.jsx` — "Cruscotto"** riscritto:
  - 4 KPI card: Fatturato Mese (con delta % vs mese scorso), Payout Pendenti, Sessioni Mese (completate/prenotate + tasso), Terapisti Attivi.
  - **BarChart 6 mesi** (recharts) con colore `#6B8FA3`.
  - Pannello **Top 5 Terapisti** con ranking, sessioni, importo.
  - **Alert IBAN mancante** rosso con lista + link a `/admin/terapisti`.
  - Alert operativi esistenti (articoli in revisione, autocertificazioni, approvazioni).
- **`TerapistiPage.jsx`** — campo IBAN nel form modal admin, uppercase + strip spaces on-type, placeholder `IT60 X054 2811 1010 0000 0123 456`, maxLength 34.

### Test agent (iteration_8)
- Backend: 8/8 ✅ (auth guard, schema, IBAN persistence, iban_missing dopo save).
- Frontend: 100% ✅ (login admin, tutti i data-testid presenti, bar chart svg renderizzato, IBAN uppercases + persiste).
- Correzioni minori applicate dopo review: boundary mese esatta con `next_month_start`, `iban_missing` filtrato a `pending_cents > 0` per essere azionabile.

### Backlog residuo
- **P2** Refactoring `server.py` (~2660 righe) — estrarre `admin_analytics.py` per Cruscotto + payouts, ridurre N+1 con `$lookup`.
- **P2** Validazione formato IBAN (regex `IT\d{2}[A-Z0-9]{23}`) nel backend PUT.
- **P2** Seed di una tx unpaid per demo del flow "da bonificare".
- **P3** Refactoring `OnboardingSection.jsx`, `ChatPanel.jsx`, `matching()`.
- **P3** Invio SDI (fatture elettroniche) — in attesa del commercialista.

---

## ✅ FASE 6 — Consolidamento Cruscotto (Feb 2026)

### Refactoring backend
- **`/app/backend/routers/admin_analytics.py`** (NUOVO) — factory `build_router(db, require_admin)`, mount in `server.py` via `app.include_router(..., prefix="/api")`.
- Rimossa la funzione inline `admin_cruscotto` da `server.py` (–176 righe).
- Eliminati gli N+1 su `db.terapisti` con helper `_batch_lookup_therapists({"_id":{"$in":[...]}})` — un solo round-trip per top_therapists e iban_missing.

### Validazione IBAN
- `TerapistaProfileInput.iban` → `@field_validator("iban", mode="before")` con regex `^IT\d{2}[A-Z0-9]{23}$`. Comportamenti:
  - IBAN invalido → HTTP 422 con messaggio italiano chiaro
  - Stringa vuota → consentita (permette di cancellare il campo)
  - IBAN con spazi/minuscole → normalizzato automaticamente

### Seed Payout Demo
- `seed_data()` estesa: se `db.payment_transactions` non contiene alcuna tx `payment_status=paid, payout_status!=paid`, crea una transazione demo per **Giulia Marchetti** (€65 lordo → €45,50 al terapeuta, €19,50 commissione), datata 3 giorni fa, con IBAN mancante — così KPI "Payout Pendenti" e alert "IBAN Mancante" mostrano dati reali. Idempotente.

### Report PDF Mensile
- **`/app/backend/cruscotto_pdf.py`** (NUOVO) — `build_cruscotto_pdf(data) → bytes` con reportlab: KPI grid, bar chart 6 mesi, tabella ricavi mensili, Top 5 terapisti, alert IBAN mancante.
- **`GET /api/admin/cruscotto/report.pdf`** — export PDF con `Content-Disposition: attachment; filename="cruscotto-YYYY-MM.pdf"`.
- Bottone **"Esporta PDF"** (`data-testid="btn-export-pdf"`) in header di `/admin`.

### Test agent (iteration_9)
- Backend: 10/10 ✅ · Frontend: 100% ✅
- Verificate: idempotenza seed, refactoring identico allo schema originale, PDF valido (%PDF-1.4), regex IBAN in tutti gli edge case, auth guard su entrambi gli endpoint.

### Backlog residuo
- **P2** Continuare refactoring `server.py` (>2500 righe): estrarre `routers/payments.py`, `routers/terapisti.py`, `routers/appuntamenti.py`.
- **P2** Restituire `id` (non `_id`) dagli endpoint GET (pre-esistente, non introdotto in questa fase).
- **P3** Refactoring `OnboardingSection.jsx`, `ChatPanel.jsx`, `matching()`.
- **P3** Invio SDI (fatture elettroniche) — in attesa del commercialista.


---

## ✅ FASE 7 — Refactoring Modulare Backend (Feb 2026)

### Obiettivo
Estrarre da `server.py` (monolite ~2500 righe) le 3 domini più corposi mantenendo comportamento identico. **Test regression 27/27 ✅**.

### Nuovi moduli
- **`/app/backend/deps.py`** (122 righe) — single source of truth per: `db`, `client`, JWT/Stripe/PLATFORM_FEE constants, `hash_password` / `verify_password` / `create_access_token` / `create_refresh_token` / `PyObjectId` / `validate_codice_fiscale`, `get_current_user` / `require_auth` / `require_admin`.
- **`/app/backend/models.py`** (152 righe) — tutti i Pydantic models (Register/Login/OTP, TerapistaProfileInput con `@field_validator` IBAN regex, PazienteProfileInput, AppuntamentoInput, ArticoloInput, ConsentPrefs, ContractInput, CheckoutBookingRequest, MarkPayoutPaidRequest, ecc.).
- **`/app/backend/routers/appuntamenti.py`** (152 righe) — 7 endpoint `/appuntamenti/*` + Daily.co video-token + presenze.
- **`/app/backend/routers/terapisti.py`** (332 righe) — 16 endpoint `/terapisti/*` + `/admin/terapisti/*` incluso slot calculator (GIORNI_IT), upload documenti, autocertificazione DPR 445/2000, admin verifica.
- **`/app/backend/routers/payments.py`** (402 righe) — 8 endpoint: Stripe checkout, webhook, therapist earnings, admin payouts+mark-paid, fattura sanitaria/commissione PDFs. Include `_mark_payment_paid` helper. Usa **lazy import** di `_finalize_confirmed_booking` da `server.py` per evitare dipendenze circolari.

### server.py — Dimagrito
- Da **~2500 → 1492 righe** (-40%).
- Contiene ancora: auth/utenti/blog/chat/contratti/SMS/public prenota/media/dashboard/seed_data/`_finalize_confirmed_booking`/scheduler.

### Bugfix bonus applicato
- `seed_data()` — guard per pending payout ora filtra su `{_seed: True, payment_status: paid, payout_status: !=paid}` invece di qualsiasi pending tx. Al riavvio del backend, se il pending seeded è stato marcato paid durante i test, viene ricreato automaticamente (idempotente e resiliente ai cicli di test).

### Test agent (iteration_10)
- **Backend 27/27 tests ✅** in `/app/backend/tests/test_iteration10_refactor.py`
- **Frontend 100% ✅** (admin dashboard + terapisti page invariati)
- Nessuna regressione. Comportamento identico a iteration_9 su tutti gli endpoint.

### Backlog residuo
- **P3** Migrare `_finalize_confirmed_booking` + `schedule_reminders` + `scheduler` in `booking_service.py` per eliminare la lazy-import.
- **P3** Restituire `id` invece di `_id` dagli endpoint GET (guideline MongoDB) — richiede aggiornamento coordinato frontend.
- **P3** Split ulteriore: `routers/auth.py`, `routers/blog.py`, `routers/chat.py`, `routers/contracts.py`, `routers/public.py`.
- **P3** Separare `AppuntamentoUpdateInput` (tutti Optional) da `AppuntamentoInput` per PUT parziali.


---

## ✅ FASE 8 — Modularizzazione Finale (Feb 2026)

### Nuovi moduli
- **`/app/backend/booking_service.py`** (103 righe) — proprietario esclusivo di `scheduler = AsyncIOScheduler()`, `start_scheduler()`, `stop_scheduler()`, `schedule_reminders()`, `finalize_confirmed_booking()`. Zero dipendenze circolari.
- **`/app/backend/routers/auth.py`** (227 righe) — 8 endpoint auth: register, verify-otp, resend-otp, login, logout, me, forgot-password, reset-password. Internals OWASP-compliant (token digest SHA-256, timing equalization con bcrypt dummy, single-use via `find_one_and_update` atomico, `hmac.compare_digest`).
- **`/app/backend/routers/blog.py`** (87 righe) — 7 endpoint blog: CRUD + admin approva/rifiuta + `/public/blog`.

### server.py — Dimagrimento finale
- Da **2500 (v0) → 1492 (fase 7) → 1136 (fase 8)** — **–55% totale**.
- Rimossa la **lazy import** in `payments.py._mark_payment_paid`: ora `from booking_service import finalize_confirmed_booking` a livello modulo.

### Import graph pulito
```
server.py  →  routers/{auth, blog, payments, appuntamenti, terapisti, admin_analytics}
routers/payments  →  booking_service
booking_service   →  deps + daily_service + email_service
```
**Nessuna dipendenza circolare.**

### Test agent (iteration_11)
- **Backend 58/58 tests ✅** (27 regressione iter10 + 31 nuovi iter11) in ~14s.
- Log `[SCHEDULER] started` verificato ad ogni startup.
- Nessuna regressione. Comportamento identico a iter10.

### Note dal code review
- ✅ RBAC blog corretto (terapeuta→bozza, admin→pubblicato/approva).
- ✅ Cookie httponly/samesite=none/secure/path=/ conservati sui flussi login/verify/logout.
- 💡 `_get_frontend_origin` fallback su `REACT_APP_BACKEND_URL` — funziona in prod (stesso origin) ma in locale punterebbe al backend. Considerare env `FRONTEND_URL` esplicita in dev.

### Backlog residuo
- **P3** `routers/pazienti.py`, `routers/chat.py` (conversazioni/messaggi), `routers/contracts.py`, `routers/public.py` (prenota + matching + terapisti).
- **P3** `AppuntamentoUpdateInput` / `ArticoloUpdateInput` con tutti i campi Optional per PUT parziali.
- **P3** Restituire `id` invece di `_id` dagli endpoint GET (guideline MongoDB) — richiede aggiornamento coordinato frontend.
- **P2** Email report automatico mensile del Cruscotto PDF via Resend.


---

## ✅ FASE 9 — Calendario Disponibilità + Riprogrammazione (Feb 2026)

### Nuove funzionalità

**1. Calendario terapista (date-specifiche)**
- Nuovo campo `terapisti.disponibilita_calendario`: `{ "YYYY-MM-DD": ["HH:MM", ...] }`
- Pagina `/terapeuta/calendario`: griglia mensile + drill-down per giorno (slot 8:00-20:00, sessioni da 50 minuti)
- Verde = disponibile, rosso = non disponibile, badge conteggio slot
- Salva come **bozza** o **conferma e pubblica** (visibilità pubblica)

**2. Calendario admin aggregato**
- Pagina `/admin/calendario`: vista mensile con conteggio terapisti disponibili per giorno
- Codice colore: 1-2 chiaro / 3-5 medio / 6+ scuro / 0 rosso
- Drill-down cliccabile → lista terapisti attivi + slot orari specifici

**3. Riprogrammazione paziente via link email**
- Al pagamento, generato token single-use SHA-256 con scadenza = 1h prima appuntamento
- Link `/riprogramma/{id}?token=xxx` in email di conferma + reminder (piccolo, nel footer)
- Pagina pubblica token-authenticated: mostra appuntamento corrente + slot calendario terapista → conferma sposta l'appuntamento (senza rimborso)
- Per rimborso: `mailto:assistenza@funzionabene.it` (istruzione in footer email + pagina errore)

**4. Email semplificate**
- Rimosso reminder 1 ora prima (per richiesta utente)
- Attivi: **email conferma immediata + reminder 1 giorno prima**
- Entrambe con link "Riprogramma qui" piccolo nel footer

### Endpoint nuovi (`/app/backend/routers/calendario.py`)
- `GET /api/terapisti/me/calendario` — legge calendario proprio + status bozza/pubblicato
- `PUT /api/terapisti/me/calendario` — batch update slots + flag `pubblica`
- `POST /api/terapisti/me/calendario/pubblica` — pubblica bozza
- `GET /api/admin/calendario?anno=YYYY&mese=MM` — vista aggregata direzionale
- `GET /api/public/terapisti/{tid}/calendario?anno=YYYY&mese=MM` — public per pagina riprogramma
- `GET /api/riprogramma/{id}/validate?token=xxx` — valida token
- `POST /api/riprogramma/{id}/confirm` — cancella vecchio + crea nuovo appuntamento

### File modificati/creati
- ✨ NEW `/app/backend/routers/calendario.py` (302 righe)
- 📝 MOD `/app/backend/booking_service.py` — gen token + rimosso reminder 1h
- 📝 MOD `/app/backend/email_service.py` — link riprogramma in footer + template reminder aggiornato
- ✨ NEW `/app/frontend/src/pages/therapist/TerapistaCalendarioPage.jsx` (232 righe)
- ✨ NEW `/app/frontend/src/pages/admin/AdminCalendarioPage.jsx` (155 righe)
- ✨ NEW `/app/frontend/src/pages/RiprogrammaPage.jsx` (215 righe)
- 📝 MOD `/app/frontend/src/App.js` — 3 route nuove
- 📝 MOD `/app/frontend/src/components/shared/Sidebar.jsx` — voci menu

### Test agent (iteration_12)
- Backend: **16/16 ✅** (pytest completo su CRUD calendar + admin aggregate + reschedule flow + booking service)
- Frontend: **100% ✅** (tutte le 3 pagine renderizzano, save/publish/error card funzionano)
- Correzioni post-review applicate: try/except per ObjectId non valido su endpoint pubblico, rimosso codice morto in calendario.py.

### Backlog residuo
- **P2** Migrare `/api/terapisti/{id}/slots` a leggere da `disponibilita_calendario` (attualmente ancora su `disponibilita` legacy settimanale)
- **P2** Notifica email al terapista quando un paziente riprogramma (attualmente solo evento silenzioso)
- **P3** Vista `/admin/calendario`: aggiungere link diretto al profilo di ogni terapista dal drill-down
- **P3** Vista terapista: pulsante "Copia settimana" per replicare le disponibilità di una settimana su quella successiva


---

## ✅ FASE 10 — Rifiniture Calendario + Rimborso Automatico (Feb 2026)

### 1. Migrazione Slots → Calendario
- `GET /api/terapisti/{id}/slots` ora legge **`disponibilita_calendario`** (nuovo modello data-specifico) quando è pubblicato.
- Fallback automatico su `disponibilita` legacy (settimanale ricorrente) per terapisti che non hanno ancora migrato.
- Response include `"source": "calendar" | "legacy_weekly"` per debug/monitoring.
- Test verificato: Maria Rossi con calendar published 2026-08-10/11/17 → 6 slot corretti, filtri booked+past attivi.

### 2. Notifica Terapista Riprogrammazione
- Nuova funzione `send_reschedule_notification_email` in `email_service.py` con template dark-mode.
- Chiamata da `confirm_reschedule` in `routers/calendario.py` (best-effort, try/except).
- Include: nome paziente, vecchio orario (barrato), nuovo orario (evidenziato), branding.
- **Bugfix testing agent**: `db.users.find_one({_id: terapista.user_id})` ora casta `user_id` (string) in `ObjectId` prima del lookup.

### 3. Replica Settimana
- Bottone **"Replica questa settimana su quella successiva"** in `/terapeuta/calendario` (drill-down del giorno).
- Logica: calcola la settimana Lun-Dom contenente il giorno selezionato, copia gli slot sui 7 giorni successivi.
- **Merge (union)** con slot esistenti: se il giorno target ha già delle disponibilità, unifica senza sovrascrivere. Toast informativo se non c'è nulla da aggiungere.

### 4. Rimborso Automatico Stripe
- Nuovo endpoint `POST /api/admin/refunds`:
  - Valida transazione (paid + payout_status != paid + presenza `stripe_payment_intent_id`)
  - Chiama `stripe.Refund.create(payment_intent=..., idempotency_key=f"refund-{tx_id}")` — **safe contro double-click**
  - Aggiorna DB: `status=refunded, payment_status=refunded, payout_status=cancelled, refunded_at, refund_reason, refund_admin_note, refund_admin_id, stripe_refund_id`
  - Cancella l'appuntamento con `cancellato_motivo=rimborsato`
- UI in `/admin/pagamenti`: pulsante **"Rimborsa"** rosso accanto a "Sanitaria" solo per righe con `payout_status=pending`. Prompt+confirm+toast. **Non appare** dopo bonifico (payout_status=paid) — se serve rimborso post-bonifico, admin deve concordare con il terapista.

### Test agent (iteration_13)
- Backend: **29/29 ✅** (13 nuovi + 16 regressione iter12) + iter10/11 regression 58/58 ancora verdi.
- Frontend: **100% ✅** su tutte le nuove interazioni (replica, rimborso, error toast).
- 2 review action items applicati post-test: merge unions in replicaSettimana, `idempotency_key` in Stripe refund.

### Backlog residuo
- **P3** Audit generale delle `db.users.find_one({_id: <string>})`: alcuni caller passano string invece di ObjectId — creare un helper `find_user_by_id(uid)` che casta automaticamente.
- **P3** Sostituire `window.prompt/confirm` nel pulsante Rimborsa con shadcn Dialog per consistenza UI.
- **P3** `refund` policy: aggiungere warning se la sessione è già completata (data futura vs passata).
- **P3** `durata_minuti` per terapista: leggere da campo custom invece di hardcode 50.


---

## ✅ FASE 11 — Documenti Legali Editabili + Compliance GDPR (Feb 2026)

### 1. Analisi Legale Comparativa Concorrente
- Analizzati 4 documenti legali di Unobravo (Privacy Utenti, Privacy Registrati, Privacy Calendario, Cookie Policy)
- Confronto vs GDPR (Reg. UE 2016/679) + Codice Privacy italiano (D.Lgs. 196/2003) + Codice Deontologico Psicologi
- Decisione modello giuridico: **BIDOC SRL = marketplace tecnologico** (NON struttura sanitaria)
- Terapeuta = Titolare autonomo dati clinici (art. 9.2.h GDPR)
- BIDOC = Responsabile ex art. 28 GDPR per ospitalità tecnica dei dati clinici
- **Nessun Direttore Sanitario richiesto** (validato con research su normativa italiana)

### 2. 6 Documenti Legali Creati (Italiano)
File Markdown sorgente in `/app/memory/legal/`:
- `informativa_privacy_visitatori.md` — Privacy per visitatori sito
- `informativa_privacy_pazienti.md` — Privacy pazienti con 3 sezioni (BIDOC titolare + Terapeuta titolare + Diritti comuni)
- `informativa_privacy_terapeuti.md` — Privacy terapeuti + **DPA art. 28 GDPR** integrato
- `cookie_policy.md` — Cookie policy con categorie Necessari/Statistica/Esperienza/Marketing
- `termini_e_condizioni_pazienti.md` — T&C completi con clausole vessatorie art. 1341-1342 c.c.
- `contratto_collaborazione.md` — Contratto Collaborazione 22 articoli con:
  - Modello economico: **commissione BIDOC 30%**
  - Liquidazione **mensile entro il 15 del mese successivo**
  - Cancellazioni <24h/>24h/no-show
  - Non sollecitazione 12 mesi + penale 3x tariffa
  - Sospensione automatica per Ordine/P.IVA scaduta
  - Firma elettronica (senza doppio OTP per scelta utente)

### 3. Backend — Seed automatico
- Estensione di `server.py` con `_seed_legal_documents()`:
  - Legge i 6 file `.md` all'avvio
  - Sostituisce placeholder `[DATA_PUBBLICAZIONE]` con "15 febbraio 2026"
  - Converte Markdown → HTML via `markdown-it-py` (già installato)
  - Inserisce in `db.contracts` collection come v1 pubblicata
  - Idempotente: skip se `kind` già esistente
- Nuovi kinds seedati: `privacy_visitatori`, `privacy_pazienti`, `privacy_terapeuti`, `cookie_policy`, `termini_pazienti`, `contratto_collaborazione`
- Kind legacy mantenuto: `mandato_all_incasso` (v1 originale)

### 4. Admin Panel — Documenti Legali Editabili
Estensione di `/admin/contratti`:
- Rinominato in "Documenti Legali"
- 7 cards (una per ogni kind) con:
  - Titolo + versione attuale + hash SHA-256
  - Pulsante "Nuova versione" → editor modale HTML con anteprima
  - Pulsante "Accettazioni" → audit trail immutabile
  - Sezione espandibile "Mostra contenuto attuale"
  - Sezione espandibile "Versioni precedenti" con storico
- Ogni modifica salvata crea versione immutabile, la precedente resta archiviata

### 5. Frontend Pubblico — Pagine Legali Dinamiche
Nuovo componente `DynamicLegalPage.jsx` che consuma `/api/contracts/current/{kind}`:
- `/privacy` e `/privacy-pazienti` → Informativa Privacy Pazienti
- `/privacy-visitatori` → Informativa Privacy Visitatori
- `/privacy-terapeuti` → Informativa Privacy Terapeuti + DPA (**restricted: solo terapeuti/admin**)
- `/termini` e `/termini-pazienti` → Termini e Condizioni
- `/cookie` e `/cookie-policy` → Cookie Policy (con toggle preferenze interattivo)
- `/contratto-collaborazione` → Contratto (**restricted: solo terapeuti/admin**)
- `/mandato-legale` → Mandato all'incasso (legacy v1)

Ogni pagina:
- Mostra title + versione + hash pubblici (trasparenza)
- Refresh automatico se admin pubblica nuova versione
- Data ultimo aggiornamento formattata in italiano

### 6. Dati aziendali consolidati
Aggiornato `legalInfo.js` con dati BIDOC SRL definitivi:
- Sede: Via Mazzini 62, 33097 Spilimbergo (PN)
- P.IVA/CF: 01985930930
- REA: PN-377600
- PEC: bidocsrl@pecimprese.it
- Email: info@bidoc.it
- Privacy: privacy@bidoc.it
- DPO: Caio Silvestre Richieri (CF SLVCAI76D16Z602F)

### File aggiuntivo
`/app/memory/legal/PIANO_IMPLEMENTAZIONE_TECNICA.md` — Roadmap 9 fasi per implementazione completa GDPR:
- Fase 1-2: Pagine legali + Cookie banner ✅ (parziale, banner già esistente)
- Fase 3-4: Consensi granulari paziente + terapeuta (**Fase 12 futura**)
- Fase 5: Diritti GDPR (portabilità, oblio, gestione consensi)
- Fase 6: Firma elettronica del Contratto Collaborazione
- Fase 7: Sistema aggiornamento documenti (email automatica + workflow "NON ACCETTO")
- Fase 8: Retention automatica (36 mesi)
- Fase 9: Registro Trattamenti art. 30 + DPIA art. 35 (documenti interni)

### Backlog residuo dopo Fase 11
- **P0** Fase 12: Firma elettronica del Contratto Collaborazione con scroll obbligatorio + digitazione nome + Ricevuta PDF via Emergent Object Storage
- **P0** Fase 13: Workflow aggiornamento versione MAJOR → email automatica + resposta "NON ACCETTO" = disattivazione automatica entro 48h
- **P1** Fase 14: Consensi granulari nel signup paziente (marketing/ricerca/dati sanitari)
- **P1** Fase 15: Area "I miei consensi" per gestire e revocare
- **P2** Fase 16: Retention automatica 36 mesi (anonimizzazione)
- **P2** Fase 17: Registro Trattamenti (documento interno)

---

## ✅ FASE 12 — Firma Elettronica + Notify MAJOR + Area Privacy Utente (Feb 2026)

### 1. Firma Elettronica del Contratto Collaborazione (Terapeuti)
- Nuovo router `/app/backend/routers/legal_signature.py` (594 righe)
- Nuovo helper `/app/backend/object_storage.py` — Emergent Object Storage (session-cached, retries su 403)
- Nuovo helper `/app/backend/signature_pdf.py` — genera Ricevuta PDF via ReportLab con:
  - Header BIDOC + dati Titolare
  - Dati Sottoscrittore (nome, CF, P.IVA, iscrizione Ordine)
  - Tabella "Documenti Sottoscritti" con versione + hash SHA-256
  - Metadati firma: nome digitato, timestamp UTC, IP, user-agent
  - Dichiarazione probatoria art. 20 CAD + eIDAS
  - Allegato: contenuto integrale di ciascun documento firmato
- Endpoints:
  - `POST /api/contracts/sign` — firma atomica di N contratti, valida nome (case-insensitive) vs anagrafica
  - `GET /api/contracts/pending/mine` — documenti pendenti (terapeuti: 4 obbligatori)
  - `GET /api/contracts/signatures/mine` — storico firme raggruppato per receipt_id
  - `GET /api/contracts/receipt/{receipt_id}` — download PDF (owner/admin only)
- Frontend `/terapeuta/firma-documenti` (`FirmaDocumentiPage.jsx`):
  - Sidebar 4 documenti + tick "letto" quando scroll ≥95%
  - Contenuto principale con scroll tracker
  - Footer sticky con signature form: nome + validation live
  - Success state con download PDF + link dashboard
- Fallback: se Object Storage fallisce, PDF salvato inline base64 in Mongo

### 2. Sistema Aggiornamento Versione MAJOR
- Endpoint `POST /api/admin/contracts/{cid}/notify-major` (admin only):
  - Trova utenti che hanno accettato versione precedente del kind
  - Genera decline token univoco (SHA-256 hashed, valido 60 giorni)
  - Invia email HTML formattata via Resend con 2 CTA: "Firma" (URL app) e "NON ACCETTO" (URL magic-link)
  - Registra timestamp `major_notification_sent_at` sul contratto
- Endpoint pubblico `GET /api/legal/decline/{token}`:
  - Verifica token (non usato, non scaduto)
  - Marca `pending_deactivation_reason=legal_decline`, `pending_deactivation_at=+48h`
  - Se terapeuta: sospende immediatamente (`sospeso=true`) per bloccare nuove prenotazioni
  - Marca token come usato
- Frontend `/legal-decline/:token` (`LegalDeclinePage.jsx`):
  - Stato di successo con data disattivazione + info recesso da appuntamenti
  - Stato errore per token invalido/scaduto/già usato
- Admin `/admin/contratti`:
  - Pulsante "📢 Notifica MAJOR" per ogni documento con version > 1
  - Confirm dialog + contatore utenti notificati

### 3. Area "I miei dati" (Diritti GDPR)
- Nuova pagina `/terapeuta/privacy` e `/paziente/privacy` (`PrivacyUtentePage.jsx`):
  - **Documenti firmati** (solo terapeuti) — lista storico + download ricevute
  - **Consensi attivi** — 3 toggle (marketing, miglioramento, ricerca) con effetto immediato
  - **Storico consensi** — log delle azioni grant/revoke con timestamp
  - **Scarica i miei dati** (art. 20 GDPR) — download JSON completo
  - **Cancella il mio account** (art. 17 GDPR) — form con conferma "CANCELLA" + motivazione facoltativa
- Backend endpoints:
  - `GET /api/user/gdpr/export` — JSON con: titolare, utente, profilo, appuntamenti, firme_contratti, storico_consensi, consensi_attuali
  - `POST /api/user/gdpr/delete-account` — soft-delete + workflow admin 15 giorni, ip anonimizzato
  - `GET /api/user/consents/mine` — stato attuale + storico
  - `POST /api/user/consents/update` — grant/revoke con audit log

### 4. Sicurezza & Privacy by Design
- IP address anonimizzato prima della persistenza (ultimo ottetto IPv4 → 0, /48 IPv6)
- Consent history immutabile (append-only)
- Delete request scriveghe in `db.gdpr_deletion_requests` per audit admin
- Doppio percorso PDF (Object Storage + inline base64 fallback) per garantire disponibilità

### 5. Testing
- Backend: 12/12 pytest passing (iteration_16.json)
- Bug fix critico applicato dal testing agent: tz-aware/naive datetime comparison in `legal_decline`
- 3 minor issues risolti: dead code audit_consents rimosso, inline PDF fallback implementato, empty state per Documenti firmati

### File di riferimento
- `/app/backend/routers/legal_signature.py`
- `/app/backend/signature_pdf.py`
- `/app/backend/object_storage.py`
- `/app/backend/email_service.py` (aggiunto `send_legal_major_update_email`, `send_signature_receipt_email`)
- `/app/frontend/src/pages/therapist/FirmaDocumentiPage.jsx`
- `/app/frontend/src/pages/shared/PrivacyUtentePage.jsx`
- `/app/frontend/src/pages/public/LegalDeclinePage.jsx`
- `/app/frontend/src/pages/admin/ContrattiPage.jsx` (pulsante Notifica MAJOR)
- `/app/frontend/src/components/shared/Sidebar.jsx` (item "I miei dati")
- `/app/frontend/src/App.js` (nuove rotte)

### Backlog residuo dopo Fase 12
- **P1** Fase 13: Consensi granulari nel signup paziente (checkbox obbligatori privacy_pazienti + T&C + dati_sanitari, checkbox facoltativi marketing/ricerca/miglioramento)
- **P1** Fase 14: Cron settimanale di anonimizzazione dopo 36 mesi inattività
- **P1** Fase 15: Cron 48h che elabora `pending_deactivation_reason=legal_decline` (cancella appuntamenti, rimborsa pazienti, hard-delete account)
- **P2** Fase 16: Cookie banner GDPR-compliant con consent-mode Google v2 + pixel Meta/TikTok/LinkedIn (opzione d=2)
- **P2** Fase 17: Registro Trattamenti art. 30 + DPIA art. 35 (documenti interni)

---

## ✅ FASE 13 — Cookie Banner GDPR + Retention + Legal Decline 48h + Consensi Signup (Feb 2026)

### 1. Cookie Banner GDPR-Compliant (Provv. Garante 231/2021)
- Nuovo componente `/app/frontend/src/components/public/CookieBanner.jsx`:
  - Banner compatto con **3 pulsanti di pari evidenza grafica**: "Rifiuta tutti" | "Personalizza" | "Accetta tutti"
  - Modal preferenze con 4 categorie: Necessari (sempre attivo), Statistica, Esperienza, Marketing
  - Descrizione dettagliata dei singoli servizi (Meta Pixel, TikTok Pixel, LinkedIn Insight, Google Ads, GA4, Microsoft Clarity)
  - Storage localStorage `funzionabene_cookie_consent_v1` con versioning
  - Backend audit log via `POST /api/audit/consent` (schema esistente)
  - `window.__openCookiePreferences()` esposto per riapertura da footer
- Nuovo `/app/frontend/src/utils/cookieLoader.js`:
  - **Google Consent Mode v2** con `initGoogleConsentDefaults()` (denied di default) + `updateGoogleConsent()`
  - Loaders idempotenti per: GA4, MS Clarity, Meta Pixel, TikTok Pixel, LinkedIn Insight, Google Ads
  - Pixel IDs caricati da `process.env.REACT_APP_*` (placeholders finché non forniti)
- Rimosso vecchio `CookieConsentBanner.jsx` per evitare duplicazioni
- Registrato globalmente in App.js dopo `</Routes>`

### 2. Retention Automatica Settimanale
- Nuovo `/app/backend/scheduled_jobs.py` con APScheduler:
  - `retention_anonymize(db)` — cron domenica 03:00 UTC
  - Trova pazienti con `last_login_at < 36 mesi fa` (o mancante + `created_at < 36 mesi fa`)
  - Skip di sicurezza: NON anonimizza se ha appuntamenti negli ultimi 36 mesi
  - Anonimizzazione: email→`anon-{id}@anon.funzionabene.local`, nome→"Anonimo", cognome/telefono→null, is_active=false, gdpr_anonymized_at
  - **Dati fiscali mantenuti** in `db.fatture` per obbligo art. 2220 c.c. (10 anni)
- **NON** anonimizza terapeuti automaticamente (obblighi professionali di conservazione)

### 3. Cron Disattivazione 48h dopo Legal Decline
- `process_legal_declines(db)` — cron ogni ora al minuto :07
- Trova users con `pending_deactivation_reason=legal_decline` e `pending_deactivation_at < now`
- Per terapeuti: cancella appuntamenti futuri (`stato=cancellato`, `rimborso_pending=true` per pickup dal worker refund Stripe)
- Hard-deactivate: `is_active=false`, unset `pending_deactivation_*`
- Se terapeuta: `terapista.sospeso=true`, `sospeso_motivo=legal_decline_definitive`
- Log in `db.admin_actions` per audit trail

### 4. Consensi Granulari nel Signup
- `models.py`: `RegisterInput` esteso con 6 consent fields + version fields
- `routers/auth.py`: 
  - Validazione: paziente DEVE dare `consenso_privacy + consenso_termini` (400 altrimenti)
  - Snapshot in `user.consents` con timestamp per singolo consenso
  - **6 eventi in `db.consent_history`** collection (art. 7 GDPR accountability), source='signup'
- `RegisterPage.jsx`:
  - Paziente: 3 checkbox obbligatori (*) — Privacy, Termini, Dati Sanitari (art. 9.2.a)
  - Terapeuta: 1 checkbox obbligatorio — Privacy
  - 3 checkbox facoltativi con divisore "FACOLTATIVI" — Marketing, Ricerca, Miglioramento
  - Ogni checkbox linka al documento pertinente in nuova tab

### 5. Admin Manual Triggers
- `POST /api/admin/jobs/retention/run` — trigger manuale retention
- `POST /api/admin/jobs/legal-decline/run` — trigger manuale legal decline processor
- Utile per test in staging e per admin intervention

### 6. Testing
- Testing agent iteration_17: 13/13 backend passing
- 1 bug critico fix: rimossi 2 CookieBanner simultanei (rimosso CookieConsentBanner.jsx legacy)
- Screenshot verify: single banner con 3 pulsanti pari evidenza + 4 categorie in Personalizza + 6 checkbox nel register

### File di riferimento
- `/app/backend/scheduled_jobs.py`
- `/app/backend/server.py` (startup event con AsyncIOScheduler)
- `/app/backend/routers/auth.py` (register con consents_snapshot + history)
- `/app/backend/routers/legal_signature.py` (admin triggers)
- `/app/backend/models.py` (RegisterInput con 6 consent fields)
- `/app/frontend/src/components/public/CookieBanner.jsx`
- `/app/frontend/src/utils/cookieLoader.js`
- `/app/frontend/src/pages/RegisterPage.jsx`
- `/app/frontend/src/App.js` (CookieBanner globale)
- `/app/frontend/src/components/public/PublicLayout.jsx` (rimosso vecchio banner)

### Backlog residuo dopo Fase 13
- **P2** Fase 14: Registro Trattamenti art. 30 GDPR + DPIA art. 35 (documenti interni)
- **P2** Fase 15: Endpoint webhook Resend per intercettare risposta email "NON ACCETTO" e triggerare decline flow automaticamente
- **P3** Fase 16: Real pixel IDs (Meta/TikTok/LinkedIn/Google Ads) e configurazione tracking eventi conversione
- **P3** Fase 17: Envio SDI (fatturazione elettronica automatizzata)

---

## ✅ FASE 14 — Fatturazione Elettronica MVP (Feb 2026)

### Approccio scelto (MVP low-cost, no SdI automation)
BIDOC genera XML + PDF di ogni fattura; ogni terapeuta riceve via email settimanale i suoi documenti e li trasmette autonomamente al Sistema TS / SdI. Nessuna delega Agenzia Entrate richiesta all'inizio.

### 1. Generatore FatturaPA v1.2.2
- Nuovo `/app/backend/fatturazione.py` (~450 righe):
  - `generate_xml_sanitaria()` — esente IVA art. 10 DPR 633/72 c.1 n.18, natura N4, marca bollo €2 se ≥ €77,47
  - `generate_xml_commissione()` — B2B con IVA 22% (BIDOC → terapeuta)
  - `generate_pdf()` — versione leggibile con logo, dati fiscali, riferimenti normativi
  - `next_fattura_number()` — contatore atomico Mongo per serie separate (FZ-YYYY-NNNN per sanitarie, CM-YYYY-NNNN per commissioni)
  - Regime fiscale mappato al codice AdE (RF01/RF02/RF19)
- Schema conforme allo standard Agenzia Entrate — validato struttura XML

### 2. Modelli e profilo terapeuta esteso
- `models.py`: aggiunto al `TerapistaProfileInput`:
  - `regime_fiscale` (default: forfettario)
  - `codice_sdi` (7 char, "0000000" se usa PEC)
  - `pec` (obbligatorio se codice_sdi mancante)

### 3. Router `/app/backend/routers/fatture.py`
Endpoints:
- `POST /api/admin/fatture/generate/paziente/{appuntamento_id}` — genera sanitaria (idempotente)
- `POST /api/admin/fatture/generate/commissione/{year}/{month}` — genera B2B commissioni mensili aggregate per terapeuta
- `GET /api/fatture/mine` — terapeuta vede le sue fatture emesse + commissioni ricevute
- `GET /api/admin/fatture[?kind=]` — cassetto BIDOC completo
- `GET /api/fatture/{id}/xml` — download XML (Object Storage + fallback inline base64)
- `GET /api/fatture/{id}/pdf` — download PDF

### 4. Scheduler jobs
Aggiunti in `scheduled_jobs.py`:
- **weekly_fatture_email** — Domenica 20:00 UTC — invia email a ogni terapeuta con le fatture della settimana + PDF allegato
- **monthly_generate_commissioni** — 1° del mese 03:30 UTC — genera fatture B2B commissione del mese precedente
- Admin manual triggers via `/api/admin/jobs/weekly-fatture/run` e `/api/admin/jobs/monthly-commissioni/run`

### 5. Frontend Admin/Terapeuta Fatture
- Nuovo `/app/frontend/src/pages/admin/FatturePage.jsx`:
  - Rotta admin: `/admin/fatture` con `isAdmin={true}` — cassetto completo BIDOC
  - Rotta terapeuta: `/terapeuta/fatture` con `isAdmin={false}` — solo fatture proprie
  - Tabella con: numero, tipo (sanitaria/commissione con badge colorati), data, imponibile, IVA, totale, marca bollo, download XML/PDF
  - KPI cards: totale sanitarie + totale commissioni BIDOC
  - Filtri per tipo + ricerca per numero
  - Export CSV completo per commercialista
  - Admin: pulsanti manual trigger jobs settimanale/mensile
- Sidebar: nuovo item "Fatture" (icona Receipt) per admin e terapeuta

### 6. Testing manuale
- ✅ Fattura sanitaria FZ-2026-0001 generata per demo appt (€70 esente, natura N4)
- ✅ Fattura commissione CM-2026-0001 generata (€21 imponibile + €4,62 IVA = €25,62)
- ✅ XML valido con namespaces corretti (FatturaElettronicaHeader, DatiTrasmissione, CedentePrestatore, CessionarioCommittente, DatiBeniServizi)
- ✅ PDF leggibile 2544 bytes, magic %PDF-1.4
- ✅ Screenshot admin/fatture: tabella + KPI + filtri + download

### File di riferimento
- `/app/backend/fatturazione.py` (generatore XML+PDF)
- `/app/backend/routers/fatture.py` (endpoints CRUD + jobs)
- `/app/backend/scheduled_jobs.py` (weekly/monthly cron)
- `/app/backend/models.py` (TerapistaProfileInput esteso)
- `/app/backend/server.py` (router registrato)
- `/app/frontend/src/pages/admin/FatturePage.jsx` (dual-role page)
- `/app/frontend/src/App.js` (nuove rotte /admin/fatture e /terapeuta/fatture)
- `/app/frontend/src/components/shared/Sidebar.jsx` (item "Fatture")

### ⚠️ Da verificare prima di produzione
- Validazione XML tramite uno dei tool ufficiali AdE ("Verifica Fatture" del portale Fatture&Corrispettivi)
- Test con commercialista italiano su almeno 1 fattura di prova
- Il terapeuta è responsabile della trasmissione al Sistema TS — istruzioni operative nell'email settimanale

### Backlog residuo dopo Fase 14
- **Fase 14b (P1)**: Frontend campo profilo terapeuta per regime_fiscale + codice_sdi + PEC + banner "Completa dati fiscali per emissione fatture"
- **Fase 14c (P2)**: Automatizzazione invio SdI (delega Agenzia Entrate + integrazione Fatture in Cloud o Aruba)
- **Fase 15 (P2)**: Sistema TS trasmissione automatica dopo delega
- **Fase 16 (P2)**: Registro Trattamenti art. 30 + DPIA (docs interni)

---

## ✅ FASE 14b — Profilo Terapeuta: Campi Fiscali Fatturazione (Feb 2026)

### Aggiunto al Profilo Terapeuta (/terapeuta/profilo)
- Nuova sezione **"Fatturazione elettronica"** dentro il card IBAN/Dati Bancari
- 3 nuovi campi:
  - **Regime fiscale** (select): forfettario / ordinario_esente / ordinario_iva / minimi (mappati a codice RF19/RF01/RF02)
  - **Codice SDI** (input 7 char alfanumerici uppercase auto-format)
  - **Indirizzo PEC** (input email lowercase auto-format)
- Badge arancione "⚠️ Da completare" mostrato in header quando dati mancanti
- Banner arancione con call-to-action quando manca regime fiscale OR (codice SDI vuoto/0000000 AND PEC vuota)
- Auto-hide del banner al completamento dati
- Salvataggio automatico tramite PUT `/api/terapisti/profilo/me` (usando `TerapistaProfileInput` esteso in models.py fase 14)

### Testing
- ✅ Backend PUT accetta i 3 nuovi campi (validato via curl)
- ✅ Frontend renderizza banner + badge + 3 form fields con data-testid completi (`fatt-elet-banner`, `fatt-elet-warning-badge`, `profilo-regime-fiscale`, `profilo-codice-sdi`, `profilo-pec`)
- ✅ Nessun lint error, screenshot conferma UX

### File modificati
- `/app/frontend/src/pages/therapist/TerapistaProfile.jsx` — form state + nuova sezione UI

---

## ✅ FASE 14c — Fluxo Fattura al Paziente (Feb 2026)

### Fluxo end-to-end
1. **Prenotazione + pagamento Stripe** → nessuna fattura ancora (acconto)
2. **Terapeuta marca seduta come "completato"** (o "cancellato_con_addebito") → hook automatico in `PATCH /appuntamenti/{id}/stato` genera fattura sanitaria FZ-YYYY-NNNN e invia email al paziente con PDF allegato
3. **Cancellazione con rimborso** (stato "cancellato") → nessuna fattura emessa

### Backend
- `routers/appuntamenti.py`: aggiunto stato "cancellato_con_addebito" alla whitelist e hook automatico per generazione fattura + email paziente (best-effort, non blocca l'update)
- `routers/fatture.py`: `GET /fatture/mine` ora fa switch role-based (terapeuta usa `terapeuta_user_id`, paziente usa `paziente_user_id`)
- Email al paziente via `send_signature_receipt_email` (riusata) con PDF fattura + testo educativo detrazione 730

### Frontend
- Rotta paziente `/paziente/fatture` → `FatturePage` con `isAdmin={false}`
- Banner verde **💚 "Detraibile al 730 come spesa sanitaria"** — spiegazione art. 15 TUIR con dettagli su Sistema TS e conservazione 5 anni
- Sidebar paziente: nuovo item **"Le mie fatture"** (icona Receipt)

### Testing manuale
- ✅ Creato appt di test, PATCH stato→completato genera FZ-2026-0002 (€90, marca bollo)
- ✅ GET /api/fatture/mine con cookie paziente ritorna 2 fatture
- ✅ Screenshot conferma UX: banner detrazione + tabella + KPI + download XML/PDF

### Backlog residuo dopo Fase 14c
- **P1**: Ricevuta di pagamento generica (non fiscale) via email al momento del pagamento Stripe
- **P1**: Export ZIP annuale con tutte le fatture del paziente per invio commercialista/730
- **P2**: Auto-completamento automatico degli appuntamenti passati (cron oraria che marca stato→completato se data_ora < now e ancora "confermato")
- **P2**: Validazione XML tramite tool ufficiale AdE "Verifica Fatture"


---

## ✅ FASE 15 — Firma Documenti Obbligatoria al Login (Feb 2026)

### Obiettivo
Prima di poter accedere a qualsiasi rotta terapeuta (`/terapeuta/*`), il terapeuta deve aver firmato TUTTI i documenti legali obbligatori (`contratto_collaborazione`, `privacy_terapeuti`, `termini_pazienti`, `cookie_policy`). Requisito GDPR Art. 28 (DPA) + eIDAS.

### Implementazione
- **Nuovo componente**: `/app/frontend/src/components/therapist/TherapistDocsGate.jsx`
  - Interroga `GET /api/contracts/pending/mine` all'ingresso e su ogni cambio di rotta
  - Se `pending.length > 0` → `Navigate replace` a `/terapeuta/firma-documenti`
  - Fail-open in caso di errore transitorio (non blocca l'utente per errori di rete)
- **App.js**: il layout terapeuta `/terapeuta` è ora avvolto da `<TherapistDocsGate>`. La rotta standalone `/terapeuta/firma-documenti` resta FUORI dal gate (altrimenti loop).
- **TerapistaDashboard.jsx**: rimosso il legacy `MandatoAcceptanceGate` (il `contratto_collaborazione` v1+ copre il contenuto del mandato all'incasso in forma più completa).

### Test manuale (Feb 2026)
- ✅ Terapeuta con doc pending: login → redirect automatico a `/terapeuta/firma-documenti`. Force navigation a `/terapeuta/calendario` → gate re-redirect. 
- ✅ Terapeuta dopo firma: login → `/terapeuta` accessibile. `/terapeuta/calendario` accessibile senza blocco.

### Backlog residuo
- **P1**: Invio SDI automatizzato (Fatture in Cloud / Aruba API) — attualmente XML per upload manuale
- **P2**: Registro Trattamenti art. 30 GDPR + DPIA art. 35 GDPR

---

## ✅ FASE 15b — Email Semanale Fatture Completa (Feb 2026)

### Obiettivo
Ogni domenica il terapeuta riceve UNA email con **PDF + XML FatturaPA di TUTTE le fatture della settimana** (sanitarie emesse ai pazienti + commissione B2B ricevuta da BIDOC), pronte per l'invio al commercialista e al SDI.

### Implementazione
- **Nuova funzione email**: `send_weekly_fatture_email` in `email_service.py` — template HTML branded con 2 tabelle (sanitarie + commissioni), accetta lista di attachments `{filename, content}`.
- **Job aggiornato**: `weekly_fatture_email` in `scheduled_jobs.py` — ora recupera fatture di ENTRAMBI i kind (`sanitaria` + `commissione`), scarica PDF+XML dall'Object Storage (fallback su `pdf_inline_b64`/`xml_inline_b64` inline), allega tutto.
- **Trigger**: cron domenica 20:00 UTC + manuale via `POST /api/admin/jobs/weekly-fatture/run`.

### Test manuale (Feb 2026)
- ✅ Trigger manuale del cron → email inviata a `demo.terapeuta@funzionabene.it` con **6 allegati** (3 fatture × PDF+XML = FZ-2026-0001, FZ-2026-0002, CM-2026-0001).
- ✅ Resend ID confermato in logs.

### Backlog residuo
- **P1**: Email mensile automatica ricevuta al terapeuta appena viene generata la fattura di commissione B2B del mese
- **P1**: Invio SDI automatizzato (Fatture in Cloud / Aruba API)
- **P2**: Export ZIP annuale con tutte le fatture per commercialista/730


---

## ✅ FASE 16 — Registro dei Trattamenti art. 30 GDPR (Feb 2026)

### Obiettivo
Pagina admin per gestire il Registro delle attività di trattamento ex art. 30 GDPR, con export PDF pronto per il Garante Privacy.

### Backend
- Nuovo router `/app/backend/routers/registro_trattamenti.py`:
  - `GET /api/admin/registro-trattamenti` — lista voci attive
  - `POST /api/admin/registro-trattamenti` — crea voce
  - `PUT /api/admin/registro-trattamenti/{id}` — modifica
  - `POST /api/admin/registro-trattamenti/{id}/archive` — archivia (soft delete)
  - `DELETE /api/admin/registro-trattamenti/{id}` — hard delete
  - `GET /api/admin/registro-trattamenti/export/pdf` — export PDF conforme
- Generatore PDF `/app/backend/registro_pdf.py` (ReportLab, formato A4 landscape, header con dati BIDOC, tabelle strutturate per voce)
- Seed automatico all'avvio (`_seed_registro_trattamenti`) con **10 voci di default** (T-01 → T-10) che coprono account/autenticazione, matching, anagrafe/fatturazione, albo terapisti, videoconsulto (responsabile), fatture commissione B2B, comunicazioni transazionali, marketing, statistiche, sicurezza.

### Frontend
- Nuova pagina admin `/admin/registro-trattamenti` (`RegistroTrattamentiPage.jsx`)
- Sidebar: nuova voce **"Registro Trattamenti"** (icona Shield)
- Lista con badge ruolo colorato, modal edit con tutti i campi GDPR art. 30, conferma archiviazione
- Bottone **"Esporta PDF"** in header

### Test manuale (Feb 2026)
- ✅ Seed inserisce 10 voci di default all'avvio
- ✅ Lista, edit modal e archive funzionanti (screenshot confermano)
- ✅ Export PDF genera 21.5 KB, 10 pagine (una per voce), conforme art. 30 GDPR verificato tramite `analyze_file_tool` (95% confidence)

### Backlog residuo
- **P1**: DPIA — Valutazione d'Impatto art. 35 GDPR (template guidato)
- **P1**: Email mensile automatica ricevuta al terapeuta per commissione B2B
- **P1**: Invio SDI automatizzato (Fatture in Cloud / Aruba)
- **P2**: Export ZIP annuale fatture per commercialista/730


---

## ✅ FASE 17 — Code Review Hardening (Feb 2026)

### Achados MEDIUM corrigidos (4/4)

**1. Backend signature gate (fail-closed)**
- Novo middleware HTTP em `server.py` → `therapist_signature_gate`
- Rejeita qualquer request `POST/PUT/PATCH/DELETE` de terapeuta sem docs firmados (excluindo allowlist: `/api/auth/`, `/api/contracts/`, `/api/legal-documents/`, `/api/upload/`)
- Retorna `403 {required_signature: true}`
- Fail-closed em erro de DB → retorna `503`
- Frontend `TherapistDocsGate` também mudou para fail-closed (bloqueia em erro de rede)

**2. Numerazione fatture race-safe**
- Índices únicos criados em startup: `numero`, `{appuntamento_id, kind}`, `{terapeuta, kind, anno, mese}`
- Numero allocado **após** validação anagrafica (reduz "queima" de numeri)
- Try/except `DuplicateKeyError` → em corrida, registra "burned number" e retorna a fattura pré-existente
- Nova coleção `fattura_burned_numbers` para audit trail fiscal

**3. Object Storage assíncrono**
- Todos `put_object`/`get_object` envolvidos em `asyncio.to_thread(...)` em `fatture.py` e `legal_signature.py`
- Backend não congela mais sob lentidão do storage

**4. HTML escape em PDF**
- Adicionado `escape()` (html) em todos os campos anagrafica cedente/cessionario em `fatture.py`
- Novo helper `_safe_html_block` para juntar linhas pré-escapadas
- Testado com "Via A&lt;B&gt;C" — PDF gera OK

### Achados LOW
- Duplicate fetch em `download_xml`/`download_pdf` → agora `_fetch_and_serve` retorna `(doc, bytes)` em uma única query
- Weekly email attachment cap: **NÃO endereçado** (backlog LOW)

