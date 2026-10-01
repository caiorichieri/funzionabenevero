# CHANGELOG — funzionabene.it

## 2026-10-01 · Filigrana BIDOC su fatture PDF

Il logo cuore BD viene stampato come filigrana al centro di ogni pagina delle fatture generate dalla piattaforma — stesso trattamento per sanitaria TD01, nota di credito TD04 e commissione B2B.

### Implementazione
- `backend/assets/bidoc_watermark.png` — logo 2000×2000 versato nel repo (419 KB).
- `backend/fatturazione.py` — nuova funzione `_draw_watermark(canvas, doc)` registrata come callback `onFirstPage` + `onLaterPages` del `SimpleDocTemplate.build`.
  - Posizione: centro geometrico A4 → `((A4.width-16cm)/2, (A4.height-16cm)/2)`.
  - Dimensione: lato 16 cm, `preserveAspectRatio=True`.
  - Opacità: 10% (`canvas.setFillAlpha(0.10)`).
  - Trasparenza alpha: `mask="auto"` sul `drawImage` (il bianco dell'immagine si fonde col bianco carta, resta visibile solo il cuore BD).
  - Fail-silent se il PNG manca → nessuna rottura della pipeline fiscale.

### Verifica
- Suite regressione fiscal 9/9 PASS (test_iter35_fattura_email + test_fattura_auto_emit).
- Smoke test manuale: PDF reale generato (661 KB) + render PNG della prima pagina → cuore BD visibile centrale, intestazione/tabelle/Dati pagamento/nota bollo tutti leggibili sopra.

### Fuori scope
- XML FatturaPA invariato (SDI accetta solo testo strutturato, non immagini).
- Fatture già persistite non rigenerate: PDF antichi restano senza filigrana. "Reinvia" admin genera col nuovo layout.

---


## 2026-09-30 · Pulizia fatture sanitarie + WhatsApp number + admin ZIP export

Sette ritocchi indipendenti sul flusso Prenota subito e sulle fatture elettroniche sanitarie, più un nuovo strumento admin per l'esportazione massiva degli XML.

### 1. Numero WhatsApp `+39 333 711 6432`
Sostituito `+39 345 112 4503` in due file:
- `frontend/src/data/legalInfo.js` — `WHATSAPP_NUMBER`, `PHONE_DISPLAY`, `PHONE_E164`
- `frontend/src/components/public/PrenotaSubitoModal.jsx` — costante `WHATSAPP_NUMBER`

### 2 + 3. Nota bollo condizionata alla soglia €77,47 in `fatturazione.py::generate_pdf`
- Sotto €77,47: **"Prestazione sanitaria esente IVA... Imposta di bollo non dovuta ai sensi dell'art. 13 della Tariffa, Parte I, allegata al DPR 642/1972, in quanto l'importo non supera euro 77,47."**
- Sopra €77,47: testo esistente invariato (esenzione IVA + marca da bollo €2 assolta ove applicabile).
- Riga "Marca da bollo €2 a carico del prestatore" nei totali resta condizionale al bollo dovuto (era già così).

### 4 + 5. Descrizione riga = "Prestazione psicologica" + rimozione blocco "Causale:"
- `routers/fatture.py::_generate_fattura_paziente`: introdotta variabile `descrizione = "Prestazione psicologica"` (statica, senza data). La data del pagamento resta nel blocco DatiPagamento e nella data di emissione.
- `causale` passato come `None` al dict PDF → il blocco "Causale: …" a fine PDF non viene renderizzato (guard `if fattura.get("causale")` già esistente).
- `generate_xml_sanitaria` accetta ora un parametro opzionale `descrizione: str = None`; se assente ricade su `causale` per retrocompatibilità con NC/commissioni. Quando `causale=None`, il tag `<Causale>` non viene aggiunto all'XML — `<Causale>` è opzionale in TD01 v1.2.2.

### 6. Blocco "Dati pagamento" in PDF + `DatiPagamento` in XML
- Nuovo blocco compatto sopra i totali del PDF: "Metodo: Carta di credito (Stripe)" + "N. operazione: pi_...".
- `_build_body` aggiunge `<DatiPagamento>` con `<CondizioniPagamento>TP02</CondizioniPagamento>` + `<ModalitaPagamento>MP08</ModalitaPagamento>` (carta) + `<DataScadenzaPagamento>` + `<ImportoPagamento>` quando la fattura è pagata via Stripe.
- Fonte dei dati: `db.payment_transactions` cercata in `_generate_fattura_paziente` — `stripe_payment_intent_id` come N. operazione, `paid_at` come data pagamento. Graceful degradation: se la transazione manca (fatture pre-Stripe, pagamenti manuali) mostra solo il metodo omettendo il N. operazione.

### 7. Export ZIP XML per terapeuta + intervallo (admin)
- `GET /api/admin/fatture/terapeuti-with-invoices` — dropdown source: terapisti con almeno una fattura emessa.
- `GET /api/admin/fatture/export-zip?terapeuta_user_id=X&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD&include_nc=true` — ZIP in memoria con tutti gli XML sanitaria + (opzionale) sanitaria_nc + nota_credito_sanitaria del terapeuta nel range. Filename: `fatture-{cognome-nome}-{from}-{to}.zip`. Commissioni B2B escluse (non parte del cassetto fiscale del terapeuta come emittente).
- Frontend `pages/admin/FatturePage.jsx` — nuovo box "Esporta XML in blocco" sopra la lista con dropdown + date + toggle "Includi note di credito" + bottone "Esporta XML in ZIP".

### File toccati
- `frontend/src/data/legalInfo.js`
- `frontend/src/components/public/PrenotaSubitoModal.jsx`
- `frontend/src/pages/admin/FatturePage.jsx`
- `backend/fatturazione.py`
- `backend/routers/fatture.py`

### Test status
- Suite fiscal esistente 13/13 PASS (test_iter35_fattura_email, test_fattura_auto_emit)
- Smoke test manuale generatore: XML sotto/sopra soglia validato — no `<Causale>`, no `<DatiBollo>` sotto, `<DatiBollo>` presente sopra, `<ModalitaPagamento>MP08</ModalitaPagamento>` in entrambi
- Export ZIP curl-testato con terapeuta reale: 200 OK, file ZIP valido con `FZ-2026-0084.xml` all'interno
- Screenshot admin/fatture: box "Esporta XML in blocco" visibile in cima alla pagina con testids corretti

### Fuori scope (esplicitamente rimandato)
- Webhook Stripe che fallisce dal 21/09: notifica email dell'utente citata ma non gestita in questa release. Va ripreso separatamente prima del 30/09/2026 (data in cui Stripe disattiva l'endpoint).

---


## 2026-09-24 · Fix "Prenota subito" mobile-vs-desktop + cleanup terapeuti demo + SMS/videocall live

**Segnalazioni utente**:
1. Cliccando "Prenota subito" dal telefonino non vede orari, dal desktop sì.
2. Video call: il link magico apriva, chiedeva permesso camera, ma restava bloccato su "Apertura della stanza video…".
3. SMS reminder non partivano (`error 21704 — messaging service has no phone number for this destination country`).

### Fix 1 — PrenotaSubitoModal random empty

**Root cause**: `PrenotaSubitoModal` prendeva sempre `terapisti[0]` dalla `/api/public/terapisti`. La query `db.terapisti.find({...})` senza `.sort()` restituiva documenti in "natural order" MongoDB → l'ordine cambiava tra chiamate. Se il primo era un utente demo/test senza agenda ("Giulia T", ecc.), il modal mostrava "nessun orario disponibile" pur essendoci altri terapisti con slot pieni.

Aggravante: in preview c'erano 9 terapisti seed/test misti a quelli reali; in produzione c'era già solo Laura De Clara ma il bug si manifestava per **cache stale del PWA** che serviva un bundle JS precedente al momento in cui Laura aveva popolato l'agenda.

**Fix**:
- `server.py` — `/api/public/terapisti`, `/api/public/terapisti/{tid}`, `/api/public/matching` ora filtrano `is_test != True` e usano `.sort([("priority", -1), ("cognome", 1), ("nome", 1)])`.
- `routers/terapisti.py` — estratta helper `_compute_terapista_slots(terapista, terapista_id, start, end, min_slot_time, durata)` riusata da:
  - `GET /api/terapisti/{id}/slots` (esistente, refactored)
  - `GET /api/public/next-slots?limit=3&settimane=2` **NUOVO**: aggrega slot di TUTTI i terapisti verificati (non-test), dedupe per `(terapeuta_id, day)` così ogni riga del modal è un'opzione realmente diversa, embed di `terapeuta_id/nome/cognome/prezzo_sessione` per riga.
- `PrenotaSubitoModal.jsx` — passa a `/public/next-slots`, ogni riga mostra "alle ore HH:MM · con Dr. {nome} {cognome} · €{prezzo}". `handleConfirm` deconstructiona il terapista dallo slot stesso.
- `public/sw.js` — `CACHE_NAME` `funzionabene-v1` → `funzionabene-v2` per forzare l'invalidazione dei bundle stale su tutti i PWA già installati.

### Fix 2 — Video call bloccata dopo permesso camera

**Root cause combinato**:
1. `VideoCallPage.jsx` passava `border: "rgba(255,255,255,0.08)"` nel theme del Daily iframe; Daily.co accetta solo colori HEX → lanciava errore intercettato genericamente come "Impossibile entrare nella stanza".
2. React 18 `StrictMode` invoca `useEffect` due volte in dev; il secondo `DailyIframe.createFrame` veniva rifiutato con "multiple call instances", exception capturata di nuovo come "Impossibile entrare".
3. `frame.join().then(() => setLoading(false))` non risolveva la Promise quando la prima istanza veniva distrutta mid-flight, così lo spinner "Apertura della stanza video…" restava indefinitamente anche a permesso camera concesso.

**Fix in `VideoCallPage.jsx`**:
- `theme.colors.border` e `supportiveText` passati a valori HEX validi (`#1F2937`, `#B8B4A8`).
- `DailyIframe.createFrame(..., { allowMultipleCallInstances: true })` — workaround ufficiale Daily.co per React StrictMode.
- Rimpiazzato `frame.join().then()` con handler basati su eventi Daily: `joined-meeting`, `loading`, `loaded` chiudono lo spinner; `error` mostra il messaggio reale; `frame.join(...).catch(...)` intercetta il fallimento della Promise stessa.

### Fix 3 — SMS reminder + smoke test end-to-end

**Root cause**: Twilio Messaging Service "FunzionaBene Reminders" era vuoto (0 numeri, 0 alpha sender). L'errore 21704 significa "Messaging Service ha nessun mittente per il paese di destinazione (IT)".

**Fix**: utente ha registrato l'alpha sender **`Funzbene`** nel pool del service tramite Twilio Console. SMS reminder ora parte con From = `Funzbene`; Twilio ha risposto `status=sent`.

**Verifica live**:
- OTP (Twilio Verify) → **delivered**
- Reminder da alpha sender `Funzbene` → **sent** al `+393518230667`
- Video call E2E mobile: sessione fake creata `_id=6ab45f290ac2fa69453418d2` con room Daily `funzionabene.daily.co/appuntamento-6ab45f290ac2fa69453418d2` — utente ha confermato "deu certo" dopo il fix.

### Data hygiene preview

Marcati come `is_test: true` in preview DB: 5 terapisti chiaramente test (Giulia T, Test User, Foto Tester, Mario Rossi, Maria Rossi). I 4 seed corporativi (Alessandro Conti, Chiara Esposito, Marco Fontana, Giulia Marchetti) confermati come seed dopo evidenze (tutti creati in 1 secondo, `telefono_verificato=None`, `documenti_count=0`) — l'utente ha confermato che l'unica terapeuta reale è **Laura De Clara** (già presente solo in prod). Flag `is_test` rimosso su preview per non rompere i test di regressione; il filtro nell'API resta.

### File toccati
- `backend/server.py`
- `backend/routers/terapisti.py`
- `frontend/src/components/public/PrenotaSubitoModal.jsx`
- `frontend/src/pages/VideoCallPage.jsx`
- `frontend/public/sw.js`

### Test status
- Suite `test_slots_endpoint::TestSlots` → PASS dopo il refactor
- `_compute_terapista_slots` verificata via curl sul preview: 3 slot diversificati con nomi terapeuti embedded
- Video call reproducibile su Playwright viewport mobile → Daily.co iframe entra in preview + partecipa
- SMS reminder → Twilio `messages.list` conferma `status=sent` con `from=Funzbene`

### Deploy
Deploy pipeline lanciata: job_id `d3dd1dcd-4cc8-41e3-9745-1d6a5a432b7b`. In produzione basta che Laura De Clara abbia slot popolati (già così, 28 disponibili) e il fix è live sia mobile che desktop.

---


## 2026-09-22 · Fix fattura FZ-2026-0004 non recapitata + email brandizzata

**Segnalazione**: fattura FZ-2026-0004 emessa e visibile in "Le mie fatture" del paziente, ma **non arrivata via email**.

**Root cause**: tutti i callsite di invio riusavano `send_signature_receipt_email` (template per ricevute firma documenti legali). Anche se l'email arrivava:
- Soggetto: "Ricevuta di sottoscrizione — Funzionabene" (zero parole "fattura").
- Allegato: `ricevuta_sottoscrizione.pdf` (non riconoscibile).
- Corpo: parla di hash SHA-256, firma digitale, timestamp UTC.

Il paziente l'ha ignorata pensando fosse un documento legale già gestito. Inoltre, in caso di storage-fetch fail, l'email partiva senza allegato e senza CTA per scaricare dalla dashboard.

**Fix**:
- **Nuova funzione `send_fattura_paziente_email`** in `email_service.py`:
  - Soggetto: `Fattura {NUMERO} per la tua seduta con Dr. {COGNOME}`.
  - Reply-To: `info@funzionabene.it`. From: `noreply@funzionabene.it` (invariato — dominio Resend verificato).
  - Allegato: `Fattura_{NUMERO}.pdf`.
  - Corpo brandizzato: blocco riepilogo (numero, importo, data emissione, causale) + nota fiscale detraibilità 19% + pulsante "Scarica dalla tua area" → `/paziente/fatture`.
  - Fallback: se `pdf_bytes` vuoto, email parte comunque SENZA allegato ma con dashboard CTA visibile.
  - Ritorna tuple `(ok, error_msg)` per surfacing errori in diagnostica admin.
- **Callsite aggiornati** (5): `_emit_fattura_for_paid_tx` (webhook Stripe), `admin_generate_missing_fatture`, `admin_retry_fattura`, `admin_reinvia_fattura`, boot migration in `server.py`. Ciascuno enriquisce ora `terapeuta_cognome` e `data_seduta_iso` per il template.
- **`admin_reinvia_fattura` bypassa il flag `email_sent_at`**: click esplicito admin → sempre eseguito. Su success pulisce `email_error` e `payment_transactions.fattura_error/step`. Nota di credito continua a usare `send_signature_receipt_email` (template diverso corretto).
- **Error tracking granulare**: `payment_transactions.fattura_error_step` scritto come `fetch_pdf` (storage fail) o `send_email` (Resend fail) → banner diagnostica admin distingue le due cause. Se storage fallisce ma email va comunque (senza allegato), `fetch_pdf` viene ancora persistito così l'admin può fare Reinvia con un fresh storage fetch.

**Test regression (8/8 nuovi + 71/74 regression)**:
- `tests/test_iter35_fattura_email.py`: subject/reply_to/filename shape, fallback pdf vuoto, guard "NON usa signature_receipt", fetch_pdf persistence in due scenari (email OK vs email fail), reinvia bypass, NC preserva template signature-receipt.
- 3 test flake pre-existing (motor+asyncio.run cross-module) non correlati.

**Piano operativo post-deploy**: dal pannello admin Fatture → riga FZ-2026-0004 → "Reinvia". Con nuovo template + logging verbose il paziente riceverà (a) l'email con soggetto "Fattura FZ-2026-0004 per la tua seduta con Dr. De Clara", (b) allegato `Fattura_FZ-2026-0004.pdf`, (c) fallback dashboard CTA se lo storage rifiuta. Se qualcosa ancora fallisce, `fattura_error_step` diagnostica dice esattamente dove.


## 2026-09-22 · Bug fix duplo · videocall magic link + reminder scheduling

### 🔴 Bug A · `/api/videocall-magic/{id}` 500 quando `videocall_magic_expires` era string
**Root cause**: alcuni record avevano `videocall_magic_expires` scritto come stringa (via `.isoformat()`) invece che BSON datetime. Il gate faceva `.tzinfo` diretto sulla stringa → `AttributeError` → 500.

**Fix** in `routers/appuntamenti.py`:
- Nuovo helper `_parse_stored_datetime(val)` che accetta sia `datetime` che stringa ISO, ritorna aware-UTC o None.
- La finestra del magic link è stata **estesa** da `start+15min` a `start+durata+15min` — coincide col logged-in join window, permette re-join dopo disconnessione via email link. Il no-show cutoff a `start+15min` rimane responsabilità del scheduled job (marca stato + email) e NON blocca più l'ingresso.
- `booking_service::_ensure_videocall_magic_token` ora scrive `magic_expires = start + durata + 15 min`.

### 🔴 Bug B · Reminder scattavano off-time (data_ora naive interpretata come UTC)
**Root cause**: `schedule_reminders` faceva `datetime.fromisoformat(data_ora).replace(tzinfo=UTC)` sui valori naive. Vecchi record naive-Rome venivano interpretati come UTC → reminder scattavano 2h fuori durante CEST.

**Fix** in `booking_service.py`:
- Naive strings ora sono interpretate come `Europe/Rome` (fuso fiscale di record), normalizzate a UTC per APScheduler.
- Nuovi helper: `_reminder_job_ids(app_id)` (centralizza il namespace), `cancel_scheduled_jobs(app_id)` (rimuove tutti i job di un appt), `reschedule_reminders(old_id, new_id, ctx)` (cancel + fresh schedule).
- `routers/calendario.py::confirm_reschedule` ora chiama `reschedule_reminders` dopo l'insert del nuovo appt → reminder + no-show jobs migrano dal vecchio id namespace al nuovo, col nuovo orario. Prima, i job leakavano nel vecchio id e scattavano sullo slot originale.

### Test regression (13/13 nuovi PASS + 55/56 precedenti)
- `tests/test_iter34_magic_link_and_reschedule.py`: gate string/datetime, finestre 425/410, idempotency scheduler, cancel + reschedule flow.
- 1 test flake pre-existing (event-loop cross-module isolation) — non causato da iter34, passa in isolamento.

### Minor code review carry-over (backlog)
- `deps.db` motor client bound al primo pytest loop → cross-module flake. Considerare lazy accessor.
- `no_show_service.schedule_no_show_check` fa parsing indipendente — se chiamato con naive-Rome esternamente potrebbe misinterpretare. Solo caller in-tree è `schedule_reminders` (ora pre-normalizza), quindi latente.


## 2026-09-22 · Code review d367edc9 · 3 defetti HIGH/MEDIUM fixed (56/56 PASS)

### 🔴 H1 · IDOR nella modifica stato appuntamento
**Prima**: `PATCH /api/appuntamenti/{id}/stato`, `PUT` e `POST` accettavano qualsiasi utente autenticato → un paziente A poteva cancellare/completare l'appuntamento del paziente B, disparando fattura sanitaria automatica per la vittima.

**Fix** in `routers/appuntamenti.py`:
- Nuovo helper `_load_appt_or_404` + `_assert_can_manage_appt` con ownership check per role:
  - admin: bypass.
  - paziente: `appt.paziente_user_id == user._id`.
  - terapeuta: `appt.terapeuta_user_id == user._id` + fallback su `terapisti.user_id` via `terapeuta_id` (per appt legacy).
- `PATCH` blocca anche pazienti/terapeuti dal forzare `completato`/`cancellato_con_addebito` (solo admin, per evitare fattura emission fuori controllo).
- `POST /appuntamenti` ora richiede `require_admin` (i booking dei pazienti passano da `/payments/checkout/booking` che stamppa correttamente i field di ownership).

### 🔴 H2 · Fatture di commissione mensile omettevano sessioni attese
**Prima**: aggregazione mensile contava solo `stato in ['completato','confermato']`. Il job no-show marca `in_corso` quando entrambi entrano → **queste sessioni non erano fatturate come commissione BIDOC 30%**.

**Fix** in `routers/fatture.py`:
- Nuovo constant module-level `PAID_APPT_STATES` = `['completato','confermato','in_corso','no_show_paziente','no_show_terapeuta','no_show_entrambi','cancellato_con_addebito']`.
- Riusato in: `_generate_fatture_commissione_mensile`, `/admin/fatture/diagnostics`, `/admin/fatture/generate-missing`, boot backfill in `server.py`.
- Rimborsi transitano `cancellato` via refund side-effects → automaticamente esclusi.

### 🟡 M1 · Refund direto no Stripe dashboard lasciava appuntamento orfano + no NC
**Prima**: webhook `charge.refunded` flipava solo `payment_status`. Se admin rimborsava dal dashboard Stripe (non via `/admin/refunds`), l'appuntamento restava `confermato` (room + reminders attivi) e la Nota di Credito TD04 non veniva emessa.

**Fix** in `routers/payments.py`:
- Extract di `_apply_refund_side_effects(tx, admin_note, motivo_nc)` che: (1) cancella appt (guarded con `$nin`), (2) emette NC TD04 (idempotente via unique guard su `fattura_originale_id + kind`), (3) email NC PDF al paziente (best-effort).
- Webhook `charge.refunded` ora è idempotente (guard `payment_status: {$ne: 'refunded'}`) e chiama lo stesso helper.
- Endpoint `/admin/refunds` refattorizzato per usare lo stesso helper (DRY).
- Fixed drift: `nc_info` nel response ora legge kind con `$in: ['nota_credito','nota_credito_sanitaria']` (era null in precedenza).

### Test regression (56/56 PASS)
- `tests/test_iter33_authz_commission_refund.py` (nuovo): 18 test coprono H1 (11), H2 (4), M1 (2), constant shape.
- Precedenti: 38/38 (fattura auto-emit + retry, no-show + video gating, Rome-TZ slots).

### Backlog code review (aperto)
- 4 LOW dal code review: N+1 in `/admin/seduta-logs` (limit 500), docstring magic-link, dead code `admin_gen_nota_credito`, weak participant name matching in no_show_service.
- 55 hook-deps residui + refactor componenti giganti + complessità cyclomatiche.


## 2026-09-22 · Code review d367edc9 · Batch 1 hook-deps (6/61 file)

Applicato fix mirati a **6 file di priorità 1** dal report — user-facing critici. I 55 hook-deps rimanenti + refactor componenti giganti (900+ righe) restano in backlog per iterazioni dedicate.

**Fatto**:
- `TerapistaProfile.jsx:72` — `useCallback fetchProfilo` deps `[]` → `[API]`.
- `TerapistaDashboard.jsx:40` — `useCallback fetchData` deps `[]` → `[API]`.
- `TerapistaCalendarioPage.jsx:48` — `useCallback fetchCal` deps `[]` → `[API]`.
- `PazienteHome.jsx:49` — `useEffect` deps `[]` → `[API]`.
- `RegistroTrattamentiPage.jsx:53` — `useCallback load` deps `[]` → `[API]`.
- `routes.js:159` — `StandaloneRedirector useEffect` deps `[..., user]` → `[..., user?.role]` (più stabile — user object può cambiare a ogni re-fetch, role no).

**Perché sicuri**: `API` viene da `AuthContext` ed è una stringa costante durante il lifetime dell'app (deriva da `REACT_APP_BACKEND_URL`). Aggiungerlo alle deps NON causa re-run indesiderati.

**Verificato (iter31)**:
- Backend regression 38/38 PASS (fattura, no-show, timezone).
- Ogni pagina flaggata monta e spara la chiamata API esattamente 2 volte (React StrictMode dev, atteso).
- Zero React warnings su console (nessun exhaustive-deps, nessun duplicate-key).
- Nessun redirect loop su StandaloneRedirector.

**Test-env side effect**: `backend/.env` ha ora `SEED_DEMO_DATA="true"` per abilitare demo.terapeuta/paziente in preview (utile per prossimi testing agent). NON influisce sulla produzione.

**Backlog code review (aperto)**:
- 55 hook-deps rimanenti — a batch di 5-10 per volta con smoke test per modulo.
- Refactor `TerapistiPage.jsx` 899 righe, `TerapistaProfile.jsx` 553, `BlogPage.jsx` 458, `FatturePage.jsx` 411.
- `BlogSeoAnalyzer.analyze()` complessità 63 — da splittare per metrica SEO.
- `OnboardingSection.jsx` complessità 28 — da splittare per wizard step.
- Backend: `cruscotto_pdf.build_cruscotto_pdf()` 151 righe, `_build_common_header()` ciclomatica 14, `_emit_snapshot()` ciclomatica 15.
- 28 possibili variabili Python non definite — richiede lista puntuale.


## 2026-09-22 · Code review triage — fix mirati alto-valore/basso-rischio

Applicato solo i fix reali dalla code review, evitando refactor massivi che avrebbero introdotto rischio di regressione sui flussi appena stabilizzati (fattura, no-show, timezone).

**Fatto**:
- `SedutaLogsSection.jsx:141` — chiave lista partecipanti da `key={i}` → `${user_name}-${join_time || i}`.
- `PrivacyUtentePage.jsx:184` — chiave storico consensi da `key={idx}` → `${timestamp}-${consent_type}-${action}`.
- `FirmaDocumentiPage.jsx`, `ContrattiPage.jsx` (×2), `MandatoAcceptanceGate.jsx`, `utils/safeHtml.js` — aggiunto commento `// eslint-disable-next-line react/no-danger` documentando che `dangerouslySetInnerHTML` passa **sempre** attraverso `sanitizeHtml()` (DOMPurify). Questi 5 falsi positivi del linter erano già sicuri.

**In backlog, NON toccato in questo iter** (rischio regressione alto/rendimento incerto):
- 61 hook-deps warnings — da fare a lotti di 5-10 per modulo.
- 28 possible undefined vars in Python — richiede lista puntuale.
- Refactor componenti giganti: `TerapistiPage.jsx` 899 righe, `TerapistaProfile.jsx` 553, `BlogSeoAnalyzer.jsx` complessità 63.
- Refactor `cruscotto_pdf.build_cruscotto_pdf()` 151 righe, `email_service.send_weekly_fatture_email()` 83 righe.
- Split di `routers/terapisti.py` (963 righe) in moduli distinti.

**Test regression (38/38 backend PASS, 3/5 frontend smoke)**: fattura auto-emit, fattura retry, no-show + video gating, Rome-TZ slots.

**Falsi positivi documentati** dal code review:
- Test-only "hardcoded secrets" (`"TESTTOKEN12345"`, `"TestPass123!"`) — placeholder pytest, non secret veri.
- `dangerouslySetInnerHTML` (×5) — tutti già sanitizzati con DOMPurify.


## 2026-09-22 · P0 · Bug orario email + email pubbliche consolidate

### Bug — orario nell'email di conferma sbagliato di 2h
**Root cause**: `GET /api/terapisti/{id}/slots` (usato da `TerapistaPublicPage` e `PrenotaSubitoModal`) interpretava le stringhe `HH:MM` salvate in `terapisti.disponibilita_calendario` come UTC anziché Rome-local. Il terapista digita "16:00" pensando 16:00 italiane, l'endpoint restituiva `2026-09-22T16:00:00+00:00` = 16:00 UTC = 18:00 Roma (CEST). Il paziente sceglieva credendolo alle 16:00 (frontend converte), pagava, e l'email arrivava con l'orario di 18:00.

**Fix**: nuovo helper `_rome_hhmm_to_utc(day_utc, hh, mm)` in `routers/terapisti.py` che costruisce il datetime in `ZoneInfo("Europe/Rome")` e chiama `.astimezone(UTC)`. DST gestito nativamente (CEST=UTC+2 in estate, CET=UTC+1 in inverno).

**Applicato a**: ramo `disponibilita_calendario` (date-specific) e fallback `disponibilita` (weekly recurring).

**Test regression (11/11 PASS)** in `/app/backend/tests/test_slots_rome_tz_fix.py`:
- 16:00 Rome CEST → 14:00 UTC ✓
- 16:00 Rome CET → 15:00 UTC ✓
- Weekly fallback conversion ✓
- Email formatters (`_format_data_ora_it`, `_fmt_it`) invariati ✓
- Daily.co token nbf/exp arithmetic ✓

### Email pubbliche consolidate
Ridotto 3 caselle → 1 (`info@funzionabene.it`). File toccati:
- `ContattiPage.jsx`: supporto@ / professionisti@ / stampa@ → info@funzionabene.it (3 sezioni).
- `LavoraConNoiPage.jsx`: 4 occorrenze di professionisti@ → info@funzionabene.it.

Mantenuti (come richiesto): `info@bidoc.it`, `privacy@bidoc.it`. Non toccato `assistenza@funzionabene.it` (già usato solo in template email interni).


## 2026-09-22 — Feature P0: Sessione video — accesso, no-show, log presenze
Bug reportato: (1) email "15 min prima" arriva puntuale ma il link "sembra aprire ma non apre" all'orario esatto di inizio; (2) pulsante "Entra" del paziente sparisce esattamente allo scoccare dell'ora; (3) dashboard terapeuta non mostra mai il pulsante "Entra"; (4) nessun rilevamento automatico di no-show; (5) log presenze consultabili solo via query live a Daily.co.

### Backend
- **`daily_service.py`** — `nbf` di stanza + token spostato a `start − 20 min` (era 15) per assorbire scarti di orologio e tempi di consegna email.
- **`booking_service.py::_ensure_videocall_magic_token`** — `videocall_magic_expires = start + 15 min` (era `start + durata + 15`). Coincide col cut-off no-show.
- **`routers/appuntamenti.py`** — nuovi gate temporali:
  - `POST /appuntamenti/{id}/video-token` (utente loggato) → HTTP **425** `{code:'too_early', available_at, start_at}` se `now < start-20min`, HTTP **410** `{code:'session_closed'}` se `now > start + durata + 15`. Loggati possono rientrare fino a fine seduta.
  - `GET /videocall-magic/{id}?token=X` → 425/410 con `role_hint:'paziente'`. Chiuso al no-show cut-off.
- **`no_show_service.py`** (nuovo) — `run_no_show_check(app_id, is_final)`:
  - Interroga Daily.co per partecipanti effettivi.
  - Calcola esito: `entrambi_presenti` / `no_show_paziente` / `no_show_terapeuta` / `no_show_entrambi`.
  - Persiste snapshot in `db.seduta_logs` (upsert per `appuntamento_id`).
  - Marca `appuntamenti.stato` + `outcome` (non sovrascrive stati manuali).
  - Idempotente sul dispatch email (`no_show_notified_at` guard).
  - `schedule_no_show_check(scheduler, id, start_iso, durata)` registra 3 job APScheduler: `final` (start+15min, invia email), `post` (start+durata+15, aggiorna log), `24h` (log finale).
- **`booking_service.py::schedule_reminders`** — chiama `schedule_no_show_check` in coda ai reminder esistenti.
- **`email_service.py`** — 5 nuovi template:
  - `send_no_show_paziente_email` — paziente assente, CTA "prenota un'altra seduta" sul profilo dello stesso terapista.
  - `send_no_show_terapeuta_email` — informa il terapista dell'assenza del paziente.
  - `send_terapeuta_absent_paziente_email` — scusa a nome della piattaforma + CTA rebook.
  - `send_terapeuta_absent_terapeuta_email` — chiede al terapista di scrivere a `hr@funzionabene.it`.
  - `send_no_show_admin_alert` — email interna a `hr@funzionabene.it` per ogni no-show.
- **Endpoint admin nuovi/estesi**:
  - `GET /admin/seduta-logs?outcome=&from_date=&to_date=&terapeuta_id=` — lista paginata dei log.
  - `GET /appuntamenti/{id}/presenze` — preferisce lo snapshot durevole in `seduta_logs`, fallback a query live Daily.

### Frontend
- **`VideoCallPage.jsx`** (rewrite) — gestisce le 3 risposte del backend:
  - 200 → apre iframe Daily.co come prima.
  - 425 → mostra countdown MM:SS a `available_at` + retry manuale + auto-retry al termine.
  - 410 → messaggio "finestra chiusa" + CTA differenziato: paziente vede "Prenota un'altra seduta"; terapeuta vede "Scrivi a hr@funzionabene.it".
- **`PazienteDashboard.jsx`** + **`TerapistaDashboard.jsx`** — filtro `isStillActive` tiene l'appuntamento nella lista fino a `start + 15 min`; `canJoin` ristretto a `[start-15, start+15]` (era `[start-15, end+15]`). Fix del pulsante che spariva allo scoccare dell'ora.
- **`PazienteHome.jsx`** (PWA) — stessa finestra `[start-15, start+15]`; card "prossima seduta" rimane visibile fino a start+15.
- **`SedutaLogsSection.jsx`** (nuovo) — vista admin in `AppuntamentiPage` con filtri esito/periodo, snapshot Daily.co dei partecipanti, espansione per riga.

### Test regression (18/18 PASS)
- `/app/backend/tests/test_no_show_and_video_gating.py` (nuovo): copre 425/410 su entrambi endpoint, nbf a 20 min, no-show detection idempotency, filtri admin/seduta-logs + permessi 403, preferenza snapshot su live, fallback SEND_EMAILS=false.

### Note operative
- Rimborsi: **nessuna decisione automatica**. Un no-show marca solo l'appuntamento ed emette alert a hr@. Il rimborso resta scelta umana dal pannello admin.
- Retention: i `seduta_logs` non hanno scadenza (rimangono insieme all'appuntamento).
- Registrazione video/audio: **NON attivata**. Solo metadati di presenza (chi/quando/quanto).


## 2026-09-21 — Bug fix P0: Fattura sanitaria non generata dopo pagamento reale
Reproduzione: pagamento Stripe reale, appuntamento confermato, email di conferma inviata, ma nessuna fattura generata. Admin vedeva "1 pagamento senza fattura"; paziente non riceveva PDF né vedeva fattura nel proprio dashboard.

### Root cause
Gli appuntamenti creati da `/payments/checkout/booking` scrivevano solo `terapeuta_id` (→ `terapisti._id`); mai `terapeuta_user_id` (→ `users._id`). Il generatore fattura leggeva `appt.terapeuta_user_id` → `None` → `_get_terapeuta_full(None)` → `None` → `ValueError("Terapeuta non trovato")` → catturato silenziosamente nel try/except del webhook.

### Fix (verificato con 9 test regression)
- **`routers/fatture.py::_resolve_terapeuta_user_id`** — nuovo helper che risolve `terapeuta_user_id` da `terapisti._id` come fallback, e fa backfill sull'appuntamento.
- **`routers/fatture.py::_generate_fattura_paziente`** — usa il resolver + fallback a `terapeuta.prezzo_sessione` se `appt.prezzo` è mancante.
- **`routers/payments.py::create_booking_checkout`** — ora scrive `terapeuta_user_id` + `prezzo` sull'appuntamento alla creazione, così i nuovi flussi non ricadono mai nel bug.
- **`routers/payments.py::_emit_fattura_for_paid_tx`** — nuovo helper step-by-step (generate → email) che persiste su `payment_transactions` sia il successo (`fattura_id`, `fattura_numero`, `fattura_emessa_at`, `fattura_sanitaria_status=emessa`) sia il fallimento per passo (`fattura_error`, `fattura_error_step`, `fattura_error_at`). Il webhook Stripe non fallisce mai per errori di fattura.
- **`routers/fatture.py`** — endpoint `POST /admin/fatture/retry/{appuntamento_id}` per retry per-riga (genera fattura + invia email + aggiorna stato tx). L'endpoint `/admin/fatture/generate-missing` ora invia anche email + persiste stato di errore.
- **`server.py`** — la migration di boot per fatture mancanti ora invia anche il PDF via email e persiste lo stato di errore quando fallisce.
- **`routers/fatture.py::admin_fatture_diagnostics`** — la lista `missing[]` include `last_error` + `last_error_step` per ogni riga, così l'admin vede il motivo del fallimento senza aprire i log.
- **Frontend `FatturePage.jsx`** — banner rosso mostra fino a 10 righe, ognuna con errore fiscale + pulsante **"Riprova"** che chiama `/admin/fatture/retry/{id}`.

### Test regression
- `/app/backend/tests/test_fattura_auto_emit.py` — resolver + backfill + idempotency (production-shape appointment).
- `/app/backend/tests/test_fattura_retry_flow.py` — end-to-end diagnostics + retry endpoint (creato dal testing agent).
- `/app/backend/tests/conftest.py` — carica `backend/.env` per MONGO_URL.
- Risultato: **9/9 test PASS**.

### Note operative
- Al prossimo deploy, la migration boot rigenererà automaticamente la fattura per il pagamento di Silvia Drigo (21/09/2026) e le invierà il PDF via email.
- Se serve invio manuale immediato in produzione: `POST /api/admin/fatture/retry/{appuntamento_id}` (ora disponibile in UI come "Riprova" sulla riga del banner rosso).


## 2026-02 — Feature: Diagnostica + Rigenerazione Note di Credito (P0)
Bug in produzione: dopo un refund Stripe, il paziente NON riceveva la Nota di Credito. La generazione della NC nel flusso di rimborso poteva fallire silenziosamente.

### Backend — nuovi endpoint
- `GET /admin/fatture/diagnostics` (esteso): ora include anche `missing_nc_count` + lista `missing_nc[]` con i rimborsi che non hanno la corrispondente NC.
- `POST /admin/fatture/generate-missing-nc` — genera automaticamente le NC per tutti i rimborsi orfani + invia il PDF al paziente via email. Ritorna i successi + gli errori con motivo.
- **Migrazione idempotente al boot** (`seed_data`): auto-recupera le NC mancanti per rimborsi precedenti al prossimo deploy.

### Frontend — banner ambrato in `/admin/fatture`
- Nuovo banner ambrato (accanto a quello rosso delle fatture mancanti) che elenca fino a 5 rimborsi senza NC e ha il pulsante **"Genera N note di credito mancanti"**.
- Toast di conferma con conteggio successi/errori + prima causa d'errore visibile.

- **Test E2E**: preview → `missing_nc_count: 0`. Endpoint funzionante.



## 2026-02 — Feature: Diagnostica + Genera Fatture Mancanti (P0)
Bug in produzione: pagamenti/storni fatti prima del deploy della funzionalità "fattura al pagamento" **non hanno generato fattura**, e l'admin non aveva modo di vederli o recuperarli.

### Backend — nuovi endpoint
- `GET /admin/fatture/diagnostics` — restituisce elenco appuntamenti pagati (stato `confermato`/`completato`/`cancellato_con_addebito`) che **non hanno una fattura sanitaria**. Include dati paziente + terapeuta per identificarli velocemente.
- `POST /admin/fatture/generate-missing` — tenta di generare le fatture mancanti per TUTTI questi appuntamenti. Restituisce lista dei successi + lista dei fallimenti con motivo dettagliato (P.IVA mancante, storage down, anagrafica invalida, ecc.).
- Filtro `kind` esteso a `nota_credito_sanitaria` in `/admin/fatture`.

### Frontend — banner rosso in `/admin/fatture`
- Se ci sono pagamenti senza fattura, appare un banner rosso con:
  - Contatore pagamenti mancanti
  - Prime 5 righe (paziente + email + data + prezzo)
  - Pulsante "Genera N fatture mancanti" (chiama `generate-missing`).
- Toast con conteggio generate/errori. Se ci sono errori, un secondo toast mostra la prima causa (così sai subito che deve correggere prima di riprovare).

- **Test E2E**: preview con 0 pagamenti → `missing_count: 0` (nessun banner). Dopo il deploy in produzione, l'admin vedrà finalmente sia i pagamenti orfani sia il pulsante per rigenerare le fatture.



## 2026-02 — UX: Pulsanti Fatture Paziente + Reinvia Admin (P1)
- **File**: `/app/backend/routers/fatture.py` (nuovo endpoint reinvia), `/app/frontend/src/pages/patient/PazienteDashboard.jsx` (link "Le mie fatture"), `/app/frontend/src/pages/admin/FatturePage.jsx` (bottone Reinvia).

### 1. Fattura al Pagamento (verificato)
- Il flusso `_mark_payment_paid()` che emette la fattura al momento del pagamento è **già indipendente dal canale d'acquisto**: sia che il paziente prenoti dal questionario di matching sia direttamente dal profilo del terapeuta, entrambi arrivano allo stesso Stripe Checkout → webhook → fattura. Nessuna modifica necessaria.

### 2. Pulsante "Le mie fatture" nella dashboard paziente
- Nuovo box grande sotto il banner "Il tuo terapeuta" con icona `FileText` arancione, link a `/paziente/fatture`. Sempre visibile — se non ci sono fatture la pagina interna mostra empty state.

### 3. Pulsante "Reinvia" nella dashboard admin
- **Nuovo backend endpoint** `POST /admin/fatture/{id}/reinvia` — carica PDF (da Object Storage o inline) e lo rispedisce al paziente via email. Traccia `resent_at` + `resent_by_admin` per audit.
- **Frontend**: icona `Send` verde nella riga di ogni fattura sanitaria o nota di credito. Confirm dialog + toast con l'email del paziente.
- Test E2E: `POST /api/admin/fatture/FZ-2026-0001/reinvia` → 200 `{"email":"caioricchieri@gmail.com","numero":"FZ-2026-0001"}`.



## 2026-02 — Fix: Auto-select Slot + Migrazione Fatture Mancanti (P1)
Bug segnalati: (1) cliccando "Prenota una seduta" dalla dashboard, il sistema **sceglieva da solo** il primo slot disponibile invece di lasciare al paziente la scelta; (2) fattura non arrivata dopo il pagamento.

### Fix 1 — Auto-select rimosso
- **File**: `/app/frontend/src/pages/public/TerapistaPublicPage.jsx`.
- Prima: `?prenota=1` apriva automaticamente il BookingSheet sul primo slot disponibile → toglieva scelta al paziente.
- Ora: scrolla semplicemente alla sezione slot per far scegliere l'orario. Il BookingSheet si apre solo dopo un click esplicito.

### Fix 2 — Logging + Migrazione Fatture Mancanti
- **File**: `/app/backend/routers/payments.py`, `/app/backend/server.py`.
- **Log migliorato**: `[PAYMENT PAID] auto-fattura failed for appt=X paziente_user=Y terapeuta_user=Z: {error}` — così si può diagnosticare in produzione (dati fiscali incompleti, storage down, validazione anagrafica, ecc.).
- **Nuova migrazione idempotente in `seed_data()`**: al boot cerca appuntamenti `stato in ("confermato","completato","cancellato_con_addebito")` con `paid_at` ma **senza fattura sanitaria** e le genera. Fix retroattivo per pazienti che hanno pagato prima di questo deploy o che sono passati attraverso una failure silenziosa.



## 2026-02 — UX: Paziente può sempre riprenotare col suo terapeuta (P1)
- **File**: `/app/frontend/src/pages/patient/PazienteDashboard.jsx`, `/app/frontend/src/pages/patient/PazienteHome.jsx`.
- **Issue segnalato**: dopo una sessione completata il paziente vedeva solo il pulsante "Trova un altro terapeuta / Questionario" — nessun CTA per prenotare una nuova seduta con lo stesso terapeuta.
- **Fix**:
  - `PazienteDashboard`: nuovo banner nero in cima "Il tuo terapeuta — Dr. X" con pulsante "Prenota una seduta" (arancione). Deducimos il terapeuta dall'appuntamento più recente. Sempre visibile finché c'è almeno una sessione (passata o futura).
  - `PazienteHome` (PWA): quando il terapeuta non ha disponibilità nei prossimi 30 giorni, ora mostra **entrambi** i pulsanti "Vedi disponibilità" (link diretto al profilo con auto-apertura del booking sheet) e "Messaggio" — non solo "Manda un messaggio" come prima.
- Il pulsante linka a `/terapeuti/{id}?prenota=1` che apre automaticamente il BookingSheet sul primo slot disponibile.



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

