# 📖 Guida Completa FunzionaBene — Manuale Passo Passo

> **Chi legge questo documento?** Chiunque usi la piattaforma: amministratore BIDOC, terapisti, pazienti. Non serve essere tecnici.
> **Come è organizzata la guida?** Prima le credenziali di accesso, poi ogni flusso spiegato passo passo con esempi concreti.

---

## 🔑 1. CREDENZIALI DI ACCESSO (ambiente di prova)

| Ruolo         | Email                                     | Password        | Cosa può fare                                                                 |
|---------------|-------------------------------------------|-----------------|-------------------------------------------------------------------------------|
| **Admin**     | `admin@funzionabene.it`                   | `admin2026`     | Gestisce tutto: terapisti, pagamenti, blog, cruscotto, invii bonifici        |
| **Terapista** | `demo.terapeuta@funzionabene.it`          | `terapeuta2026` | Vede i suoi pazienti, appuntamenti, incassi, carica documenti, scrive blog   |
| **Paziente**  | `demo.paziente@funzionabene.it`           | `paziente2026`  | Cerca un terapista, prenota una sessione, paga, entra nella call video       |

> ⚠️ **Importante**: Al primo login su ogni account il sistema può chiedere un codice OTP via email. Controlla la casella di posta (anche lo spam).

---

## 🏢 2. GLI ATTORI DELLA PIATTAFORMA

- **BIDOC SRL** — È la società che gestisce la piattaforma. Riceve i pagamenti dai pazienti tramite Stripe, trattiene una commissione del **30%**, e bonifica il **70%** al terapista.
- **Il Terapista** — Il professionista sanitario (psicologo, sessuologo, ecc.). Emette la fattura sanitaria al paziente per l'intera sessione.
- **Il Paziente** — Chi prenota e paga la sessione.
- **Modello legale**: "Mandato all'incasso con Rappresentanza" — BIDOC agisce come intermediario dei pagamenti.

---

## 👨‍⚕️ 3. INSERIMENTO E GESTIONE DI UN NUOVO TERAPISTA

### 3.1 Registrazione (fatta dal terapista stesso)

1. Il terapista va su `funzionabene.it/register` e sceglie il ruolo **"Sono un terapeuta"**.
2. Compila email, password (min 8 caratteri), nome, cognome.
3. Riceve via email un **codice OTP a 6 cifre**.
4. Inserisce l'OTP nella pagina di verifica → account creato.
5. Il suo stato iniziale è **"in attesa di approvazione"** — non è ancora pubblicamente visibile.

### 3.2 Onboarding del terapista (dopo il login)

Il terapista completa 3 step obbligatori prima di essere visibile ai pazienti:

**Step A — Verifica il numero di telefono**
1. Va nella sua area privata → "Il mio profilo"
2. Inserisce numero di telefono italiano (`+39...`) → riceve un SMS con codice → lo inserisce → telefono verificato

**Step B — Carica 3 documenti obbligatori** (PDF, PNG o JPG, max 10MB ognuno)
1. **CV** — Curriculum vitae aggiornato
2. **Laurea** — Diploma di laurea/specializzazione
3. **Assicurazione** — Polizza RC professionale in corso di validità

**Step C — Firma l'Autocertificazione DPR 445/2000**
1. Solo dopo aver completato Step A + Step B, appare il pulsante "Firma Autocertificazione".
2. Cliccando, il sistema registra data, ora e indirizzo IP della firma.
3. Il terapista dichiara sotto la propria responsabilità che i dati inseriti sono veri.

### 3.3 Approvazione da parte dell'Admin

L'amministratore BIDOC accede a `funzionabene.it/admin/terapisti`:

1. Vede la lista di tutti i terapisti con badge di stato (In Attesa / Approvato / Documenti Verificati).
2. Clicca su un terapista → si apre una modale con:
   - Dati anagrafici
   - Numero d'ordine, ordine di appartenenza, città
   - Anni di esperienza, specializzazioni
   - Prezzo sessione, disponibilità settimanale
   - **IBAN italiano** (richiesto per i bonifici del 70%) — validato automaticamente (formato `IT` + 2 cifre + 23 caratteri, es. `IT60X0542811101000000123456`)
   - Compagnia assicurazione, numero polizza, scadenza
3. **Rivede i documenti**: nella sezione "Documenti Caricati" può scaricare CV, Laurea, Assicurazione.
4. Se tutto è a posto, clicca **"Verifica Documenti"** → il terapista diventa **pubblicamente visibile** sul sito.
5. In parallelo, clicca **"Approva Terapeuta"** per abilitare l'account.

### 3.4 Contratto di Mandato Legale

Prima di poter ricevere prenotazioni, il terapista deve accettare digitalmente il contratto **"Mandato all'incasso con Rappresentanza"**:
1. Al primo login dopo l'approvazione, appare una schermata gate "MandatoAcceptanceGate".
2. Il terapista legge il contratto, scorre fino in fondo, spunta "Accetto" → firma digitale registrata con timestamp.
3. Da questo momento in poi può usare la piattaforma normalmente.

---

## 🧑‍💼 4. IL PANNELLO ADMIN — "CRUSCOTTO"

Accesso: login con account admin → menu "Cruscotto" (`/admin`).

### 4.1 KPI Executive (in alto)

Quattro card mostrano lo stato di salute della piattaforma:

- **💶 Fatturato Mese** — Totale incassato tramite Stripe nel mese corrente (con confronto % vs mese precedente)
- **💸 Payout Pendenti** — Quanti euro devono ancora essere bonificati ai terapisti (70% delle sessioni pagate)
- **📅 Sessioni Mese** — Sessioni completate / prenotate + tasso di completamento
- **👥 Terapisti Attivi** — Numero di professionisti + numero pazienti totali

### 4.2 Grafico Ricavi Ultimi 6 Mesi
Grafico a barre in Euro con l'andamento del fatturato lordo mese per mese. Utile per capire trend e stagionalità.

### 4.3 Top 5 Terapisti
Classifica per ricavi lordi con numero di sessioni. Serve per capire chi genera più valore.

### 4.4 Alert IBAN Mancante
🚨 Se un terapista ha sessioni pagate ma **non ha inserito l'IBAN**, appare un alert rosso con:
- Nome del professionista
- Numero di sessioni non ancora bonificate
- Importo pendente
- Link diretto per aggiungere l'IBAN in `/admin/terapisti`

### 4.5 Esporta PDF
Pulsante **"Esporta PDF"** in alto a destra → scarica un report mensile completo (KPI + grafico + top 5 + alert IBAN) da inviare alla direzione.

---

## 💳 5. FLUSSO PAGAMENTI — DA PRENOTAZIONE A BONIFICO

### 5.1 Il paziente prenota (accesso pubblico)

1. Va su `funzionabene.it` → sfoglia i terapisti pubblici (solo quelli con "Documenti Verificati")
2. Clicca su un terapista → vede profilo, prezzo, disponibilità
3. Sceglie uno slot libero → si registra o effettua il login
4. Inserisce numero di telefono → riceve SMS Twilio con codice → verifica (obbligatorio per pagare, valido 60 minuti)
5. Conferma i dati fiscali (Codice Fiscale calcolato automaticamente dai dati anagrafici)
6. Clicca **"Procedi al Pagamento"** → viene rediretto su **Stripe Checkout**
7. Paga con carta di credito → Stripe conferma → torna sulla piattaforma con "Pagamento riuscito"

### 5.2 Cosa succede dietro le quinte

Quando Stripe conferma il pagamento (webhook `checkout.session.completed`):
1. La transazione viene marcata **`payment_status = paid`**
2. L'appuntamento passa da "in attesa di pagamento" → **"confermato"**
3. Viene creata automaticamente una **stanza video Daily.co** dedicata
4. Vengono inviate 2 email di conferma (terapista + paziente) via Resend con il link della call
5. Il sistema pianifica 2 email di promemoria automatiche:
   - **1 giorno prima** dell'appuntamento
   - **1 ora prima** dell'appuntamento
6. La quota **70% viene registrata come "payout pendente"** per il terapista

### 5.3 Come si divide il pagamento

Esempio pratico — sessione da **€65**:
- Il paziente paga **€65** su Stripe → i soldi entrano sul conto BIDOC
- **BIDOC trattiene €19,50 (30%)** come commissione di piattaforma
- **BIDOC bonifica €45,50 (70%)** al terapista sull'IBAN registrato

### 5.4 Admin: gestione bonifici mensili

Ogni fine mese l'admin va su `/admin/pagamenti`:

1. Vede la lista di **tutte le transazioni pagate ma non ancora bonificate** (raggruppate per terapista)
2. Per ogni terapista: nome, IBAN, importo totale da bonificare, numero sessioni
3. Effettua il **bonifico bancario** dal conto BIDOC verso l'IBAN del terapista (operazione manuale in banca)
4. Torna sulla piattaforma → seleziona le transazioni bonificate → clicca **"Segna come Pagate"** → può inserire il riferimento del bonifico (opzionale)
5. Da ora le transazioni sono `payout_status = paid` → sparite dai pendenti, contate nella colonna "già pagati"

### 5.5 Le due fatture

Per ogni sessione la legge italiana richiede 2 fatture separate:

**Fattura A — Sanitaria (Terapista → Paziente)**
- Emessa dal **terapista** per l'intero importo (es. €65)
- Nel PDF: dati fiscali paziente, prestazione sanitaria, IVA esente ex art. 10 DPR 633/72
- L'admin può scaricarla dal cruscotto pagamenti (`GET /admin/fattura-sanitaria/{tx_id}`)
- Sopra €77,47 è richiesta marca da bollo (aggiunta automaticamente €2)
- Se il paziente non ha dato l'opposizione al Sistema TS, la fattura viene trasmessa (funzionalità **invio SDI in attesa di attivazione col commercialista**)

**Fattura B — Commissione (BIDOC → Terapista)**
- Emessa da **BIDOC** al terapista per la commissione mensile del 30% (es. €19,50)
- Riepilogo mensile di tutte le sessioni pagate
- Scaricabile via `/admin/fattura-commissione/{terapeuta_id}/{anno}/{mese}`

---

## 📅 6. GESTIONE APPUNTAMENTI

### 6.1 Vista Paziente
- Login → sezione "I miei appuntamenti"
- Vede lista degli appuntamenti futuri e passati
- Per ogni appuntamento futuro: pulsante **"Entra nella videocall"** (attivo 5 minuti prima dell'ora)

### 6.2 Vista Terapista
- Login → sezione "Appuntamenti"
- Vede solo i propri appuntamenti (filtrati automaticamente)
- Può cambiare lo stato: **prenotato → confermato → completato → cancellato**
- Ha il pulsante "Entra nella videocall" come host della stanza

### 6.3 Videochiamata con Daily.co
1. Alla generazione del token, il terapista entra come **owner** (può moderare, mutare, espellere)
2. Il paziente entra come partecipante normale
3. Al termine, la piattaforma può leggere la **cronologia presenze** (chi è entrato/uscito, per quanto tempo) via `/appuntamenti/{id}/presenze` — utile in caso di contestazioni

### 6.4 Chat 1-a-1 (fuori dalla call)
Il terapista e il paziente hanno accesso a una **chat testuale privata** (`/conversazioni`) — utile per messaggi pre-sessione o materiali. La chat non sostituisce la seduta.

---

## 📝 7. BLOG DEI TERAPISTI

### 7.1 Terapista scrive un articolo
1. Login terapista → sezione "Blog" → "Nuovo articolo"
2. Compila titolo, contenuto, categoria, immagine di copertina
3. Al salvataggio l'articolo è in stato **`bozza`** — non pubblico

### 7.2 Admin approva
1. Login admin → sezione "Blog" — vede tutti gli articoli
2. Per gli articoli in bozza compaiono i pulsanti **"Approva"** o **"Rifiuta"**
3. Approvato → stato `pubblicato` → visibile su `funzionabene.it/blog`
4. Rifiutato → stato `rifiutato` → il terapista può modificare e riproporlo

---

## 🔒 8. GDPR & COMPLIANCE

### 8.1 Consenso Cookie / Privacy
- Al primo accesso al sito appare un banner cookie
- L'utente sceglie: "Essenziali" (obbligatori), "Analytics", "Marketing"
- Le scelte vengono registrate su `audit_consents` con hash della policy, IP anonimizzato, data/ora → prova legale per GDPR
- Le informazioni DPO e legali sono centralizzate in un unico file (`legalInfo.js`) e mostrate su `/privacy`, `/contatti`, footer

### 8.2 Password reset
1. Utente clicca "Password dimenticata?" su login
2. Inserisce email → riceve link email via Resend valido **30 minuti**
3. Clicca il link → apre pagina con form nuova password (min 8 caratteri)
4. Il token viene consumato al primo uso (single-use, OWASP compliant)

### 8.3 SMS Verifica (Twilio Verify)
- Sostituisce la vecchia integrazione Skebby (non più funzionante)
- Twilio invia un codice numerico al numero italiano
- Il codice ha scadenza breve — se scaduto, il paziente può richiedere un reinvio

---

## 📄 9. DOCUMENTI LEGALI PUBBLICI

Sul sito sono presenti pagine pubbliche accessibili a tutti:

- `/privacy` — Informativa Privacy GDPR
- `/termini` — Termini e Condizioni
- `/cookie-policy` — Politica sui cookie
- `/mandato-legale` — Spiega il modello "Mandato all'incasso con Rappresentanza"
- `/contatti` — Dati BIDOC SRL + DPO

---

## 🛠️ 10. INTEGRAZIONI ATTIVE

| Servizio         | Cosa fa                                              | Chiave necessaria      |
|------------------|------------------------------------------------------|------------------------|
| **Stripe**       | Riceve pagamenti carta, gestisce webhook             | ✅ Configurato (test)  |
| **Twilio Verify**| Invia SMS OTP al paziente per verifica telefono      | ✅ Configurato         |
| **Daily.co**     | Crea stanze video per le sessioni                    | ✅ Configurato         |
| **Resend**       | Invia email: OTP, conferme, promemoria, reset psw    | ✅ Configurato         |
| **MongoDB**      | Database persistente per tutti i dati                | ✅ Locale in container |

---

## 🚨 11. COSA FARE SE...

### "Un terapista non riceve il bonifico"
1. Vai su `/admin/cruscotto` → sezione **Alert IBAN Mancante**
2. Se compare, clicca su "Aggiungi IBAN" → apre `/admin/terapisti` → modifica il terapista → inserisci IBAN → salva
3. Torna su `/admin/pagamenti` → esegui il bonifico → segna come pagato

### "Un paziente non riceve l'SMS di verifica"
1. Controlla che il numero abbia il prefisso `+39`
2. Attendi qualche minuto (Twilio a volte ha ritardi)
3. Usa il pulsante "Reinvia codice" (max ogni 60 secondi)

### "Un pagamento risulta pending ma il paziente dice di aver pagato"
1. Vai su Stripe Dashboard → cerca la Session ID (visibile in `/admin/pagamenti`)
2. Se Stripe mostra "succeeded" ma la nostra piattaforma no → il webhook non è arrivato
3. Chiama manualmente `/api/payments/status/{session_id}` — questo controlla Stripe e sincronizza

### "Ho fatto un errore nell'accettazione del Mandato"
Solo l'admin può resettarlo direttamente dal database. Contattare il team tecnico.

---

## 📊 12. REPORT MENSILE (per la direzione BIDOC)

Ogni mese consigliato:
1. Login admin → **`/admin/cruscotto`** → **"Esporta PDF"**
2. Il PDF include: KPI executive, grafico ricavi 6 mesi, tabella dettagliata, top 5 terapisti, alert IBAN mancanti
3. Salvarlo o inoltrarlo alla direzione + commercialista
4. Scaricare le fatture di commissione mensili di ogni terapista da `/admin/pagamenti` (una per professionista attivo)

---

## 🎯 13. LEGENDA STATI

**Stati Appuntamento**
- `in_attesa_pagamento` — creato ma non pagato
- `prenotato` — creato manualmente da admin
- `confermato` — pagato con successo, videocall pronta
- `completato` — la sessione è avvenuta
- `cancellato` — annullato dall'utente o dall'admin
- `annullato` — pagamento fallito/scaduto

**Stati Pagamento**
- `pending` — sessione Stripe creata, aspettando conferma
- `paid` — pagamento riuscito, soldi arrivati a BIDOC
- `failed` / `expired` — pagamento non andato a buon fine
- `refunded` — rimborsato

**Stati Payout (bonifico terapista)**
- `pending` — 70% da bonificare al terapista
- `paid` — bonifico eseguito da BIDOC, contrassegnato dall'admin

**Stati Terapista**
- `pending` (approval_status) — appena registrato, non ancora approvato
- `approvato` — approvato dall'admin
- `documenti_verificati: true` — pubblicamente visibile
- `autocertificazione_firmata: true` — ha firmato DPR 445

**Stati Articolo Blog**
- `bozza` — scritto dal terapista, non pubblico
- `pubblicato` — approvato dall'admin, visibile su `/blog`
- `rifiutato` — non approvato

---

## 📞 SUPPORTO

Per problemi tecnici: contatta il team di sviluppo tramite l'admin BIDOC.
Per domande legali (fatture, SDI, marca da bollo): consulta il commercialista di riferimento.
