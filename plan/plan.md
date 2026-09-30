# Pulizia fatture sanitarie, contatto WhatsApp e export XML admin

Sei ritocchi indipendenti su contatto pubblico e generazione fatture elettroniche, più un nuovo strumento admin per esportare in blocco gli XML fiscali di un terapeuta filtrati per periodo.
Interventi mirati e circoscritti: nessuno stravolge un flusso esistente, tutti convivono in un'unica release.

## Who it's for

- Pazienti che aprono il CTA "Prenota subito" e cliccano "Più opzioni" → arrivano a un numero WhatsApp reale e presidiato.
- Commercialista e verifiche fiscali del terapeuta → ricevono fatture sanitarie conformi in tutti i casi di soglia, senza note contraddittorie sulla marca da bollo.
- Admin operativo → in un click scarica tutti gli XML fiscali di un terapeuta per un intervallo scelto, invece di aprirli uno per uno dal pannello.

## Core features and experience

### 1. Numero WhatsApp pubblico corretto
Sostituzione di `+39 345 112 4503` con `+39 333 711 6432` come contatto WhatsApp nel modale "Prenota subito" (link `wa.me/393337116432`). Rimozione anche ovunque altrove il vecchio numero compaia nel repository (footer, altre CTA, pagina contatti).

### 2. Nota bollo sotto soglia €77,47 — testo dedicato
Le fatture sanitarie con imponibile inferiore a €77,47 devono riportare come nota di rodapé esattamente:
> *"Imposta di bollo non dovuta ai sensi dell'art. 13 della Tariffa, Parte I, allegata al DPR 642/1972, in quanto l'importo non supera euro 77,47."*
Questa nota è sull'esenzione dal bollo per importo, non su un bollo assolto — è formalmente distinta dal caso sopra soglia.

### 3. Nota bollo sopra soglia — invariata
Per imponibile ≥ €77,47 la nota resta quella attuale:
> *"Prestazione sanitaria esente IVA ai sensi dell'art. 10 c.1 n.18 DPR 633/72. Marca da bollo virtuale €2,00 assolta ove applicabile (art. 6 tabella B DPR 642/72)."*

### 4. Riga di dettaglio semplificata
La descrizione della prestazione nelle fatture sanitarie diventa `"Prestazione psicologica"` — senza la data che oggi appare come `"Prestazione psicologica del 2026-09-23"`. La data della seduta rimane comunque presente in altri punti del documento (data emissione, DatiPagamento).

### 5. Rimozione del blocco "Causale:" in fondo al PDF
Come conseguenza della #4, la sezione "Causale: …" a fine PDF sparisce. La stessa informazione ("Prestazione psicologica") è già la descrizione della riga, quindi non serve ripeterla in fondo.

### 6. Riferimento pagamento in fattura (PDF + XML)
Nuovo blocco compatto **sopra i totali** del PDF, intitolato "Dati pagamento":
- *Metodo:* Carta di credito (Stripe)
- *N. operazione:* `pi_...` (il `stripe_payment_intent_id` della transazione Stripe collegata)

Nell'XML FatturaPA lo stesso dato entra nel blocco `DatiPagamento`: Modalità `MP08` (carta di pagamento), Data pagamento = data della transazione Stripe, Importo = totale fattura, Beneficiario = codice fiscale del terapeuta.

### 7. Export ZIP degli XML per terapeuta e periodo (nuovo strumento admin)
Nuova sezione nel pannello `/admin/fatture`, posizionata sopra la lista fatture:

- **Dropdown "Terapeuta"** — mostra solo terapeuti con almeno una fattura emessa.
- **Data inizio** + **Data fine** — default: 1° gennaio anno corrente → oggi.
- **Toggle "Includi note di credito"** — default acceso.
- **Bottone "Esporta XML in ZIP"** — download immediato di `fatture-{cognome-nome}-{data-inizio}-{data-fine}.zip`.

Nel ZIP solo XML (nessun PDF), ciascuno nominato con il numero fattura (`FZ-2026-00XX.xml`). Le fatture di commissione B2B (piattaforma → terapeuta) non entrano nel pacchetto, perché non fanno parte del cassetto fiscale del terapeuta come emittente.

## User flow

**Paziente**: apre la home → tap "Prenota subito" → nel modale tap "Più opzioni" → si apre WhatsApp verso `+39 333 711 6432`.

**Terapeuta e commercialista**: dopo ogni pagamento, il paziente riceve via email il PDF con la nota di bollo corretta per la soglia, la descrizione pulita, il riferimento Stripe visibile, e l'XML FatturaPA con il blocco `DatiPagamento` pronto per lo SDI.

**Admin**: entra in `/admin/fatture` → seleziona terapeuta dal dropdown → sceglie intervallo date → click "Esporta XML in ZIP" → riceve il file zip con tutte le fatture (e, se toggle attivo, note di credito) del periodo.

## UI/UX feel

- **Modale Prenota subito**: nessuna modifica visiva. Solo il link WhatsApp cambia.
- **PDF fattura**: layout invariato. Cambia solo il testo della nota di piede (secondo la soglia), la stringa della riga di dettaglio, e appare un blocco "Dati pagamento" tra le voci e i totali. Il blocco "Causale:" a fine PDF sparisce.
- **Pannello admin fatture**: il nuovo box "Esporta XML in blocco" appare in cima, distinto graficamente dalla lista sottostante. Coerente con lo stile dei filtri già presenti (input date + dropdown + primary button). Nessun redesign, solo aggiunta.
- **Tono**: strumento operativo, non decorativo. Feedback immediato al click (spinner sul bottone durante la generazione, poi download del file).

## Implementation phases

### Phase 1 — MVP (in questa release)
Tutti e sette gli interventi sopra descritti. Sono cambi mirati, ciascuno tocca uno o due file, nessuno interferisce con gli altri. Le modifiche #4 e #5 sono in realtà un'unica variazione nel codice (la stessa variabile "causale"); la #2 e la #3 coesistono nello stesso ramo condizionale sul PDF generator; la #6 modifica lo stesso file della #2/#3; la #7 è tutta additiva. Perimetro contenuto, deploy unico.

### Phase 2 — Robustezza fiscale (futuro)
- Suite di regressione sulle fatture: casi sotto e sopra soglia, con verifica dei testi nel PDF e degli XML tramite validazione schema FatturaPA v1.2.2.
- Validazione lato server dell'XML prima di persisterlo, per catturare eventuali errori del nuovo blocco `DatiPagamento` prima che arrivino al SDI.

### Phase 3 — Estensioni admin (futuro)
- Nel ZIP di export, aggiunta di un PDF consolidato riepilogativo (totali del periodo, IVA, bollo, elenco fatture).
- Invio automatico mensile al terapeuta del ZIP delle proprie fatture del mese chiuso.
- Contatore live nel dashboard admin: fatture emesse mese/anno corrente, in errore, con bollo assolto.

## Assumptions

- **Il numero WhatsApp `+39 333 711 6432` è già attivo su WhatsApp** e presidiato dalla persona giusta. Se il numero non è ancora registrato su WhatsApp, l'utente arriverebbe a un vicolo cieco.
- **Il vecchio numero `+39 345 112 4503` non è utilizzato per altri scopi** (SMS, contatto commerciale, backup). Se lo fosse, la rimozione globale è troppo aggressiva e vale la pena confermare i punti d'uso prima di sostituire.
- **Il metodo di pagamento è sempre "Carta di credito (Stripe)"** perché Stripe è oggi l'unico canale attivo. Se in futuro si aggiungono altri metodi, il testo dovrà derivare dinamicamente dal record `payment_transactions.payment_method` mantenendo l'infrastruttura pronta.
- **Il campo `stripe_payment_intent_id` è sempre presente** sulle transazioni delle fatture emesse dopo l'integrazione Stripe. Le fatture antiche (pre-Stripe o pagamenti manuali) mostreranno solo "Metodo: Carta di credito (Stripe)" senza numero operazione — la sezione non si rompe, degrada gracefully.
- **Il campo `Causale` è opzionale nello schema TD01 FatturaPA v1.2.2**, quindi rimuoverlo (metterlo a `None`) non compromette la validazione SDI. Nel caso improbabile di un rifiuto da regola custom Agenzia Entrate, si potrebbe reintrodurre un valore neutro tipo "Prestazione professionale".
- **Il ZIP di export contiene solo `sanitaria` e `sanitaria_nc`** (fatture del terapeuta come emittente). Le commissioni B2B della piattaforma verso il terapeuta sono flusso fiscale distinto e non fanno parte del cassetto fiscale del terapeuta come emittente.
- **Le modifiche al PDF valgono per le fatture emesse d'ora in avanti**. Le fatture già presenti in Object Storage non vengono rigenerate; il PDF antico resta col vecchio testo. Se qualcuno richiede una ristampa (via bottone "Reinvia" admin) il sistema genererà quello nuovo con il layout aggiornato.
- **L'endpoint di export ZIP è read-only e admin-only**, idempotente, sicuro per volume anche se richiamato più volte. Con volumi previsti (massimo ~500 fatture per terapeuta all'anno) la generazione in-memory del ZIP resta ampiamente sotto ogni limite di risorse.
- **Il webhook Stripe che sta fallendo dal 21 settembre (email Stripe ricevuta dall'utente) è fuori scope da questo piano**, per esplicita richiesta dell'utente. Verrà gestito separatamente in un'iterazione successiva. Il rischio è che dal 30 settembre Stripe disattivi l'endpoint e le fatture generate da pagamenti nuovi non si aggancino automaticamente all'appuntamento — da monitorare a parte.
