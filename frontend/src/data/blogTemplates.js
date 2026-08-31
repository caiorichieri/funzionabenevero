/**
 * Pre-made HTML skeletons for common article types.
 * Used by the admin blog editor as a starting point — the admin/therapist
 * fills in the placeholders instead of writing HTML from scratch.
 */

export const BLOG_TEMPLATES = [
  {
    id: "case-study",
    label: "Case Study",
    description: "Un caso clinico raccontato con anonimato e cornice teorica.",
    titolo: "Il coraggio di parlare: il percorso di un paziente con vaginismo",
    contenuto: `<p class="intro"><strong>Nome e dettagli sono modificati per proteggere la privacy della persona.</strong> Questo racconto è pubblicato con il suo consenso e ha lo scopo di aiutare chi si trova in una situazione simile.</p>

<h2>Il quadro iniziale</h2>
<p>Descrivi il paziente in modo non identificabile: età, situazione di vita, come è arrivato in studio, cosa portava. Concentrati sul <strong>vissuto soggettivo</strong> più che sulla diagnosi.</p>

<h2>La cornice teorica</h2>
<p>Spiega in modo semplice come la letteratura scientifica inquadra questo tipo di disturbo. Cita approcci evidence-based (CBT, terapia sistemica, sessuologia clinica) senza appesantire.</p>

<h2>Il percorso terapeutico</h2>
<p>Racconta le tappe: le prime sedute, la costruzione dell'alleanza, gli esercizi proposti, i punti di svolta. <em>Usa il "noi" invece del "il paziente"</em> per riconoscere che il cambiamento è co-costruito.</p>

<h3>Il momento di svolta</h3>
<p>Descrivi l'episodio, la seduta o l'insight che ha cambiato il ritmo del percorso.</p>

<h2>I risultati</h2>
<ul>
  <li>Cambiamento sintomatologico osservato</li>
  <li>Cambiamento nel modo di raccontarsi</li>
  <li>Nuove risorse acquisite</li>
</ul>

<h2>Cosa possiamo imparare</h2>
<p>Chiudi con 2-3 riflessioni cliniche e umane che parlino a chi legge — soprattutto a chi si riconosce nella storia. Ricorda che ogni percorso è unico e che chiedere aiuto è il primo passo.</p>

<blockquote>"La citazione del paziente (se autorizzata) o una frase che sintetizza il senso del percorso."</blockquote>
`,
    tags: "case study, terapia, sessuologia",
  },
  {
    id: "guida-clinica",
    label: "Guida Clinica",
    description: "Spiegazione strutturata di un sintomo, disturbo o area di intervento.",
    titolo: "Anorgasmia femminile: cos'è, perché succede, come si affronta",
    contenuto: `<p class="intro">L'anorgasmia — la difficoltà o impossibilità di raggiungere l'orgasmo — è uno dei motivi di consulto sessuologico più comuni. In questa guida spieghiamo di cosa si tratta, quali sono le cause e cosa possiamo fare per affrontarla.</p>

<h2>Di cosa parliamo davvero</h2>
<p>Definizione clinica in linguaggio semplice. Distinguere tra primaria/secondaria, generalizzata/situazionale. Sfatare uno o due miti diffusi.</p>

<h2>Come si manifesta</h2>
<ul>
  <li>Sintomo principale</li>
  <li>Vissuti emotivi frequenti (frustrazione, vergogna, senso di inadeguatezza)</li>
  <li>Effetti sulla vita di coppia</li>
</ul>

<h2>Le cause: un mosaico</h2>
<p>Le cause raramente sono una sola. Vale la pena distinguere:</p>

<h3>Cause psicologiche</h3>
<p>Ansia da prestazione, storia di traumi, educazione restrittiva, difficoltà relazionali.</p>

<h3>Cause fisiologiche</h3>
<p>Ormoni, farmaci (in particolare SSRI), condizioni ginecologiche o neurologiche.</p>

<h3>Cause relazionali</h3>
<p>Comunicazione, gestione del conflitto, dinamiche di potere nella coppia.</p>

<h2>Come si affronta</h2>
<ol>
  <li><strong>Valutazione integrata</strong> — sessuologo + medico di riferimento per escludere cause organiche.</li>
  <li><strong>Psicoeducazione</strong> — riscoprire il proprio corpo, imparare a distinguere piacere e prestazione.</li>
  <li><strong>Interventi mirati</strong> — mindfulness sessuale, esercizi di sensate focus, terapia di coppia se necessario.</li>
</ol>

<h2>Quando rivolgersi a uno specialista</h2>
<p>Se la difficoltà persiste da mesi, se genera sofferenza personale o di coppia, se ti stai chiedendo se "sei sbagliata" — è il momento di parlarne. La sessuologia clinica ha strumenti concreti e in Italia i tempi di risposta sono buoni.</p>

<p><em>Su FunzionaBene puoi prenotare una prima consulenza con un/a sessuologo/a iscritto all'Albo in meno di 48 ore.</em></p>
`,
    tags: "guida clinica, sessuologia, disfunzioni",
  },
  {
    id: "ricerca",
    label: "Ricerca / Approfondimento",
    description: "Approfondimento su un tema di attualità o su nuove evidenze scientifiche.",
    titolo: "Cosa dice la ricerca sul desiderio dopo i 50 anni",
    contenuto: `<p class="intro">La convinzione che il desiderio sessuale sparisca dopo una certa età è uno dei miti più duri a morire. Le ricerche degli ultimi vent'anni raccontano una storia diversa e più interessante.</p>

<h2>Il fenomeno oggi</h2>
<p>Contestualizza il tema: dati demografici, cambiamento culturale, cosa è diverso rispetto a 30 anni fa. Uno o due dati statistici affidabili.</p>

<h2>Cosa dice la ricerca</h2>
<p>Presenta 2-3 studi recenti in modo divulgativo — non serve tecnicismo, serve chiarezza:</p>

<ul>
  <li><strong>Studio 1</strong> (autore, anno, campione): cosa ha trovato.</li>
  <li><strong>Studio 2</strong> (autore, anno, campione): cosa ha trovato.</li>
  <li><strong>Meta-analisi</strong> (se disponibile): la conclusione più solida.</li>
</ul>

<h2>Le implicazioni cliniche</h2>
<p>Cosa cambia — o dovrebbe cambiare — nel modo in cui accompagniamo le persone in studio:</p>

<h3>Cosa <em>non</em> è patologia</h3>
<p>Ripulisci il campo: variazioni normali del desiderio, differenze individuali, adattamenti fisiologici.</p>

<h3>Cosa merita attenzione</h3>
<p>Segnali che indicano invece un intervento specialistico.</p>

<h2>Conclusioni</h2>
<p>Chiudi con una riflessione sintetica e un invito ad approfondire — magari collegato a un altro articolo del blog o a una consulenza.</p>

<h2>Riferimenti</h2>
<ol>
  <li>Autore, Anno. <em>Titolo articolo.</em> Rivista, vol(n), pp.</li>
  <li>Autore, Anno. <em>Titolo articolo.</em> Rivista, vol(n), pp.</li>
</ol>
`,
    tags: "ricerca, approfondimento, sessuologia",
  },
];
