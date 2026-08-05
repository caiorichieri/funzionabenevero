# Mappa Tecnica di Implementazione — Privacy & Compliance GDPR

_Documento di pianificazione tecnica. Nessuna modifica al codice è stata ancora effettuata._

---

## 🗂️ Panoramica documenti legali creati

| # | Documento | File sorgente | Pubblicazione web |
|---|---|---|---|
| 1 | Informativa Privacy Visitatori | `/app/memory/legal/informativa_privacy_visitatori.md` | `/privacy-visitatori` |
| 2 | Informativa Privacy Pazienti | `/app/memory/legal/informativa_privacy_pazienti.md` | `/privacy-pazienti` |
| 3 | Informativa Privacy Terapeuti + DPA | `/app/memory/legal/informativa_privacy_terapeuti.md` | `/privacy-terapeuti` |
| 4 | Cookie Policy | `/app/memory/legal/cookie_policy.md` | `/cookie-policy` |

---

## 🎯 FASE 1 — Pagine legali (Frontend)

### 1.1 Nuove pagine React

Creare 4 nuove pagine statiche (rendering del contenuto Markdown):

```
/app/frontend/src/pages/legal/
├── PrivacyVisitatoriPage.jsx
├── PrivacyPazientiPage.jsx
├── PrivacyTerapeutiPage.jsx
└── CookiePolicyPage.jsx
```

Ogni pagina:
- Importa il testo Markdown come stringa;
- Usa `react-markdown` (già presente in shadcn) per il rendering;
- Layout coerente con il design del sito;
- SEO metadata (`<title>`, `<meta description>`);
- Include footer di ultima modifica.

### 1.2 Aggiungere le rotte in `App.js`

```jsx
<Route path="/privacy-visitatori" element={<PrivacyVisitatoriPage />} />
<Route path="/privacy-pazienti" element={<PrivacyPazientiPage />} />
<Route path="/privacy-terapeuti" element={<PrivacyTerapeutiPage />} />
<Route path="/cookie-policy" element={<CookiePolicyPage />} />
```

### 1.3 Aggiornare il Footer globale

`/app/frontend/src/components/Footer.jsx` (o equivalente):

Aggiungere sezione **"Legale"** con link a:
- Termini e Condizioni (già esistente)
- Privacy Visitatori
- Privacy Pazienti
- Privacy Terapeuti
- Cookie Policy
- **"Gestisci preferenze cookie"** (apre il cookie banner)
- **"Esercita i tuoi diritti GDPR"** → `/gdpr-richieste`

Dati aziendali in footer:
> BIDOC SRL — Via Mazzini 62, 33097 Spilimbergo (PN) — P. IVA 01985930930 — REA PN-377600 — PEC: bidocsrl@pecimprese.it — DPO: privacy@bidoc.it

---

## 🍪 FASE 2 — Cookie Banner (GDPR-compliant)

### 2.1 Componente Cookie Banner

`/app/frontend/src/components/CookieBanner.jsx`

Requisiti obbligatori (Provv. Garante 231/2021):

- ✅ Mostrato al **primo accesso** al Sito;
- ✅ **3 pulsanti con pari evidenza grafica**: "Accetta tutti" | "Rifiuta tutti" | "Personalizza";
- ✅ **NON** installa cookie non necessari prima del consenso;
- ✅ Consenso **granulare** per categoria: Necessari (attivi sempre, non modificabili) / Statistica / Esperienza / Marketing;
- ✅ Registrazione del consenso lato backend con timestamp + IP (per accountability art. 7.1 GDPR);
- ✅ Riproposizione del banner **dopo 6 mesi** o in caso di aggiornamento della Cookie Policy;
- ✅ Link a Cookie Policy dettagliata.

Storage locale: `localStorage['funzionabene_cookie_consent']` con struttura:
```json
{
  "necessari": true,
  "statistica": false,
  "esperienza": false,
  "marketing": false,
  "timestamp": "2026-02-15T10:30:00Z",
  "consent_id": "uuid-v4",
  "version": "1.0"
}
```

### 2.2 Loader condizionale degli script

`/app/frontend/src/utils/cookieLoader.js`

Funzioni per caricare/rimuovere dinamicamente gli script in base al consenso:
- `loadGoogleAnalytics()` — solo se `statistica === true`
- `loadMicrosoftClarity()` — solo se `statistica === true`
- `loadMetaPixel()` — solo se `marketing === true`
- `loadTikTokPixel()` — solo se `marketing === true`
- `loadLinkedInInsight()` — solo se `marketing === true`
- `loadGoogleAds()` — solo se `marketing === true`

Google Consent Mode v2 se si integra GA4.

### 2.3 Backend: Registro consensi

Nuovo modello Mongo `cookie_consents`:
```python
class CookieConsent(BaseDocument):
    consent_id: str  # uuid
    user_id: Optional[str]  # se autenticato
    ip_address: str
    user_agent: str
    preferences: dict  # {necessari, statistica, esperienza, marketing}
    timestamp: datetime
    version: str  # versione della cookie policy accettata
```

Nuovo endpoint: `POST /api/consents/cookie` — salva il consenso.

---

## 📝 FASE 3 — Consensi granulari nel flusso Paziente

### 3.1 Signup Paziente (`/registrati` o equivalente)

Aggiungere prima del pulsante "Registrati":

```jsx
<Checkbox required data-testid="consent-privacy-obligatoria">
  Ho letto l'<a href="/privacy-pazienti">Informativa Privacy Pazienti</a> e i
  <a href="/termini">Termini e Condizioni</a>. *
</Checkbox>

<Checkbox required data-testid="consent-dati-sanitari">
  Acconsento al trattamento dei miei dati particolari (relativi alla salute)
  ai fini della compilazione del questionario iniziale e della proposta del
  Terapeuta più adatto (art. 9.2.a GDPR). *
</Checkbox>

<Checkbox data-testid="consent-marketing">
  Acconsento a ricevere comunicazioni promozionali via email/SMS su servizi
  e iniziative di Funzionabene (art. 6.1.a GDPR). — Facoltativo
</Checkbox>

<Checkbox data-testid="consent-miglioramento-servizio">
  Acconsento all'utilizzo dei miei dati anonimizzati per finalità statistiche
  di miglioramento del servizio (art. 6.1.f GDPR). — Facoltativo
</Checkbox>
```

**IMPORTANTE**: I checkbox obbligatori NON possono essere pre-selezionati (art. 4.11 + Cons. 32 GDPR). L'invio del form deve fallire se i due obbligatori non sono spuntati.

### 3.2 Backend — Modello Paziente

Estendere il modello `profili_pazienti` (o `utenti`) con campi:

```python
class ConsentiPaziente(BaseModel):
    privacy_pazienti_accettata: bool = False
    privacy_pazienti_versione: str = "1.0"
    privacy_pazienti_timestamp: datetime
    consenso_dati_sanitari: bool = False
    consenso_dati_sanitari_timestamp: datetime
    consenso_marketing: bool = False
    consenso_marketing_timestamp: Optional[datetime]
    consenso_miglioramento: bool = False
    consenso_miglioramento_timestamp: Optional[datetime]
    ip_registrazione: str
```

### 3.3 Endpoint gestione consensi

- `GET /api/user/consents` — restituisce lo stato attuale dei consensi;
- `POST /api/user/consents` — aggiorna un consenso specifico (con log storico);
- `POST /api/user/consents/revoke/{tipo}` — revoca specifica.

Nuovo modello Mongo `consent_history` per tenere lo **storico completo** (obbligatorio per accountability):
```python
class ConsentHistoryEntry(BaseDocument):
    user_id: str
    consent_type: str  # "marketing", "sanitari", "miglioramento"
    action: str  # "grant" | "revoke"
    timestamp: datetime
    ip_address: str
    version_policy: str
```

### 3.4 Questionario iniziale (`/questionario`)

All'inizio del questionario, banner informativo art. 13 GDPR:

```
📋 Prima di iniziare
Le risposte a questo questionario saranno trattate da BIDOC SRL come Titolare
del pre-matching (art. 6.1.b + 9.2.a GDPR) al solo fine di proporti il
Terapeuta più adatto. Alla prima seduta le risposte saranno trasferite al
Terapeuta scelto, che ne diventerà Titolare autonomo.

Leggi l'informativa completa → /privacy-pazienti
```

---

## 👨‍⚕️ FASE 4 — Consensi terapeuta

### 4.1 Onboarding Terapeuta

Aggiungere step al processo di onboarding (`/terapeuta/onboarding`):

```jsx
<Checkbox required data-testid="terapeuta-privacy-accettata">
  Ho letto l'<a href="/privacy-terapeuti">Informativa Privacy Terapeuti</a>
  e accetto il relativo trattamento dei miei dati. *
</Checkbox>

<Checkbox required data-testid="terapeuta-dpa-accettato">
  Sottoscrivo l'<a href="/privacy-terapeuti#parte-2">Accordo di nomina di
  BIDOC SRL come Responsabile del Trattamento (art. 28 GDPR)</a> per i dati
  clinici dei miei Pazienti sulla piattaforma. *
</Checkbox>

<Checkbox required data-testid="terapeuta-conservazione-clinica">
  Mi impegno alla conservazione dei dati clinici per il periodo minimo di 5
  anni ai sensi dell'art. 17 del Codice Deontologico degli Psicologi Italiani. *
</Checkbox>

<Checkbox required data-testid="terapeuta-responsabilita-clinica">
  Dichiaro di essere iscritto all'Albo degli Psicologi e di operare in piena
  autonomia clinica sotto la mia esclusiva responsabilità professionale. *
</Checkbox>
```

### 4.2 Backend — Modello Terapeuta

Estendere `profili_terapeuti`:
```python
class ConsentiTerapeuta(BaseModel):
    privacy_accettata: bool
    dpa_accettato: bool
    dpa_versione: str
    dpa_timestamp: datetime
    dpa_ip: str
    impegno_conservazione_clinica: bool
    dichiarazione_responsabilita_clinica: bool
```

Il terapeuta **non può** ricevere pazienti finché tutti i consensi obbligatori non sono spuntati.

---

## 🔧 FASE 5 — Pagina "I miei dati" (Diritti GDPR)

### 5.1 Frontend

Sezione **"Privacy e i miei dati"** nell'area utente:

- 📥 **Scarica i miei dati** (art. 20 – portabilità) → bottone che chiama `GET /api/user/gdpr/export` → restituisce ZIP con JSON di tutti i dati.
- ❌ **Cancella il mio account** (art. 17 – oblio) → conferma con doppio prompt + email di conferma.
- 🔄 **Gestisci i miei consensi** → visualizza lo stato attuale con toggle per revocare.
- 📜 **Storico consensi** → lista di tutte le azioni di consent grant/revoke con timestamp.
- 📧 **Contatta il DPO** → apre form email precompilato verso `privacy@bidoc.it`.

### 5.2 Backend — Endpoint GDPR

```python
GET  /api/user/gdpr/export        # Portabilità (JSON)
POST /api/user/gdpr/delete        # Richiesta cancellazione (con soft-delete + workflow admin)
GET  /api/user/gdpr/consents      # Stato consensi
PUT  /api/user/gdpr/consents      # Aggiorna consensi
GET  /api/user/gdpr/history       # Storico consensi
POST /api/user/gdpr/contact-dpo   # Form contatto DPO
```

**Cancellazione**: soft-delete iniziale + workflow admin di 15 giorni per verifica obblighi di conservazione (fiscale, giudiziario) + hard-delete definitivo con anonimizzazione dei log.

### 5.3 Pubblica pagina non-autenticata

`/gdpr-richieste` — form pubblico per persone non registrate (o ex utenti) che vogliono esercitare i diritti. Genera un ticket verso `privacy@bidoc.it`.

---

## 🎥 FASE 6 — Banner videochiamata

### 6.1 Componente `VideoCallBanner.jsx`

Prima di entrare nella seduta Daily.co, mostrare avviso:

```
🎥 Questa seduta NON viene registrata.

Le immagini e i contenuti della videochiamata sono trasmessi in tempo reale
e non sono conservati da Funzionabene o dal tuo Terapeuta, salvo che il
Terapeuta ti abbia esplicitamente chiesto (e tu abbia acconsentito) di
registrare la seduta.

[Ho capito, entra in seduta →]
```

---

## 📢 FASE 7 — Revisione linguaggio marketing

### 7.1 Testi da rivedere sul sito

Effettuare grep di frasi che potrebbero qualificare Funzionabene come "erogatore sanitario" e sostituirle con formulazioni da "marketplace tecnologico":

| ❌ Da evitare | ✅ Preferire |
|---|---|
| "il nostro servizio di terapia" | "il servizio di psicologi che aderiscono alla piattaforma" |
| "la nostra clinica online" | "la piattaforma per trovare psicologi online" |
| "prescriviamo il percorso migliore" | "ti proponiamo i terapeuti più adatti alle tue esigenze" |
| "guarigione", "cura garantita" | "supporto psicologico", "percorso di benessere" |
| "il nostro team di psicologi" | "gli psicologi partner", "psicologi iscritti all'Albo che collaborano con la piattaforma" |

### 7.2 File da esaminare

- `/app/frontend/src/pages/HomePage.jsx`
- `/app/frontend/src/pages/AboutPage.jsx`
- `/app/frontend/src/pages/ComeFunzionaPage.jsx`
- Landing pages di marketing

---

## 🗄️ FASE 8 — Data retention automatica

### 8.1 Cron job settimanale — anonimizzazione

`/app/backend/scripts/gdpr_retention.py`

Job schedulato che ogni settimana:

1. Trova utenti Pazienti **inattivi da 36 mesi** → anonimizza (nome=`Utente-anonimo-X`, email=null, telefono=null, mantiene solo dati fiscali per 10 anni);
2. Trova richieste di contatto **più vecchie di 24 mesi** → elimina;
3. Trova risposte questionario **senza registrazione dopo 12 mesi** → elimina;
4. Trova log di navigazione **più vecchi di 12 mesi** → elimina;
5. Registra tutte le azioni in `admin_actions` (audit log).

### 8.2 Data breach workflow

Nuovo modello `data_breaches` per registrare violazioni:
```python
class DataBreach(BaseDocument):
    discovered_at: datetime
    description: str
    affected_users_count: int
    data_categories: list
    severity: str  # low/medium/high
    notified_garante: bool
    notified_garante_at: Optional[datetime]  # obbligo entro 72h
    notified_users: bool
    remediation_actions: str
```

Endpoint admin per gestire il workflow di notifica al Garante entro 72 ore (art. 33 GDPR).

---

## 📋 FASE 9 — Registro dei Trattamenti (art. 30 GDPR)

### 9.1 Documento interno

Creare `/app/memory/legal/registro_trattamenti.md` con schema conforme art. 30 GDPR:

Per BIDOC SRL come Titolare:
1. Dati anagrafici Pazienti
2. Dati questionario iniziale
3. Dati pagamento
4. Dati marketing
5. Log tecnici

Per BIDOC SRL come Responsabile (per conto Terapeuti):
1. Dati clinici ospitati sulla piattaforma
2. Corrispondenza clinica

Ogni voce con: finalità, base giuridica, categorie interessati, categorie dati, destinatari, trasferimenti extra-UE, termini di conservazione, misure di sicurezza.

Documento **non pubblicato**, ma prodotto in caso di ispezione del Garante.

### 9.2 DPIA — Valutazione d'Impatto

Creare `/app/memory/legal/dpia_funzionabene.md` con la DPIA obbligatoria ex art. 35 GDPR per trattamento di dati sanitari in larga scala.

Modello: usare il tool **PIA Software** della CNIL (open source) o il template del Garante Italiano.

---

## 🚦 Priorità di rollout suggerite

| Priorità | Fase | Motivo |
|---|---|---|
| 🔴 P0 | Fase 1 (pagine legali) + Fase 2 (cookie banner) | Compliance minima per operare legalmente in produzione |
| 🔴 P0 | Fase 3 (consensi paziente) + Fase 4 (consensi terapeuta) | Requisito GDPR imprescindibile |
| 🟠 P1 | Fase 5 (diritti GDPR) | Obbligo art. 12 GDPR (facilitare esercizio diritti) |
| 🟠 P1 | Fase 6 (banner videochiamata) | Trasparenza sedute |
| 🟡 P2 | Fase 7 (revisione marketing) | Blindaggio giuridico marketplace vs struttura sanitaria |
| 🟡 P2 | Fase 8 (retention automatica) | Data minimization art. 5.1.e |
| 🟢 P3 | Fase 9 (Registro + DPIA) | Documenti interni, obbligatori ma non pubblici |

---

_Ultimo aggiornamento: [DATA_PIANIFICAZIONE]_
