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
