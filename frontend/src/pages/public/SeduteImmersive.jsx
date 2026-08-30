import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight, Check, Home, Shield, Award, Headphones } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import SEO from "@/components/shared/SEO";

const BENEFITS = [
  {
    titolo: "Esposizione graduale",
    descrizione: "Per chi soffre di fobie, ansia da prestazione o blocchi sessuali: il terapeuta ti guida in scenari immersivi progressivi, rispettando i tuoi tempi.",
    img: "/benefit-esposizione.jpg",
  },
  {
    titolo: "Desensibilizzazione",
    descrizione: "Riduzione progressiva di paure, ansie e blocchi legati alla sessualità. L'ambiente controllato rende il percorso più sicuro e meno invasivo rispetto ai metodi tradizionali.",
    img: "/benefit-desensibilizzazione.jpg",
  },
  {
    titolo: "Consapevolezza corporea",
    descrizione: "Mindfulness sessuale guidata da esperienze sensoriali immersive — un supporto utile per anorgasmia, vaginismo e disconnessione dal piacere.",
    img: "/benefit-consapevolezza.jpg",
  },
  {
    titolo: "Coppia",
    descrizione: "Esercizi immersivi condivisi per coppie in terapia — per ricostruire intimità, comunicazione e linguaggi sensoriali comuni.",
    img: "/benefit-coppia.jpg",
  },
];

const FAQ = [
  {
    q: "Serve comprare un visore?",
    a: "No. Le sessioni immersive funzionano anche direttamente dal tuo smartphone o tablet, in modalità guidata. Il visore è un'opzione aggiuntiva che alcuni pazienti preferiscono per un'esperienza più profonda. È il tuo terapeuta a consigliarti la modalità più adatta.",
  },
  {
    q: "È sempre guidata da un professionista?",
    a: "Assolutamente sì. La sessione immersiva non è un'app di auto-aiuto: è un intervento clinico condotto in tempo reale dal tuo terapeuta. Non esistono percorsi automatizzati né 'fai-da-te'.",
  },
  {
    q: "È adatta a tutti?",
    a: "No, e questa è un'informazione importante. L'immersività non è indicata per tutti i casi o tutte le persone: il terapeuta valuta con te se può essere parte del tuo percorso. Quando non è adatta, si procede con sessioni tradizionali (altrettanto efficaci).",
  },
  {
    q: "Ha costi aggiuntivi?",
    a: "No. Quando il terapeuta decide di integrare una sessione immersiva nel tuo percorso, il costo è lo stesso di una sessione tradizionale. Nessun upcharge, nessuna sorpresa.",
  },
  {
    q: "Quali sono le evidenze scientifiche?",
    a: "Numerosi studi peer-reviewed dimostrano l'efficacia delle tecnologie immersive in psicoterapia, in particolare per fobie, disturbi d'ansia, traumi e disfunzioni sessuali ansiose. Ti invitiamo a consultare Riva G. et al. (2016), Freeman D. et al. (2017), Wiederhold B.K. (per la sessuologia), tra gli altri.",
  },
  {
    q: "E la privacy?",
    a: "Le sessioni immersive sono parte della videochiamata con il tuo terapeuta, quindi protette dallo stesso livello di cifratura e dallo stesso segreto professionale di una sessione tradizionale. Nessun dato sensoriale viene registrato o conservato.",
  },
];

export default function SeduteImmersive() {
  return (
    <main className="min-h-[calc(100vh-80px)] relative bg-transparent overflow-hidden" data-testid="immersive-page">
      <SEO
        title="Sedute immersive — VR terapeutica per fobie e ansia sessuale"
        description="Prima piattaforma italiana di sessioni immersive per disfunzioni, ansia da prestazione e fobie sessuali. Sempre guidate dal terapeuta. Evidence-based."
        path="/sedute-immersive"
      />
      {/* Continuous atmospheric backdrop — gold ↔ blue blooms only */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-32 -left-32 w-[900px] h-[900px] rounded-full bg-[#0A0A0A]/8 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-[1000px] h-[1000px] rounded-full bg-[#6B8FA3]/18 blur-3xl" />
        <div className="absolute top-[50%] right-[20%] w-[500px] h-[500px] rounded-full bg-white/22 blur-3xl" />
      </div>

      {/* Hero */}
      <section className="relative">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#E9D628]" />
        </div>

        <div className="relative max-w-5xl mx-auto px-6 lg:px-10 py-20 lg:py-32">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="relative"
          >
            {/* Floating mascot peeking from the side */}
            <div className="hidden lg:block absolute -right-4 top-8 opacity-90">
              <Mascotte name="sereno" theme="light" size={170} animation="float" />
            </div>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-[#0A0A0A]/15 text-[#0A0A0A] text-xs tracking-[0.2em] uppercase mb-8">
              <Sparkles className="w-3.5 h-3.5" /> Il nostro differenziale
            </div>

            <h1 className="font-serif text-5xl sm:text-6xl lg:text-7xl leading-[1.05] text-[#0A0A0A] tracking-tight max-w-3xl">
              Sessioni immersive.<br /><em className="text-[#0A0A0A] not-italic">La terapia, reimmaginata.</em>
            </h1>

            <p className="mt-8 text-lg lg:text-xl text-[#0A0A0A]/75 leading-relaxed max-w-3xl">
              La sessualità è un affare così intimo che richiede un ambiente altrettanto intimo:
              <strong className="text-[#0A0A0A]"> riservato, solo tuo</strong>. Parlare di sessualità è già difficile —
              farlo sostenendo lo sguardo di chi ti ascolta, a volte, lo è ancora di più.
            </p>
            <p className="mt-4 text-base lg:text-lg text-[#0A0A0A]/70 leading-relaxed max-w-3xl">
              Nell&apos;ambiente immersivo il tuo terapeuta è sempre con te, ti guida in tempo reale come in una sessione
              normale, ma la relazione passa attraverso un avatar, non attraverso il suo sguardo diretto.
              <strong className="text-[#0A0A0A]"> Uno spazio che, per la prima volta, è davvero soltanto tuo.</strong>
            </p>
            <p className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-[#0A0A0A]/12 text-xs text-[#0A0A0A]/75">
              <Check className="w-3.5 h-3.5" /> Incluse nel tuo percorso, nessun servizio extra da attivare
            </p>
          </motion.div>
        </div>
      </section>

      {/* Stats */}
      <section className="max-w-6xl mx-auto px-6 lg:px-10 py-20" data-testid="immersive-stats">
        <div className="grid md:grid-cols-3 gap-8">
          <div className="brand-card !p-8">
            <div className="font-serif text-5xl lg:text-6xl text-[#0A0A0A]">76%</div>
            <p className="mt-4 text-sm text-[#0A0A0A]/75 leading-relaxed">
              dei pazienti, in studi su terapia espositiva per ansia e fobie, preferisce la realtà virtuale all&apos;esposizione tradizionale.
            </p>
          </div>
          <div className="brand-card !p-8">
            <div className="font-serif text-5xl lg:text-6xl text-[#0A0A0A]">9×</div>
            <p className="mt-4 text-sm text-[#0A0A0A]/75 leading-relaxed">
              tasso di rifiuto del trattamento più basso in VR rispetto all&apos;esposizione tradizionale.
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
          Fonti: Garcia-Palacios A. et al. — <em>studio sull&apos;accettabilità dell&apos;esposizione in VR vs in vivo per fobie specifiche</em>. Meta-analisi JMIR 2022 sull&apos;efficacia della VR-CBT per disturbi d&apos;ansia.
        </p>
      </section>

      {/* How it works */}
      <section className="max-w-5xl mx-auto px-6 lg:px-10 py-20" data-testid="immersive-how">
        <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Come funziona</span>
        <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight mb-14">
          Il terapeuta decide.<br />Tu vivi l&apos;esperienza.
        </h2>

        <ol className="space-y-10 border-l border-[#0A0A0A]/10 pl-10">
          {[
            { t: "Il terapeuta valuta se è adatta al tuo percorso", d: "Non tutte le persone o tutti i casi beneficiano della modalità immersiva. La valutazione clinica è sempre il primo passo." },
            { t: "Scegli la modalità che preferisci", d: "Dal tuo schermo (smartphone, tablet, computer) con effetto immersivo guidato, oppure con un visore se preferisci un coinvolgimento più profondo." },
            { t: "Il terapeuta guida la sessione in tempo reale", d: "Durante la videochiamata, il terapeuta attiva l'ambiente immersivo sincronizzato. Puoi interrompere in ogni momento: hai sempre il controllo." },
            { t: "Rielaborazione terapeutica", d: "Dopo l'esperienza, si torna al dialogo con il terapeuta per dare senso a quanto hai vissuto. È qui che avviene il cambiamento." },
          ].map((s, i) => (
            <li key={i} className="relative" data-testid={`immersive-step-${i}`}>
              <div className="absolute -left-[53px] top-0 w-10 h-10 rounded-full bg-[#0A0A0A] text-white font-medium flex items-center justify-center font-serif text-lg">
                {i + 1}
              </div>
              <h3 className="font-serif text-2xl text-[#0A0A0A] mb-2">{s.t}</h3>
              <p className="text-[#0A0A0A]/65 leading-relaxed">{s.d}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Use cases */}
      <section className="relative py-20 lg:py-28" data-testid="immersive-usecases">
        <div className="max-w-6xl mx-auto px-6 lg:px-10">
          <div className="max-w-2xl mb-14">
            <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Applicazioni cliniche</span>
            <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
              Quando l&apos;immersivo fa la differenza.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-5">
            {BENEFITS.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="brand-card group overflow-hidden !p-0"
              >
                {b.img && (
                  <div className="relative aspect-[16/9] overflow-hidden">
                    <img
                      src={b.img}
                      alt=""
                      aria-hidden="true"
                      loading="lazy"
                      className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                      data-testid={`benefit-img-${i}`}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0A]/12 via-white/50 to-transparent" />
                  </div>
                )}
                <div className="p-7">
                  <h3 className="font-serif text-2xl text-[#0A0A0A] mb-3">{b.titolo}</h3>
                  <p className="text-[#0A0A0A]/65 text-sm leading-relaxed">{b.descrizione}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust signals */}
      <section className="max-w-5xl mx-auto px-6 lg:px-10 py-20" data-testid="immersive-trust">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: Home, titolo: "Dal tuo salotto", desc: "Nessuno spostamento, nessuna sala d'attesa. Il tuo spazio sicuro." },
            { icon: Shield, titolo: "Riservato per costruzione", desc: "Le sessioni non vengono registrate. Comunicazione cifrata end-to-end." },
            { icon: Award, titolo: "Solo evidence-based", desc: "Tecniche supportate da ricerca peer-reviewed. Zero marketing vuoto." },
            { icon: Check, titolo: "Sempre incluse", desc: "Le sessioni immersive sono comprese nel tuo percorso, senza costi aggiuntivi." },
            { icon: Headphones, titolo: "Interrompibile sempre", desc: "Hai il controllo totale. Esci quando vuoi, senza spiegazioni." },
            { icon: Sparkles, titolo: "Opzionale", desc: "Se non fa per te, il percorso tradizionale è altrettanto efficace." },
          ].map((p, i) => {
            const Icon = p.icon;
            return (
              <div key={i} className="p-5 bg-white/20 border border-[#0A0A0A]/10 rounded-2xl">
                <Icon className="w-5 h-5 text-[#0A0A0A] mb-3" />
                <div className="font-serif text-lg text-[#0A0A0A] mb-1">{p.titolo}</div>
                <div className="text-xs text-[#0A0A0A]/60 leading-relaxed">{p.desc}</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 lg:px-10 py-20 lg:py-24" data-testid="immersive-faq">
        <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Domande frequenti</span>
        <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight mb-10">Dubbi? È normale.</h2>

        <div className="divide-y divide-white/10 border-t border-b border-[#0A0A0A]/10">
          {FAQ.map((f, i) => (
            <details key={i} className="group py-6" data-testid={`immersive-faq-${i}`}>
              <summary className="cursor-pointer list-none flex items-start justify-between gap-4">
                <span className="font-serif text-xl text-[#0A0A0A] group-hover:text-[#0A0A0A] transition-colors">{f.q}</span>
                <span className="text-[#6B8FA3] text-2xl font-light mt-[-6px] group-open:rotate-45 transition-transform">+</span>
              </summary>
              <p className="mt-4 text-[#0A0A0A]/75 leading-relaxed">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* References */}
      <section className="max-w-4xl mx-auto px-6 lg:px-10 py-12 mb-12" data-testid="immersive-references">
        <h3 className="text-xs tracking-[0.2em] uppercase text-[#0A0A0A] mb-4">Riferimenti scientifici</h3>
        <ul className="space-y-2 text-xs text-[#0A0A0A]/50 leading-relaxed">
          <li>• Riva G., Baños R.M., Botella C., Mantovani F., Gaggioli A. (2016). <em>Transforming experience: the potential of augmented reality and virtual reality for enhancing personal and clinical change.</em> Frontiers in Psychiatry.</li>
          <li>• Freeman D. et al. (2017). <em>Virtual reality in the assessment, understanding, and treatment of mental health disorders.</em> Psychological Medicine.</li>
          <li>• Diemer J., Alpers G.W., Peperkorn H.M., Shiban Y., Mühlberger A. (2015). <em>The impact of perception and presence on emotional reactions.</em> Frontiers in Psychology.</li>
          <li>• Wiederhold B.K., Wiederhold M.D. <em>Virtual reality therapy for anxiety disorders.</em> APA Press.</li>
          <li>• Optale G. et al. <em>Virtual reality exposure therapy for sexual dysfunction.</em> CyberPsychology &amp; Behavior.</li>
        </ul>
      </section>

      {/* CTA */}
      <section className="max-w-5xl mx-auto px-6 lg:px-10 pb-24">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0A0A0A]/10 via-[#0A0A0A]/10 to-white border border-[#0A0A0A]/25 p-10 lg:p-16 text-center">
          <h2 className="font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight max-w-2xl mx-auto">
            Pronto a provare una terapia diversa?
          </h2>
          <p className="mt-5 text-[#0A0A0A]/65 max-w-xl mx-auto">
            Il tuo percorso inizia da un questionario di 2 minuti. Il terapeuta giusto deciderà con te se integrare sessioni immersive.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <PrenotaSubitoCTA
              testid="immersive-prenota"
              label="Prenota subito"
            />
            <Link
              to="/questionario"
              data-testid="immersive-cta-btn"
              className="inline-flex items-center gap-3 px-8 py-4 border-[1.5px] border-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white text-[#0A0A0A] rounded-2xl tracking-wide transition-all"
            >
              Inizia il Questionario <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
