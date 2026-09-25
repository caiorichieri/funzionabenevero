# Fix orario email admin "Nuova richiesta terapeuta"

Nel corpo dell'email di notifica admin la riga `Registrazione: 24/09/2026 14:41` mostra 2h in meno rispetto al momento reale (16:41 ora italiana). Va corretta in modo che ogni **nuovo invio** riporti l'ora italiana esatta.

## Chi è impattato

- Admin che riceve la notifica quando un nuovo terapista completa l'iscrizione.
- Nessun impatto per pazienti, terapisti o processi in corso.

## Ambito

**Solo l'email admin "Un nuovo terapeuta si è registrato"**, campo `Registrazione: …`.

Nessun altro template viene toccato. Nessun dato storico viene modificato. Le email già inviate ieri restano come sono.

## Cosa cambia dal punto di vista utente

Il campo `Registrazione:` nel prossimo email di notifica admin mostrerà:

**Prima** (bug attuale): `Registrazione: 24/09/2026 14:41`
**Dopo** (fix): `Registrazione: 24/09/2026 16:41`

L'ora coinciderà con quella del cellulare / laptop dell'admin, e sarà espressa in ora italiana automatica (CET d'inverno, CEST d'estate). Nessuna etichetta esplicita "ora italiana" viene aggiunta — il formato resta identico a oggi, si corregge solo il valore.

## Come si fa

1. Si legge il codice della funzione che invia il "Nuova richiesta terapeuta".
2. Si identifica il punto in cui il timestamp `Registrazione` viene formattato — quasi certamente un `datetime.utcnow()` o simile stampato senza conversione al fuso italiano.
3. Si converte il valore ad **Europe/Rome** prima del `strftime`, così CET/CEST è gestito automaticamente da Python.
4. Verifica finale a carico del **bug_testing_agent**: simula una nuova iscrizione terapista e conferma che l'orario nel corpo dell'email coincida con l'ora reale italiana.

## Cosa NON viene fatto

Escluso esplicitamente dall'ambito:

- Backfill di email storiche o dati nel database.
- Refactor generale del formattatore date.
- Audit di altri template email (promemoria seduta, fattura, conferma prenotazione, ecc.).
- Aggiunta di label "ora italiana" o simili.
- Modifiche al frontend.
- Nuove variabili d'ambiente, nuove dipendenze o nuovi endpoint.

Se in futuro emergono altri email con lo stesso sintomo, saranno oggetto di un nuovo task separato.

## Fasi

### Fase 1 (MVP — quello che viene costruito ora)
- Fix del formato timestamp `Registrazione:` nell'email di notifica admin "Nuova richiesta terapeuta".
- Verifica obbligatoria via bug_testing_agent.

### Fase 2 (fuori scope, solo se richiesto in futuro)
- Auditoria estesa degli altri template.
- Helper unico condiviso per la formattazione date-ora nell'intera app.
- Regression test suite per CET/CEST.

## Assumptions

- Target fuso orario: **Europe/Rome**. La conversione avviene lato server prima di generare l'HTML.
- Il formato visivo `dd/MM/YYYY HH:MM` (24h) resta uguale — cambia solo il valore.
- La verifica finale è a carico del bug_testing_agent, non self-test manuale.
- Il fix è puramente text-level nell'HTML dell'email futura: nessuna migrazione dati, nessun contratto API cambia.
