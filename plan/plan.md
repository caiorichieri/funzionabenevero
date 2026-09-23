# Piano: fattura FZ-2026-0004 non recapitata + email brandizzata

## Risposta alla domanda ("perché la fattura non parte se dovrebbe essere emessa prima dell'email e subito dopo il pagamento?")

Sono **due step distinti** dello stesso flusso, non uno solo:

1. **Emissione della fattura** — allocazione del numero (FZ-2026-0004), generazione dell'XML TD01, rendering del PDF, salvataggio in DB e/o Object Storage. **Questo step è andato bene** per FZ-2026-0004: infatti la fattura appare in "Le mie fatture" del paziente ed è scaricabile.

2. **Invio della fattura via email** — recupero del PDF dallo storage, costruzione dell'email, invio a Resend. **Questo step è fallito silenziosamente.**

I due step girano uno dopo l'altro dentro il webhook Stripe, in un `try/except` unico. Se lo step 2 fallisce, lo step 1 resta valido (la fattura è emessa a fini fiscali) — ma il paziente non riceve la notifica via email.

### Perché lo step 2 può fallire dopo che lo step 1 è riuscito

Tre motivi concreti nel codice attuale, in ordine di probabilità:

**A · Recupero del PDF dallo storage inghiottito.** Quando la fattura viene emessa dal migration all'avvio (caso comune quando c'è stato un redeploy tra pagamento ed emissione), il PDF finisce in Object Storage. Al momento di allegarlo all'email, viene rifatto un fetch. Se c'è un errore temporaneo di rete o di credenziali, l'eccezione viene catturata e `pdf_bytes` resta vuoto. L'email parte comunque **senza allegato** e col template sbagliato (vedi punto B) — Resend la registra come "delivered" ma il paziente non la riconosce.

**B · Template completamente sbagliato.** Il codice riusa una funzione fatta per la ricevuta di firma di documenti legali (`send_signature_receipt_email`). Anche se l'email fosse arrivata:
- Soggetto: "Ricevuta di sottoscrizione — Funzionabene" (zero parole "fattura").
- Allegato: `ricevuta_sottoscrizione.pdf` (non riconoscibile).
- Corpo: parla di hash SHA-256, timestamp UTC, firma digitale.

Il paziente probabilmente l'ha ignorata o cestinata pensando fosse un documento legale già gestito. Legittima segnalazione "non ho ricevuto la fattura".

**C · Idempotency guard.** Se un primo tentativo aveva marcato `email_sent_at` sulla fattura (anche parziale), il pulsante "Reinvia" del pannello admin oggi rispetta quel flag e non rifà l'invio → click silenzioso, nessuna email.

Per FZ-2026-0004 è scattato uno di A/B/C. Nessuno di questi lascia traccia chiara nei log perché l'errore viene inghiottito senza segnalarlo nel diagnostico admin.

---

## Cosa cambia

Le decisioni confermate nella conversazione sono:
- Soggetto email: **`"Fattura {NUMERO} per la tua seduta con Dr. {COGNOME}"`**
- Reply-To: **`info@funzionabene.it`**
- Mittente (from): resta **`noreply@funzionabene.it`** (dominio verificato su Resend, nessun rollback).

### 1. Nuova email dedicata alla fattura
Nuova funzione separata dall'invio della ricevuta di firma. Uso: webhook Stripe, pulsante admin "Reinvia", migration di boot.

Contenuto:
- **Soggetto**: `Fattura {NUMERO} per la tua seduta con Dr. {COGNOME}` (es. "Fattura FZ-2026-0004 per la tua seduta con Dr. De Clara").
- **Allegato**: `Fattura_{NUMERO}.pdf` (es. `Fattura_FZ-2026-0004.pdf`).
- **Corpo**:
  - "Ciao {NOME}, ecco la fattura per la seduta con Dr. {COGNOME} del {GIORNO}."
  - Blocco riepilogo: numero, data emissione, importo totale, causale.
  - Nota fiscale: "Detraibile al 19% al 730 come spesa sanitaria (art. 15 TUIR). Conserva la fattura per 5 anni."
  - Pulsante "Scarica la fattura dalla tua area" (link diretto a "Le mie fatture" — utile se l'allegato non arriva).
- **Reply-To**: `info@funzionabene.it`.
- **Footer**: `BIDOC SRL · P.IVA 01985930930 · info@funzionabene.it`.

### 2. Robustezza dell'invio
- Log verbose prima e dopo la chiamata a Resend con `email_id` del risultato. Distingue "non chiamato" da "chiamato ma Resend ha rifiutato" da "chiamato senza allegato".
- Se il PDF non è recuperabile dallo storage, l'email parte comunque **senza allegato** ma col pulsante "Scarica dall'app" ben visibile. Meglio arrivare senza allegato che non arrivare.
- Errori del fetch storage o della chiamata Resend vengono scritti in `payment_transactions.fattura_error` e `fattura_error_step` (rispettivamente `fetch_pdf` o `send_email`) — così il banner diagnostica dell'admin li mostra e l'admin sa cosa premere.

### 3. "Reinvia" del pannello admin ora funziona sempre
Il pulsante "Reinvia" bypassa il flag `email_sent_at`: se l'admin lo preme è un'azione esplicita, e va eseguita anche se un invio precedente risulta "riuscito" ma il paziente segnala di non averla ricevuta.

### 4. Ripristino di FZ-2026-0004
Dopo la release, dal pannello admin Fatture → riga FZ-2026-0004 → "Reinvia". Con il nuovo template + logging, o arriva al paziente (99% dei casi), oppure sappiamo esattamente dove sta il problema e correggiamo puntualmente.

## Cosa NON viene fatto

- Nessuna modifica a `SENDER_EMAIL` (rimane `noreply@funzionabene.it`, dominio verificato).
- Nessuna modifica ai template di conferma prenotazione o promemoria (funzionano).
- Nessuna modifica al template della ricevuta di firma documenti legali (giusto per il suo caso d'uso).

## Assunzioni

- `info@funzionabene.it` esiste come casella di posta ed è controllata dal team di supporto.
- FZ-2026-0004 è l'unico caso segnalato di fattura non recapitata — nessun backfill in massa.
- L'admin ha accesso al pannello Fatture per premere "Reinvia" dopo il deploy.
