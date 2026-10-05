# FunzionaBene — audit remediation Fase 1

Rimedio tecnico e strategico al sito funzionabene.it a fronte dell'audit SEO/UX/legale. Fonda le basi per rendere il sito trovabile su Google, coerente nei contenuti, legalmente difendibile e pronto a campagne a pagamento.

## Who it's for

- **Pazienti** che oggi non trovano il sito tramite ricerca (anche cercando il nome del brand) e, se ci arrivano, incontrano un percorso confuso con cinque CTA concorrenti, un pulsante "Scarica l'app" per un'app che non esiste, testimonianze finte e nessun prezzo visibile.
- **Google e crawler**: oggi vedono "You need to enable JavaScript to run this app" al posto del contenuto. Il sito è di fatto non indicizzato.
- **FunzionaBene come brand**: audit legale ha segnalato espressioni non difendibili ("prima piattaforma italiana", "1 su 8 ammesso", testimonianze "rappresentative") che espongono il titolare a rischio deontologico in ambito sanitario.
- **L'amministratore** che vuole aprire campagne a pagamento con basi SEO stabili e messaggi coerenti.

## Core features and experience

### Foundations SEO (bloccanti)
- **Pre-rendering statico con react-snap**: ogni rotta pubblica diventa HTML servito direttamente dal server. Il crawler vede titoli, paragrafi e metadati senza dover eseguire JavaScript. Rotte riservate (`/admin`, login, aree paziente/terapeuta) restano SPA. Dettaglio nelle nove regole della sezione *Assumptions*.
- **Title unici per pagina**: ogni rotta pubblica ha il proprio `<title>` (max 60 caratteri, keyword in testa). Home, FAQ, blog, chi siamo, questionario, ogni articolo del blog, ogni futura pagina area.
- **Canonical assoluti** su tutte le rotte pubbliche.
- **og:image e twitter:image**: immagine 1200×630 con URL assoluto (`https://funzionabene.it/assets/og-cover.png`), sostituire l'attuale logo con percorso relativo.
- **sitemap.xml generata dal build** elencando tutte le rotte pre-renderizzate (statiche + articoli blog recuperati dall'API al build). Submit a Google Search Console è compito dell'admin, non del codice.
- **robots.txt** controllato: deve permettere `/` e vietare `/admin`, `/paziente`, `/terapista`.
- **Redirect 301 www → non-www** (o viceversa, in base all'attuale configurazione DNS/CDN). Verifica tecnica; se richiede modifica DNS, viene segnalato all'admin.
- **Rimozione `<meta name="keywords">`** (inutile per Google, impatto zero).
- **Schema markup JSON-LD**: Organization sul sito, FAQPage sulla pagina FAQ, Article + Person sui post del blog.

### Slug blog leggibili
- Gli articoli oggi hanno URL con ObjectId MongoDB (es. `/blog/6a954241e36c582b9cacb152`).
- Nuovo schema: `/blog/{slug}` dove `slug` è generato dal titolo (kebab-case italiano, max 60 caratteri).
- **Redirect 301** dagli URL ObjectId vecchi ai nuovi slug — nessun link rotto.
- Il backend genera lo slug al momento della pubblicazione dell'articolo e lo persiste. Se mancante su articoli esistenti, lo backfilla una tantum.

### Correzioni UX
- **CTA primaria unica** in home: "Inizia il Questionario". Gli altri bottoni ("Prenota subito", "Trova il tuo sessuologo", "Scopri come funziona") diventano link secondari di contorno, non più in competizione visiva.
- **Pulsante "Scarica l'app" rimosso**. Al suo posto una sezione discreta "App in arrivo — avvisami quando esce" con form email (one-field + submit). Lead salvati in `db.app_waitlist`.
- **Pop-up install PWA solo dalla seconda visita** (controllo via `localStorage` di una flag di primo accesso). Non più contemporaneo al banner cookie.
- **Promesse temporali coerenti**: tutte le occorrenze "entro 48 ore", "nelle prossime ore", "disponibile ora" allineate a una formulazione unica. La formulazione scelta: "Prima seduta entro 48 ore" (realistica dato il parco terapeuti attuale).
- **Titolo "Non per tutti"** sostituito con una formulazione empatica ("Per chi vuole affrontare davvero quello che non si dice" — placeholder, da raffinare).
- **Sezione "sessioni immersive"** spostata più in basso nella homepage; sopra, risposta immediata a "che cosa mi serve" (prerequisiti, costo generico, modalità).
- **Dati generici "76%" e "9x"** rimossi (non pertinenti alla sessuologia — venivano da esposizione per ansie/fobie).

### Coerenza e affidabilità
- **DPO unificato**: un solo indirizzo email `privacy@bidoc.it` ovunque. Rimossa l'occorrenza `caio@friulion.it` dal questionario.
- **Cookie policy URL unico**: `/cookie-policy`. L'URL `/cookie` diventa redirect 301.
- **Menu uniforme**: la voce "Disabilità" presente in tutte le pagine (oggi manca su "Chi siamo" e "Questionario").
- **FAQ riformulate**: domanda "Le sessioni sono online o in presenza?" sostituita con "Come funzionano le sessioni online?" (il servizio è solo online).
- **Alt text immagini** riscritti in italiano descrittivo. Oggi contengono i nomi delle mascotte in portoghese (`embrulhado`, `peludo`), vanno sostituiti con alt coerenti (`"Mascotte FunzionaBene - personaggio arancione sorridente"`).
- **Mockup app**: i nomi fittizi "Dr. Rossi", "Dr. Bianchi", "Anna" vengono sostituiti dai nomi delle mascotte oppure contrassegnati come esempio.

### Rimozioni legali (con audit log)
Prima di qualsiasi modifica, viene creato `/app/memory/RIMOZIONI_LEGALI.md` che per ciascuna rimozione contiene: pagina, selettore/posizione, testo originale verbatim, data rimozione, motivo, stato ("rimosso" / "modificato" + nuovo testo). Serve al legale per decidere se ripristinare.

Elementi rimossi/modificati in Fase 1:
1. **Testimonianze "rappresentative"** — rimosse completamente finché non arrivano recensioni verificabili dalla pagina `/recensione/{id}`.
2. **Superlativi non dimostrabili**: "prima piattaforma italiana", "1 su 8 ammesso", "il miglior sessuologo", e qualsiasi variante — rimossi.
3. **Affermazione "cifratura end-to-end"** — verifica tecnica sul fornitore video (Daily.co) PRIMA di qualsiasi modifica al testo. Se Daily.co conferma e2e → la frase resta e viene aggiunta nota a `RIMOZIONI_LEGALI.md` con riferimento ai docs del vendor. Se non conferma → sostituzione con "connessione cifrata HTTPS" o equivalente verificabile.

Rimangono invariati, segnalati separatamente al legale (fuori scope Fase 1): la parola "Clinica" nel titolo (`<title>FunzionaBene — Clinica di Sessuologia Online</title>`) e nei testi di sales copy.

## User flow

L'utente non percepisce la maggior parte dei cambi tecnici (pre-rendering, schema, canonical, slug). Vede invece:

1. Arriva sulla home → **una sola CTA grossa** ("Inizia il Questionario"). Nessun confusione tra 5 bottoni concorrenti.
2. Non vede più il pulsante "Scarica l'app" promettente qualcosa che non esiste. Vede, in fondo, un invito discreto a iscriversi alla waitlist.
3. Al primo accesso vede solo il banner cookie (il prompt PWA scompare).
4. Scorre e trova subito risposte a "che cosa mi serve" e "come funziona", prima delle sezioni atmosferiche.
5. Clicca un articolo del blog → l'URL è `/blog/pornografia-e-intimita-reale` invece di `/blog/6a954241e36c582b9cacb152`.
6. Il crawler di Google, nel frattempo, scopre il sito, lo indicizza correttamente, e dopo 2-4 settimane il brand compare nei risultati per "funzionabene sessuologia".

## UI/UX feel

Pulito. Niente di nuovo graficamente — tutti i cambi sono *sottrattivi* (meno CTA, meno pop-up, meno affermazioni gonfiate) o *sostitutivi* (title migliori, alt migliori, slug leggibili). Il tono resta la stessa linea editoriale attuale, con eccezione del claim "Non per tutti" che viene ammorbidito.

Nessuna animazione nuova, nessun componente nuovo, nessuna palette modificata. L'eccezione è la sezione waitlist dell'app, che si posiziona come un card minimale in fondo alla home con un singolo campo email.

Il risultato visivo: sito percepito come **meno ansioso** (meno urlato), **più serio** (nessuna testimonianza finta, nessun superlativo), **più semplice** da attraversare (una CTA, una promessa, un prezzo nascosto onestamente invece di 5 CTA e 3 promesse incompatibili).

## Implementation phases

### Phase 1 — Audit remediation foundations (ora)
Tutto quanto descritto sopra: pre-rendering con react-snap, title unici, canonical, og:image, sitemap+robots, redirect www, schema JSON-LD, slug blog, CTA unificata, rimozione pulsante app + waitlist, pop-up PWA dalla 2° visita, promesse temporali coerenti, DPO/cookie/menu/FAQ/alt-text uniformati, rimozioni legali (testimonianze + superlativi + verifica cifratura) con log in RIMOZIONI_LEGALI.md.

### Phase 2 — Content expansion (dopo)
20 pagine dedicate per area di intervento (es. `/eiaculazione-precoce`, `/vaginismo`, `/terapia-di-coppia`), ognuna 800+ parole, FAQ specifiche, CTA al questionario, con link reciproci agli articoli del blog pertinenti. Ripresa calendario editoriale del blog (1 articolo a settimana) con autori firmati e data di revisione sugli articoli clinici. Correzione refusi nei titoli esistenti (spazio prima dei due punti in sei titoli).

### Phase 3 — Growth e trust (dopo ancora)
Pagina Team con foto + nome + Albo + direttore clinico quando ci sono almeno 2-3 terapeuti reali onboardati. Prezzi visibili (strategia da decidere: minimo, range, o per terapeuta). Prima seduta a prezzo ridotto o colloquio conoscitivo gratuito come porta d'ingresso. Icone social funzionanti con tracciamento UTM. Decisione finale col legale su "Clinica" e eventuali ripristini da RIMOZIONI_LEGALI.md.

## Assumptions

### Pre-rendering (react-snap) — le 9 regole dell'utente, verbatim, applicate alla lettera

0. **PRIMA DI TUTTO** — creare un checkpoint/backup ripristinabile. Modificare SOLO il frontend e la configurazione di build. Non toccare backend, database, endpoint API, variabili d'ambiente, autenticazione, sitemap esistenti o robots.txt (salvo quanto indicato al punto 7). Nessuna modifica non richiesta.

1. **VERIFICA PRELIMINARE** (senza modificare nulla) — comunicare all'utente la versione di React, react-scripts e react-router. Elencare tutte le rotte, distinguendo pubbliche e private. Se react-snap non è compatibile con la versione di React installata, FERMARSI e proporre un'alternativa senza applicare modifiche.

2. **INSTALLAZIONE E CONFIGURAZIONE** — react-snap come devDependency + script `"postbuild": "react-snap"`. Nel blocco `reactSnap` di package.json: includere tutte le rotte pubbliche; ESCLUDERE `/admin`, pagine di login, ogni rotta che richiede autenticazione. Mai pre-renderizzare pagine con dati utente. Se serve in ambiente container, usare `puppeteerArgs: ["--no-sandbox"]`. Non attivare `inlineCss`. L'output deve restare cartella statica (`build/`) pubblicabile su qualsiasi hosting.

3. **HYDRATION** — in `index.js` usare `hydrate` (`hydrateRoot` su React 18) quando il root contiene già HTML, altrimenti render normale. Il codice che usa `window`, `document`, `localStorage`, `Date` o `Math.random` durante il render va protetto (`useEffect` o `typeof window`) per evitare differenze tra HTML pre-renderizzato e client. In console zero errori di hydration.

4. **ARTICOLI DEL BLOG** — prima del pre-render, il build deve recuperare l'elenco degli articoli dall'API e passare tutti gli URL a react-snap. Se l'API non è raggiungibile durante il build, il build deve FALLIRE. Nessuna pagina vuota. Ogni pagina articolo deve contenere nell'HTML titolo e testo reali.

5. **EFFETTI COLLATERALI DEL PRE-RENDER** — durante lo snapshot (user agent `ReactSnap`) non devono partire analytics, pixel o eventi di tracciamento. Il banner cookie non deve restare "chiuso" o "accettato" nell'HTML pre-renderizzato.

6. **SERVER / ROUTING** — ogni rotta pre-renderizzata servita dal proprio file HTML (es. `/blog/slug/index.html`). Rotte non pre-renderizzate continuano come SPA (fallback). F5 su rotta profonda deve funzionare. URL inesistenti devono mostrare la pagina 404.

7. **SEO PER PAGINA** — ogni rotta deve avere title, meta description, canonical e og:tags propri (`react-helmet-async` o equivalente). Se esiste `sitemap.xml`, deve elencare le stesse URL pre-renderizzate. Se non esiste, generarlo dal build.

8. **VERIFICA FINALE** (obbligatoria, mostrare output reale) — curl sull'HTML servito per: home, 2 pagine statiche, 2 articoli del blog. Deve esserci testo reale (h1, paragrafi), NON "You need to enable JavaScript". curl su `/admin`: non deve contenere dati sensibili né contenuto riservato. Console del browser: nessun errore di hydration o errore JS. Funzionano: navigazione tra pagine, login admin, form di contatto, prenotazione e questionario. Il build termina senza errori.

9. **PUBBLICAZIONE** — non pubblicare finché non si sono mostrati i risultati del punto 8. Se qualcosa fallisce, ripristinare il checkpoint e spiegare il problema invece di improvvisare soluzioni.

### Altre assumptions

- **Prezzo tenuto nascosto in Fase 1** nonostante l'audit lo chieda. Giustificabile se Laura De Clara è l'unica terapeuta reale e il suo prezzo attuale (€5) è un placeholder. Da riaprire in Fase 3 col portafoglio terapeuti definitivo.
- **Pagina Team saltata in Fase 1**. L'audit la segnala come "Alta priorità / 2 giorni (serve il materiale dai professionisti)" — rinviato finché non ci sono 2-3 terapeuti onboardati.
- **"Clinica" nel title e nel body resta invariata**. Decisione legale posticipata.
- **Testimonianze finte: rimozione totale**. Finché non arrivano recensioni verificabili tramite la pagina `/recensione/{id}` (già esistente), la sezione testimonianze homepage sparisce.
- **Verifica cifratura e2e Daily.co è un check tecnico sui documenti del fornitore prima di qualsiasi modifica al testo**. Se i docs confermano → claim mantenuto, nota in RIMOZIONI_LEGALI.md. Se non confermano → sostituzione con "connessione cifrata HTTPS" + nota.
- **Formulazione promessa temporale**: "Prima seduta entro 48 ore" come single source of truth. Modificabile se il team ritiene troppo stretto.
- **Immagine og:cover 1200×630**: viene creata al volo partendo dal logo esistente, con sfondo brand e testo "FunzionaBene — Psicologi e Sessuologi Online". Se l'utente ha già un'immagine marketing pronta, la carica e sostituisce.
- **Redirect 301 www**: se la gestione DNS/CDN non consente di impostare il redirect lato infrastruttura, viene segnalato all'utente senza bloccare le altre modifiche.
- **Form waitlist app**: email salvate in `db.app_waitlist` con `{ email, created_at, source: "home-app-section" }`. Nessun double opt-in in Fase 1 (bassa frizione), aggiungibile dopo se serve GDPR confirm.
- **Articoli blog esistenti**: lo slug viene generato dal titolo attuale. Se due articoli collidono sullo stesso slug, viene aggiunto suffisso numerico (`-2`, `-3`).
- **RIMOZIONI_LEGALI.md**: ogni rimozione viene documentata PRIMA di toccare il codice, non dopo. Se la verifica tecnica blocca una rimozione (es. Daily.co risponde dopo giorni), la rimozione viene posticipata senza bloccare le altre.
- **Nessun test di regressione viene scritto** per cambi puramente di contenuto/metadata (title, alt, copy). I test di regressione nuovi coprono solo: hydration zero-errors, build fail-fast se API blog irraggiungibile, redirect 301 blog da ObjectId a slug.
- **Deploy in produzione resta decisione separata dell'utente**: Fase 1 produce un preview completo. Il deploy è un comando a parte dopo l'OK finale.
