# RIMOZIONI LEGALI — FunzionaBene (Fase C audit)

Documento che traccia ogni testo o blocco di contenuto rimosso o modificato dal frontend/backend pubblico per motivi di conformità (testimonianze non verificabili, superlativi non dimostrabili, claim di cifratura non vera, numeri non documentati).

**Convenzione**:
- Ogni voce riporta: data, file:riga originaria, categoria, testo originale integrale, motivo della rimozione, azione eseguita.
- Nessun testo è stato cancellato definitivamente dalla storia: tutto resta qui per il legale.
- I dati nel DB non sono stati toccati. Solo codice sorgente.

---

## 2026-02-21 — Esecuzione Fase C

**Audit di partenza**: scansione completa del repository, verifica Daily.co E2EE, verifica fonti VR studies, verifica flusso credenziali terapisti.

**Verifiche propedeutiche**:

### Daily.co — stato cifratura reale
- Documentazione ufficiale: https://www.daily.co/security/secure-calls/
- Configurazione nostra (`/app/backend/daily_service.py:52-65`): architettura **SFU** di default, **nessun flag E2EE**, `enable_chat: True`, nessun `enable_recording`, nessun `enable_transcription`.
- **Conclusione**: videoconsulti **cifrati in transito (SRTP/DTLS)**, **NON end-to-end**. Il server Daily (USA) può tecnicamente decifrare media per instradamento SFU.
- Non è stata modificata la configurazione delle stanze video. Solo testo descrittivo del sito.

### Verifica fonti VR studies (HomePage 76% / 9×)
- **76%**: confermato — Garcia-Palacios, Botella, Hoffman, Fabregat (2007), "Comparing Acceptance and Refusal Rates of Virtual Reality Exposure vs. In Vivo Exposure by Patients with Specific Phobias", *CyberPsychology & Behavior* 10(5). N=150 pazienti con **fobie specifiche** (non pazienti sessuologici). Link: https://pubmed.ncbi.nlm.nih.gov/17927544/
- **9×**: confermato come derivazione dai refusal rates dello stesso studio (27%/3% = 9).
- **Errore nella nota originaria**: citava "Meta-analisi JMIR 2022" che riguarda in realtà **dropout rates** (Donker et al. 2022, nessuna differenza significativa) → **non supporta il 9×**. La fonte vera è il paper 2007. Citazione corretta nella sostituzione.

### Verifica flusso credenziali terapisti
- `components/therapist/onboarding/DocumentsStep.jsx:7`: caricamento obbligatorio di CV, Assicurazione RC Professionale, Laurea/Abilitazione.
- `components/therapist/onboarding/DprStep.jsx`: firma digitale autocertificazione ex art. 46 DPR 445/2000.
- `components/therapist/onboarding/PhoneVerifyStep.jsx`: verifica telefonica via SMS.
- `backend/server.py:1807-1811`: approvazione admin con `approval_status: approvato`.
- `backend/server.py:453-484` + `frontend/src/pages/admin/AdminDashboard.jsx:237-244`: **alert automatico scadenza assicurazione a 60 e 30 giorni**.
- Campi DB terapista: `albo_numero`, `albo_ordine`, `albo_iscrizione_data`, `assicurazione_compagnia`, `assicurazione_numero_polizza`, `assicurazione_scadenza`.
- NON esiste cron trimestrale di re-verifica né supervisione clinica mensile automatizzata nel codice.

---

## RIMOZIONI E MODIFICHE APPLICATE

### 1. Testimonianze fittizie — RIMOZIONE COMPLETA

**File**: `/app/frontend/src/data/areeIntervento.js` (righe 37-75)  
**Categoria**: Testimonianza fittizia / non verificabile  
**Motivo**: 6 testimonianze firmate con iniziali e età ("M., 34 anni", "G. e L., 41 e 39 anni", ecc.) presentate come esperienze di pazienti reali. Il disclaimer in home ("nomi, età e dettagli sono stati modificati") ammette la modifica ma non prova che derivino da pazienti reali. Nessun log di raccolta consenso GDPR per queste storie.

**Testo originale integrale rimosso**:
```javascript
// Testimonianze anonimizzate (disclaimer legale incluso)
export const TESTIMONIANZE = [
  {
    nome: "M., 34 anni",
    area: "Disfunzione erettile",
    testo: "Pensavo di essere l'unico. Il percorso con il mio sessuologo mi ha fatto capire quanto fosse un tema comune — e quanto si potesse davvero risolvere.",
    durata: "3 mesi di percorso",
  },
  {
    nome: "G. e L., coppia 41 e 39 anni",
    area: "Differenze di desiderio",
    testo: "Dopo dieci anni insieme pensavamo fosse normale 'spegnersi'. Abbiamo scoperto che non era spegnersi: era non parlarne. Ora è diverso.",
    durata: "6 mesi di percorso di coppia",
  },
  {
    nome: "S., 28 anni",
    area: "Vaginismo",
    testo: "Il tema per cui non avevo mai avuto il coraggio di chiedere aiuto. Farlo online, nel mio spazio, ha reso tutto meno spaventoso. Sono infinitamente grata.",
    durata: "4 mesi di percorso",
  },
  {
    nome: "A., 52 anni",
    area: "Menopausa e andropausa",
    testo: "Credevo che per la mia età non valesse più la pena. Oggi so che non è così — e vivo la mia sessualità meglio di dieci anni fa.",
    durata: "2 mesi di percorso",
  },
  {
    nome: "D., 23 anni",
    area: "Orientamento e coming out",
    testo: "Uno spazio senza etichette, senza fretta. Il mio terapeuta mi ha accompagnato nei miei tempi. Mi ha cambiato la vita.",
    durata: "8 mesi di percorso",
  },
  {
    nome: "R., 46 anni",
    area: "Dipendenza da pornografia",
    testo: "Un ciclo che non riuscivo a interrompere da solo. Il percorso mi ha dato strumenti concreti, non solo parole. Ora ho il controllo.",
    durata: "5 mesi di percorso",
  },
];
```

**Azione**: export `TESTIMONIANZE` rimosso dal file. Nessun placeholder.

---

### 2. Sezione Testimonianze — RIMOZIONE COMPLETA DELLA SECTION

**File**: `/app/frontend/src/pages/public/HomePage.jsx` (righe 410-446)  
**Categoria**: Testimonianza fittizia / dati strutturati  
**Motivo**: Rendering delle testimonianze fittizie di cui al punto 1. Include anche disclaimer GDPR che però non copre la mancanza di origine reale.

**Testo originale integrale rimosso** (sezione completa):
```jsx
{/* ────────── TESTIMONIANZE ────────── */}
<section className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32" data-testid="testimonianze-section">
  <div className="mb-16 max-w-2xl">
    <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Storie dei nostri pazienti</span>
    <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
      Qualcuno l&apos;ha già fatto<br />prima di te.
    </h2>
  </div>

  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
    {TESTIMONIANZE.map((t, i) => (
      <motion.blockquote
        key={i}
        initial={{ opacity: 0, y: 15 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4, delay: (i % 3) * 0.1 }}
        data-testid={`testimonial-${i}`}
        className="p-7 brand-card flex flex-col"
      >
        <Quote className="w-6 h-6 text-[#0A0A0A]/60 mb-4" />
        <p className="text-[#0A0A0A]/85 leading-relaxed font-serif text-lg flex-1">
          &quot;{t.testo}&quot;
        </p>
        <div className="mt-6 pt-5 border-t border-[#0A0A0A]/10">
          <div className="text-sm text-[#0A0A0A]">{t.nome}</div>
          <div className="text-xs tracking-[0.15em] uppercase text-[#6B8FA3] mt-1">{t.area}</div>
          <div className="text-xs text-[#0A0A0A]/50 mt-1">{t.durata}</div>
        </div>
      </motion.blockquote>
    ))}
  </div>

  <p className="mt-12 text-xs text-[#0A0A0A]/65 text-center max-w-2xl mx-auto leading-relaxed">
    Testimonianze rappresentative. Nomi, età e dettagli sono stati modificati per tutelare la riservatezza dei pazienti, come previsto dal codice deontologico degli psicologi e dal GDPR.
  </p>
</section>
```

**Azione**: intera sezione rimossa. Rimosso import `TESTIMONIANZE` e import `Quote` (icona non più usata).

---

### 3. Statistiche Login — RIMOZIONE PANNELLO 4 NUMERI

**File**: `/app/frontend/src/pages/LoginPage.jsx` (righe 51-63)  
**Categoria**: Numeri non dimostrabili  
**Motivo**: 4 statistiche inventate ("12+", "340+", "480+", "98% soddisfazione") senza fonte né log aggregato nel DB.

**Testo originale integrale rimosso**:
```jsx
<div className="grid grid-cols-2 gap-4">
  {[
    { label: "Terapisti", value: "12+" },
    { label: "Pazienti", value: "340+" },
    { label: "Sessioni/mese", value: "480+" },
    { label: "Soddisfazione", value: "98%" }
  ].map((stat) => (
    <div key={stat.label} className="bg-white/5 border border-white/10 rounded-2xl p-4">
      <div className="text-2xl font-bold text-[#E9D628] font-[Outfit]">{stat.value}</div>
      <div className="text-[rgba(253,251,247,0.6)] text-sm mt-1">{stat.label}</div>
    </div>
  ))}
</div>
```

**Azione**: blocco rimosso. Layout del pannello sinistro di login è stato ricompattato: il titolo "Benvenuto nel Gestionale" e il payoff restano, nessun elemento appare spostato o con spazi vuoti perché i margini sono gestiti dal container flex.

---

### 4. Claim "cifratura end-to-end" — RIFORMULAZIONE

**Categoria**: Claim di cifratura non vera (Daily.co usa SFU, non E2EE)  
**Motivo**: Daily.co documentazione ufficiale: le stanze SFU "non sono E2EE in senso stretto". Nostra configurazione non abilita P2P né Insertable Streams. La frase corretta è "cifrato in transito" o "videochiamate cifrate".

#### 4.1 HomePage benefit "Riservatezza assoluta"
**File**: `/app/frontend/src/pages/public/HomePage.jsx:40`  
**Originale**: `"Cifratura end-to-end, segreto professionale, zero dati condivisi. La tua intimità è intima davvero."`  
**Nuovo**: `"Videochiamate cifrate, segreto professionale, zero dati condivisi. La tua intimità è intima davvero."`

#### 4.2 ChiSiamo valore "Riservatezza assoluta"
**File**: `/app/frontend/src/pages/public/ChiSiamoPage.jsx:28`  
**Originale**: `"I tuoi dati sono cifrati end-to-end, custoditi su server europei. Le sessioni sono coperte dal segreto professionale. La tua intimità è intima davvero."`  
**Nuovo**: `"I tuoi dati sono cifrati e custoditi su server europei conformi al GDPR. Le sessioni sono coperte dal segreto professionale. La tua intimità è intima davvero."`

#### 4.3 ScaricaApp — Feature "Riservatezza assoluta"
**File**: `/app/frontend/src/pages/public/ScaricaAppPage.jsx:122`  
**Originale**: `body="Cifratura end-to-end, GDPR, dati in Europa."`  
**Nuovo**: `body="Comunicazione cifrata, GDPR, dati in Europa."`

#### 4.4 SeduteImmersive — trust pill "Riservato per costruzione"
**File**: `/app/frontend/src/pages/public/SeduteImmersive.jsx:215`  
**Originale**: `desc: "Le sessioni non vengono registrate. Comunicazione cifrata end-to-end."`  
**Nuovo**: `desc: "Le sessioni non vengono registrate. Videochiamata cifrata."`

#### 4.5 Registro GDPR trattamenti (backend)
**File**: `/app/backend/server.py:1665`  
**Originale**: `"misure_sicurezza": "Videoconsulto end-to-end encrypted (SRTP/DTLS), stanze temporanee con token JWT a scadenza, nessuna registrazione video lato piattaforma, log accessi."`  
**Nuovo**: `"misure_sicurezza": "Videoconsulto cifrato in transito (SRTP/DTLS) via Daily.co (architettura SFU), stanze temporanee con token JWT a scadenza, nessuna registrazione né trascrizione video lato piattaforma, log accessi."`

---

### 5. "Prima piattaforma italiana…" — RIFORMULAZIONE (5 occorrenze)

**Categoria**: Superlativo di primato non dimostrabile.

#### 5.1 HomePage SEO meta description
**File**: `/app/frontend/src/pages/public/HomePage.jsx:72`  
**Originale**: `description="Prima piattaforma italiana 100% dedicata alla sessuologia. Psicologi e sessuologi iscritti all'Albo, prima sessione entro 48 ore. Online, riservato, cifrato."`  
**Nuovo**: `description="Piattaforma italiana dedicata alla sessuologia. Psicologi e sessuologi iscritti all'Albo. Consulenze online riservate e cifrate."`  
_Nota: "48 ore" rimossa (sarà rivisitata in Fase B). "100%" mantenuta come richiesto dal legale. "Prima" rimossa._

#### 5.2 HomePage benefit "Sessioni immersive"
**File**: `/app/frontend/src/pages/public/HomePage.jsx:29`  
**Originale**: `descrizione: "Prima piattaforma italiana a offrire sessioni terapeutiche immersive per disfunzioni, fobie e blocchi. Sempre guidate dal tuo terapeuta."`  
**Nuovo**: `descrizione: "Piattaforma italiana che integra sessioni terapeutiche immersive per disfunzioni, fobie e blocchi. Sempre guidate dal tuo terapeuta."`

#### 5.3 HomePage sezione immersive — paragrafo
**File**: `/app/frontend/src/pages/public/HomePage.jsx:254`  
**Originale**: `"FunzionaBene è la prima piattaforma italiana a integrare sessioni immersive nei percorsi di sessuologia."`  
**Nuovo**: `"FunzionaBene integra sessioni immersive nei percorsi di sessuologia."`

#### 5.4 ChiSiamo — valore "Innovazione clinica"
**File**: `/app/frontend/src/pages/public/ChiSiamoPage.jsx:18`  
**Originale**: `desc: "Siamo la prima piattaforma italiana a integrare <strong>sessioni immersive</strong> nei percorsi di sessuologia. Non per moda tecnologica, ma perché la ricerca lo dimostra: funziona."`  
**Nuovo**: `desc: "Integriamo <strong>sessioni immersive</strong> nei percorsi di sessuologia. Non per moda tecnologica, ma perché la ricerca sulle tecnologie immersive mostra risultati promettenti per fobie e disturbi d'ansia."`

#### 5.5 ChiSiamo STATS — ultimo elemento
**File**: `/app/frontend/src/pages/public/ChiSiamoPage.jsx:46`  
**Originale**: `{ n: "Prima", desc: "piattaforma italiana con sessioni immersive" }`  
**Nuovo**: `{ n: "Immersive", desc: "sessioni VR integrate nei percorsi di sessuologia" }`

#### 5.6 ChiSiamo SEO meta description
**File**: `/app/frontend/src/pages/public/ChiSiamoPage.jsx:54`  
**Originale**: `description="FunzionaBene: la piattaforma italiana 100% dedicata alla sessuologia. Professionisti scelti uno a uno, iper-specializzati e iscritti all'Albo."`  
**Nuovo**: `description="FunzionaBene: la piattaforma italiana 100% sessuologia. Professionisti scelti uno a uno, iper-specializzati e iscritti all'Albo."`  
_Nota: "100%" conservato come richiesto dal legale._

#### 5.7 SeduteImmersive SEO
**File**: `/app/frontend/src/pages/public/SeduteImmersive.jsx:63`  
**Originale**: `description="Prima piattaforma italiana di sessioni immersive per disfunzioni, ansia da prestazione e fobie sessuali. Sempre guidate dal terapeuta. Evidence-based."`  
**Nuovo**: `description="Piattaforma italiana di sessioni immersive per disfunzioni, ansia da prestazione e fobie sessuali. Sempre guidate dal terapeuta. Evidence-based."`

---

### 6. "1 su 8 ammessi" — RIFORMULAZIONE con fatto verificabile

**File**: `/app/frontend/src/pages/public/HomePage.jsx:534-536`  
**Categoria**: Numero non pubblicato / superlativo di selezione  
**Motivo**: statistica interna non documentata. Sostituita con fatto verificabile dal flusso di onboarding (DocumentsStep.jsx + DprStep.jsx + verifica admin).

**Originale**:
```jsx
<span className="block mt-4 text-[#6B8FA3]">
  Solo <strong className="text-[#0A0A0A]">1 su 8</strong> dei professionisti che si candidano viene ammesso.
</span>
```

**Nuovo**:
```jsx
<span className="block mt-4 text-[#6B8FA3]">
  Ogni terapeuta è <strong className="text-[#0A0A0A]">verificato</strong>: iscrizione all'Albo e assicurazione RC professionale.
</span>
```

_Base di verifica_: documentazione obbligatoria caricata (CV, Laurea, Assicurazione) ex `DocumentsStep.jsx:7`; approvazione manuale admin con flag `approval_status: approvato`; alert automatico scadenza assicurazione 60/30 gg.

---

### 7. Numeri VR 76% / 9× — RIFORMULAZIONE + CORREZIONE FONTE

**File**: `/app/frontend/src/pages/public/HomePage.jsx:258-294`  
**Categoria**: Numeri da studi scientifici — wording ambiguo e citazione errata.

**Verifica fonti**:
- **76%**: ✅ corretto. Garcia-Palacios et al. (2007) *CyberPsychology & Behavior* 10(5), N=150, pazienti con fobie specifiche.
- **9×**: ✅ corretto come derivazione (27%/3% refusal rate dallo stesso studio 2007).
- **Citazione nota originale "Meta-analisi JMIR 2022"**: ❌ errata — JMIR 2022 (Donker et al.) riguarda dropout rates, non refusal rates, e non ha trovato differenze significative. Non supporta il 9×.

**Originale** (righe 259-269):
```jsx
<div className="mt-10 grid sm:grid-cols-2 gap-6">
  <div>
    <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">76%</div>
    <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
      dei pazienti, in studi su terapia espositiva per ansia e fobie, preferisce la realtà virtuale all'esposizione tradizionale<sup>*</sup>
    </div>
  </div>
  <div>
    <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">9×</div>
    <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
      tasso di rifiuto del trattamento più basso in VR rispetto all'esposizione tradizionale<sup>*</sup>
    </div>
  </div>
</div>
```

**Originale nota** (riga 293):
```jsx
<sup>*</sup> Garcia-Palacios A. et al. — <em>studio sull&apos;accettabilità dell&apos;esposizione in VR vs in vivo per fobie specifiche</em>. Meta-analisi JMIR 2022 sull&apos;efficacia della VR-CBT per disturbi d&apos;ansia.
```

**Nuovo**:
```jsx
<div className="mt-10 grid sm:grid-cols-2 gap-6">
  <div>
    <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">76%</div>
    <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
      dei pazienti con fobie specifiche negli studi preferisce la realtà virtuale all'esposizione tradizionale<sup>*</sup>
    </div>
  </div>
  <div>
    <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">9×</div>
    <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
      tasso di rifiuto più basso con la VR rispetto all'esposizione in vivo, negli stessi studi<sup>*</sup>
    </div>
  </div>
</div>
```

**Nuova nota**:
```jsx
<sup>*</sup> Garcia-Palacios A., Botella C., Hoffman H., Fabregat S. (2007) — <em>Comparing Acceptance and Refusal Rates of Virtual Reality Exposure vs. In Vivo Exposure by Patients with Specific Phobias</em>, CyberPsychology & Behavior 10(5), N=150. I dati si riferiscono a studi sulla realtà virtuale in generale, non a risultati di FunzionaBene.
```

---

### 8. "Zero marketing vuoto" — RIFORMULAZIONE

**File**: `/app/frontend/src/pages/public/SeduteImmersive.jsx:216`  
**Categoria**: Auto-elogio non misurabile  
**Originale**: `{ icon: Award, titolo: "Solo evidence-based", desc: "Tecniche supportate da ricerca peer-reviewed. Zero marketing vuoto." }`  
**Nuovo**: `{ icon: Award, titolo: "Solo evidence-based", desc: "Tecniche supportate da ricerca peer-reviewed." }`

---

### 9. "Ogni trimestre verifichiamo" — RIFORMULAZIONE SU CIÒ CHE ESISTE DAVVERO

**File**: `/app/frontend/src/pages/public/ChiSiamoPage.jsx:188-192`  
**Categoria**: Impegno operativo non implementato nella forma dichiarata  
**Motivo**: non esiste un cron trimestrale di re-verifica di multipli documenti. Esiste solo l'alert automatico scadenza assicurazione (60/30 gg) in `server.py:453-484` + `AdminDashboard`.

**Originale**:
```jsx
<p>
  Verifichiamo <strong className="text-[#0A0A0A]">ogni trimestre</strong> l&apos;iscrizione all&apos;Albo, la validità
  della polizza assicurativa professionale e la partecipazione a percorsi di supervisione continua.
  Se qualcosa scade, sospendiamo immediatamente il terapeuta dalla piattaforma.
</p>
```

**Nuovo**:
```jsx
<p>
  Riceviamo <strong className="text-[#0A0A0A]">avvisi automatici 60 e 30 giorni</strong> prima della scadenza
  dell&apos;assicurazione professionale di ogni terapeuta. Se la polizza scade senza essere rinnovata,
  il profilo viene sospeso dalla piattaforma.
</p>
```

---

### 10. Cleanup import morti

- `/app/frontend/src/pages/public/HomePage.jsx:5` — rimosso `Quote` dall'import `lucide-react` (icona usata solo nella sezione testimonianze rimossa al punto 2).
- `/app/frontend/src/pages/public/HomePage.jsx:7` — rimosso `TESTIMONIANZE` dall'import `@/data/areeIntervento`.
- `/app/frontend/src/pages/public/TerapistaPublicPage.jsx:6` — rimosso `Star` dall'import `lucide-react` (import morto: nessuna sezione rating/stelle renderizzata, l'endpoint `/api/reviews/terapista/{id}` esiste ma non ha UI pubblica).

---

### 11. SeduteImmersive — Stats section (76% / 9× / "Prima") + citazione JMIR errata

**File**: `/app/frontend/src/pages/public/SeduteImmersive.jsx:115-139`  
**Categoria**: Numeri da studi scientifici + superlativo di primato + citazione fonte errata (stessa issue del punto 7, replicata su questa pagina).

**Testo originale integrale**:
```jsx
{/* Stats */}
<section className="max-w-6xl mx-auto px-6 lg:px-10 py-20" data-testid="immersive-stats">
  <div className="grid md:grid-cols-3 gap-8">
    <div className="brand-card !p-8">
      <div className="font-serif text-5xl lg:text-6xl text-[#0A0A0A]">76%</div>
      <p className="mt-4 text-sm text-[#0A0A0A]/75 leading-relaxed">
        dei pazienti, in studi su terapia espositiva per ansia e fobie, preferisce la realtà virtuale all'esposizione tradizionale.
      </p>
    </div>
    <div className="brand-card !p-8">
      <div className="font-serif text-5xl lg:text-6xl text-[#0A0A0A]">9×</div>
      <p className="mt-4 text-sm text-[#0A0A0A]/75 leading-relaxed">
        tasso di rifiuto del trattamento più basso in VR rispetto all'esposizione tradizionale.
      </p>
    </div>
    <div className="brand-card !p-8">
      <div className="font-serif text-5xl lg:text-6xl text-[#0A0A0A]">Prima</div>
      <p className="mt-4 text-sm text-[#0A0A0A]/75 leading-relaxed">
        piattaforma italiana di sessuologia ad adottare questo approccio in modo strutturale.
      </p>
    </div>
  </div>
  <p className="mt-8 text-xs text-[#0A0A0A]/60 leading-relaxed text-center max-w-3xl mx-auto">
    Fonti: Garcia-Palacios A. et al. — <em>studio sull'accettabilità dell'esposizione in VR vs in vivo per fobie specifiche</em>. Meta-analisi JMIR 2022 sull'efficacia della VR-CBT per disturbi d'ansia.
  </p>
</section>
```

**Azione**:
- 76% e 9×: wording riformulato come al punto 7 ("dei pazienti con fobie specifiche negli studi", "negli stessi studi") per non far intendere risultati nostri.
- Terza card "Prima piattaforma italiana…" → sostituita con "Integrate / nei percorsi di sessuologia, sempre guidate dal terapeuta e incluse nel costo della sessione" (fatto operativo verificabile).
- Citazione corretta: Garcia-Palacios et al. (2007) *CyberPsychology & Behavior* 10(5), N=150, non JMIR 2022.

---

## ELEMENTI SOLO SEGNALATI — NON MODIFICATI

### A. Collection MongoDB `ambassadors` — vuota
- Collection: 0 documenti attivi al momento della scansione.
- UI consumer: `/app/frontend/src/pages/public/SessualitaDisabilitaPage.jsx:321-328` → mostra placeholder `ambassadors-empty` ("Stiamo raccogliendo le prime voci").
- Endpoint pubblico: `GET /api/public/ambassadors` restituisce array vuoto.
- **Nessuna modifica richiesta**.

### B. Collection MongoDB `reviews` — 1 documento approvato (non visibile al pubblico)
- `_id` recensione: `6a886f0e06b9b7dd0636fa78` (voto 5, testo "Percorso illuminante, sono davvero grato al terapeuta.")
- Endpoint `GET /api/reviews/terapista/{id}` esiste in `routers/reviews.py:111` ma **nessun componente React la renderizza**.
- `TerapistaPublicPage.jsx` NON mostra rating/stelle/recensioni.
- **Nessun contenuto visibile al pubblico**. Flag: valutare se l'endpoint vada rimosso in futuro (fuori scope Fase C).

### C. Collection MongoDB `articoli` — 15 articoli blog
- Visibili su `/blog/<id>`.
- **Non scansionati per contenuto medico** (come da istruzione utente: "non modificarli, segnala soltanto").
- Da scansionare separatamente in futuro per promesse mediche o garanzie di esito.

### D. Occorrenze "Clinica" / "clinico" / "clinica" (aggettivo e sostantivo)
- **`<title>FunzionaBene — Clinica di Sessuologia Online</title>`** in `public/index.html:41`.
- Circa 15+ occorrenze di "clinico/a/e" come aggettivo tecnico ("sessuologia clinica", "direzione clinica", "supervisione clinica", "applicazioni cliniche").
- **Nessuna modifica**: da discutere col legale, come da istruzione utente.

### E. Daily.co — `enable_chat: True`
- La chat durante la videochiamata è attiva. I messaggi transitano via server Daily (USA) durante la sessione, non vengono persistiti dopo la scadenza della stanza (`exp`).
- Lato piattaforma: nessuna copia salvata.
- **Nessuna modifica alla configurazione video**, come da istruzione utente. Flag solo.

### F. Promesse operative "48 ore"
- `components/public/PrenotaSubitoCTA.jsx:78`, `pages/public/BlogPostPage.jsx:129`, `data/blogTemplates.js:80`.
- **Rimandate a Fase B** come da istruzione utente.
- Rimossa dal meta description homepage (vedi punto 5.1) per coerenza con la riformulazione in corso.

### G. Log tecnici — contenuto attuale (NO modifiche)
- File: `/var/log/supervisor/backend.*.log` (gestione container).
- Dati personali presenti: email destinatario email, ID Resend, id interni (user_id, appuntamento_id, terapista_id), numero fattura, nome stanza Daily.
- Dati **NON presenti**: CF, P.IVA, IBAN, numero carta, contenuto clinico, trascrizioni video.
- Retention: ereditata dall'infrastruttura Emergent (nessuna policy esplicita nel codice applicativo).
- Caso particolare: `email_service.py:67` → in modalità disabled (nessuna API key Resend) stampa OTP in chiaro nel log. In produzione con Resend attivo questo path non viene eseguito.
