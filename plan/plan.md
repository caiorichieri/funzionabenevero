# Marca d'acqua BIDOC sulla fattura PDF — identica all'esempio

Il logo a cuore BD viene stampato come filigrana al centro di ogni pagina della fattura PDF, replicando esattamente il mockup fornito dall'utente. Il risultato finale sarà visivamente indistinguibile dall'immagine di riferimento.

## Who it's for

- **Pazienti** che aprono la propria fattura: riconoscono immediatamente il brand della piattaforma anche se la ricevuta è emessa in nome del terapeuta.
- **Commercialista del terapeuta** che riceve il PDF: il documento è coerente visivamente con il resto della documentazione Bidoc.
- **Terapeuta** che reinvia una ricevuta via "Reinvia" admin: trasmette un documento visibilmente branded, non un PDF anonimo generato da un gestionale generico.

## Core features and experience

### Filigrana identica all'esempio fornito

Il PNG del logo BD viene stampato al centro di ogni pagina A4 con esattamente queste caratteristiche, misurate direttamente dall'immagine di riferimento:

- **Posizione**: centro geometrico assoluto della pagina (orizzontale e verticale).
- **Dimensione**: 16 cm di lato (cuore inscritto in box quadrato), proporzione 1:1 originale preservata. Occupa circa l'80% della larghezza dell'area utile.
- **Opacità**: 10%. Il cuore risulta visibile ma lascia perfettamente leggibile ogni elemento sovrapposto (intestazione, tabelle, totali, nota bollo).
- **Colori**: logo bicolore originale invariato (B grigio-blu, D arancione) — l'opacità ridotta li fonde con il bianco carta nelle stesse tonalità soffuse dell'esempio.
- **Dietro al testo**: la filigrana viene posata sul canvas prima che Platypus disegni il contenuto. Nessun elemento fiscale finisce coperto.

### Applicata a tutte le fatture generate d'ora in avanti

La modifica è centralizzata nel generatore `fatturazione.py::generate_pdf`, quindi vale per:
- Fatture sanitarie TD01 (seduta pagata).
- Note di credito sanitarie TD04 (rimborso/annullo).
- Fatture commissione B2B (BIDOC → terapeuta, fine mese).

Tutte e tre con lo stesso logo cuore BD, come nell'esempio.

### Fallback silenzioso se il logo manca

Se il PNG non è presente nel container al momento della generazione (scenario remoto ma gestito), la filigrana viene saltata e il PDF esce senza watermark. Nessun errore propagato al chiamante, nessun impatto sulla validità fiscale.

## User flow

1. Paziente paga una seduta via Stripe → pipeline genera fattura TD01 con filigrana.
2. Email con PDF allegato arriva al paziente → apre e vede documento identico al mockup.
3. Admin clicca "Reinvia" su una fattura antecedente al deploy → PDF rigenerato con il nuovo layout.

## UI/UX feel

Replica fedele e non interpretativa del mockup fornito dall'utente. Il contenuto fiscale già oggi in produzione (impaginazione, numero fattura, Dati pagamento, nota bollo) rimane esattamente dov'è e com'è. L'unica cosa che cambia è l'aggiunta della filigrana BD cuore dietro al contenuto.

Nessuna animazione, nessun layer interattivo: è un PDF, è una stampa fiscale.

## Implementation phases

### Phase 1 — MVP: filigrana su tutte le fatture (ora)

- Download del logo dal link asset fornito dall'utente e salvataggio in `backend/assets/bidoc_watermark.png` (versato nel repo, deve viaggiare col deploy).
- Modifica di `generate_pdf` in `fatturazione.py`: aggiunta di una callback `onPage` di reportlab che disegna il logo sul canvas prima del flusso Platypus, con `canvas.setFillAlpha(0.10)` + `drawImage(..., mask='auto')` per preservare la trasparenza alpha del PNG.
- Centro pagina A4: `width=16cm`, posizionato in `(A4.width-16cm)/2, (A4.height-16cm)/2`.
- Nessuna modifica all'XML FatturaPA. Nessun endpoint nuovo, nessun env var nuovo, nessuna modifica al DB.

### Phase 2 — Varianti (futuro, non ora)

- Filigrana testuale "BIDOC SRL" al posto del cuore BD per la fattura di commissione B2B, per distinguere a vista il flusso piattaforma→terapeuta dal flusso terapeuta→paziente. Oggi non richiesto: l'utente ha chiesto la stessa filigrana per tutti.
- Toggle amministrativo per generare PDF senza filigrana su richiesta (es. archiviazione agenziale neutrale).

### Phase 3 — Branding esteso (futuro)

- Header della fattura con il logo Bidoc completo accanto all'intestazione del cedente.
- Footer con QR code di verifica pubblica della fattura (`funzionabene.it/fattura/{numero}`).

## Assumptions

- **Il PNG `Bidoc Logo.png` fornito dall'utente** (409 KB) ha canale alpha trasparente intatto. `drawImage(mask='auto')` di reportlab preserva la trasparenza: lo sfondo bianco attorno al cuore resta invisibile, solo il cuore stesso riceve l'opacità ridotta.
- **Replica esatta del mockup**: dimensioni (~16 cm), opacità (10%), posizione (centro assoluto), colori originali del logo. Nessuna variante proposta — se dopo il primo PDF reale servirà un ritocco (es. opacità 8% invece di 10% per qualche visualizzatore PDF), è un singolo parametro, correzione in un commit a seguire.
- **Il logo viene versato nel repo** sotto `backend/assets/`, non in Object Storage. Per un file di 400 KB letto ad ogni generazione, filesystem locale è l'approccio corretto.
- **Filigrana ripetuta su ogni pagina** se il PDF è multi-pagina (callback `onPage` reportlab). Oggi le fatture sanitarie sono monopagina ma la nota di credito o fatture multi-prestazione future potrebbero sforare.
- **Fatture già persistite non vengono rigenerate**. Il PDF antico resta senza filigrana. "Reinvia" admin usa il nuovo layout.
- **XML FatturaPA non toccato**: il SDI accetta solo contenuto strutturato testuale, non immagini. Il branding vive solo nel PDF leggibile da umani.
- **Nessun test di regressione fiscal richiede update**: la suite esistente verifica contenuto testuale, non layout visivo del PDF.
