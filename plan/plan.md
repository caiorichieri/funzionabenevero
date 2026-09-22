# Piano: Sessione video — accesso, no-show, log

## Cosa non funziona oggi (root cause)

1. **Il pulsante "Entra" del paziente scompare esattamente all'orario di inizio.**
   La dashboard/home del paziente filtra gli appuntamenti mostrando solo quelli con `data_ora > adesso`. Alle 16:00 in punto la seduta delle 16:00 esce dalla lista, il pulsante svanisce e la seduta migra nella sezione "passate", dove non c'è alcun link di ingresso.

2. **Il terapeuta non vede mai il pulsante "Entra".**
   La dashboard del terapeuta usa lo stesso filtro `> adesso` per la lista "Prossime sessioni" — dove vive il pulsante. Nella lista "Sessioni oggi" non c'è nessun pulsante di ingresso. Quindi nel momento utile (15 min prima → 15 min dopo) il terapeuta non ha alcun accesso visibile.

3. **Il link ricevuto via email 15 min prima non apre.**
   L'email arriva puntuale ma il token di ingresso alla stanza Daily.co ha una finestra di validità che parte esattamente all'orario `inizio − 15 min`. Piccoli scarti di orologio, tempi di consegna dell'email e apertura del client tolgono di mezzo i primi secondi utili: risultato "sembra aprirsi ma non apre". Non c'è nessun messaggio chiaro all'utente né un pulsante di ripetizione: si vede una pagina di errore generica.

4. **Nessun rilevamento no-show, nessun follow-up automatico.**
   Al momento non esiste alcun processo che verifica, dopo la seduta, chi si è presentato e chi no. Nessuna email di recupero al paziente. Nessuna segnalazione al terapeuta assente. Nessun alert all'amministrazione.

5. **I log di presenza in seduta non sono consultabili in modo affidabile.**
   Oggi le presenze si leggono a richiesta interrogando Daily.co in tempo reale. Se un domani un utente contesta una seduta, o Daily ripulisce lo storico, non abbiamo una fonte propria di verità. Non c'è una pagina admin per consultarli.

---

## Cosa verrà cambiato

### A. Il pulsante "Entra" resta visibile nella finestra giusta
Regola unica per paziente + terapeuta + admin:
> il pulsante appare **15 min prima** dell'orario di inizio e scompare **15 min dopo l'orario di inizio**.

Questo vale come richiesto: chi non è entrato entro `inizio + 15 min` è considerato no-show e il pulsante sparisce (la stanza Daily viene comunque chiusa).

Effetti collaterali:
- Sulla dashboard del paziente la seduta della giornata resta visibile finché la finestra è aperta, poi si sposta nella sezione "passate".
- Sulla dashboard del terapeuta la seduta compare in evidenza in cima alla lista "Oggi" con il pulsante grande in vista appena scatta la finestra.
- La versione mobile/PWA del paziente ha lo stesso comportamento e la stessa scritta di attesa quando manca meno di un'ora.

### B. Il link dell'email 15 min prima funziona senza errori a raffica
Interventi combinati:
- Rilassamento della finestra di validità del token della stanza: il token diventa valido **20 min prima** dell'inizio (invece che esattamente 15), così l'email ricevuta con qualche secondo di anticipo non trova il "muro" chiuso. La finestra alla coda resta a 15 min dopo l'inizio, come richiesto.
- Quando il paziente/terapeuta apre il link nei primi secondi utili e il token non è ancora valido, la pagina video mostra un **countdown** e ritenta da sola all'orario giusto, invece di lasciare un errore generico.
- Se il link è scaduto (usato dopo `inizio + 15 min`), la pagina lo dice in modo esplicito e propone al paziente di prenotare un'altra seduta con lo stesso terapeuta; al terapeuta di scrivere a `hr@funzionabene.it`.

### C. Processo automatico di no-show a `inizio + 15 min`
15 min dopo l'orario di inizio viene lanciato un controllo automatico che interroga Daily.co per sapere chi è entrato in stanza. Quattro esiti possibili:

1. **Entrambi presenti** → nessuna email, seduta marcata come `in_corso` (fino a fine) poi `completato`.
2. **Solo paziente entrato / terapeuta assente** →
   - email al terapeuta che lo informa dell'assenza e gli chiede di scrivere a `hr@funzionabene.it` per giustificare / rischedulare;
   - email al paziente che si scusa a nome della piattaforma, gli comunica che il team lo ricontatterà, e nel frattempo gli offre il link per riprenotare con lo stesso terapeuta (o cambiare terapeuta se preferisce);
   - alert email a `hr@funzionabene.it` con contesto completo.
2b. **Solo terapeuta entrato / paziente assente** →
   - email al paziente con un tono comprensivo ("ci sei mancato oggi") + link diretto per prenotare un'altra seduta con lo stesso terapeuta;
   - il terapeuta viene notificato che il paziente non si è presentato;
   - la seduta viene marcata "no-show paziente" (la fattura resta valida — non è un rimborso automatico).
3. **Entrambi assenti** →
   - email al paziente con link di riprenotazione;
   - alert a `hr@funzionabene.it` per rivedere il caso.

**Nota sull'addebito**: la responsabilità dell'assenza definisce se la seduta viene rimborsata o no. Su questo il piano **non** decide automaticamente: la seduta viene solo etichettata (`no_show_paziente`, `no_show_terapeuta`, `no_show_entrambi`) e l'admin, dal pannello, decide se rimborsare tramite Stripe. Motivazione: un rimborso automatico può essere ingiusto in tanti scenari (paziente entra dal telefono ma la stanza segna errore, terapeuta entrato con un altro account, connessione debole non registrata come "join", ecc.). Nessuna azione di rimborso automatico verrà mai eseguita da questo processo.

### D. Log di presenza consultabili nel tempo
Per ogni seduta viene salvato nel database, alla chiusura della finestra utile e poi periodicamente per 24 ore, uno snapshot con:
- chi è entrato,
- a che ora è entrato e uscito (in fuso Europe/Rome),
- quanto è rimasto,
- l'esito no-show calcolato,
- riferimento tecnico alla stanza Daily.

Questo storico è visibile:
- al terapeuta sulla scheda della seduta (dopo la fine),
- all'admin in una nuova sezione **"Log sedute"** all'interno della pagina Appuntamenti dell'admin, con filtro per periodo/terapeuta/no-show.

Non è visibile al paziente per non generare fraintendimenti su piccoli scarti di secondi.

---

## Chiarimenti già decisi (per default) — dire se cambiare

1. **Finestra di apertura del link**: 20 min prima → 15 min dopo l'inizio. La richiesta era "15 prima / 15 dopo"; ho spostato l'apertura a 20 min prima solo per risolvere l'errore "sembra aprire ma non apre" nei primissimi secondi. Se preferite tenere esattamente 15/15, va bene ma la pagina di ingresso dovrà comunque mostrare countdown+retry per non far più errore.
2. **Chiusura del pulsante**: il pulsante "Entra" **scompare a `inizio + 15 min`** (come richiesto), non a `fine + 15 min`. Chi non è entrato in tempo perde l'accesso e riceve il flusso no-show. Se una seduta dovesse durare più del previsto e uno dei due esce e vuole rientrare a metà, deve comunque essere entrato almeno una volta prima di `inizio + 15 min`.
3. **Chi rimborsa in caso di no-show**: nessuno in automatico. Etichetta + notifica admin, decisione umana. Se preferite regola "no-show paziente = no rimborso, no-show terapeuta = rimborso totale automatico", va detto esplicitamente qui e verrà applicata.
4. **Link "prenota un'altra seduta"** che viene inviato al paziente no-show: punta al **profilo pubblico dello stesso terapeuta** con la modalità di prenotazione veloce già aperta. Se preferite che porti a "cerca un altro terapeuta", va detto qui.
5. **Chi riceve gli alert email di no-show lato admin**: solo `hr@funzionabene.it`. Aggiungerne altri va detto qui.
6. **Ritenzione dei log seduta nel database**: senza scadenza (rimangono per sempre insieme all'appuntamento). Se preferite una purga automatica (es. dopo 5 anni per GDPR), va detto qui.
7. **Registrazione audio/video della seduta**: **non attivata**. Nessun contenuto della seduta è salvato — solo metadati di presenza (chi è entrato, quando, per quanto). Se in futuro si vorrà registrare, richiederà un progetto a parte con consenso esplicito paziente + adeguamento GDPR.

## Cosa resta fuori scope da questo piano
- Fase 19 (Coach Sessuale AI).
- Storico sessioni con note del diario nella dashboard paziente.
- Email 24h post-sessione ("com'è andata?") — già esistente, non toccata.
- Web push VAPID.
- Invio SDI automatico delle fatture.
- Il fix "fattura mancante dopo pagamento" è già consegnato e non è in questo piano.
