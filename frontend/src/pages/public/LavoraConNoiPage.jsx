import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Award, BookOpen, Heart, Sparkles } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";
import SEO from "@/components/shared/SEO";

const ROLES = [
  {
    icon: Award,
    titolo: "Terapeuti sessuologi",
    sottotitolo: "Iscritti all'Albo, con formazione specifica in sessuologia",
    desc: "Cerchiamo professionisti che vivono la sessuologia come specializzazione, non come complemento. La selezione include verifica documentale, colloquio clinico e revisione di casi.",
    requisiti: [
      "Laurea in Psicologia o Medicina + abilitazione",
      "Iscrizione all'Albo (Psicologi o Ordine dei Medici)",
      "Formazione specifica in sessuologia clinica (post-laurea)",
      "Assicurazione professionale RC attiva",
    ],
    cosaOffriamo: [
      "Pazienti pre-selezionati attraverso il nostro questionario",
      "Strumenti immersivi inclusi (visore opzionale fornito)",
      "Piattaforma video, calendario, fatturazione integrati",
      "Tariffe trasparenti — nessuna trattenuta opaca",
    ],
    mailto: "mailto:professionisti@funzionabene.it?subject=Candidatura%20terapeuta%20sessuologo",
    mascotName: "abbraccio",
  },
  {
    icon: BookOpen,
    titolo: "Psicologi giovani",
    sottotitolo: "Percorso di crescita affiancato",
    desc: "Hai meno di 5 anni di esperienza e vuoi specializzarti in sessuologia? Offriamo affiancamento clinico, formazione continua e un volume di lavoro gestibile per crescere bene, non in fretta.",
    requisiti: [
      "Laurea in Psicologia + abilitazione",
      "Iscrizione all'Albo da almeno 1 anno",
      "Interesse documentato per la sessuologia",
      "Disponibilità di almeno 8 ore settimanali",
    ],
    cosaOffriamo: [
      "Supervisione clinica mensile gratuita",
      "Accesso al network di colleghi senior",
      "Formazione interna su immersive therapy e sessuologia integrata",
      "Pazienti più semplici nelle prime fasi, complessità progressiva",
    ],
    mailto: "mailto:professionisti@funzionabene.it?subject=Candidatura%20psicologo%20junior",
    mascotName: "curioso",
  },
  {
    icon: Heart,
    titolo: "Stage e tesi",
    sottotitolo: "Per studenti dell'ultimo anno o appena laureati",
    desc: "Hai una tesi in cantiere o vuoi fare un periodo di stage in una piattaforma di sessuologia online? Accettiamo un numero limitato di stagisti all'anno, con un percorso formativo strutturato.",
    requisiti: [
      "Iscritto/a a Psicologia, Medicina o disciplina affine",
      "Indicazione del tema di interesse (sessuologia, salute digitale, VR therapy)",
      "Disponibilità minima 4 mesi continuativi",
    ],
    cosaOffriamo: [
      "Tutoraggio dedicato (almeno 2 ore settimanali)",
      "Dati anonimi per ricerca empirica (con approvazione etica)",
      "Lettera di referenze e possibile percorso post-stage",
    ],
    mailto: "mailto:professionisti@funzionabene.it?subject=Candidatura%20stage",
    mascotName: "saltitante",
  },
];

export default function LavoraConNoiPage() {
  return (
    <main className="min-h-[calc(100vh-80px)] relative bg-transparent overflow-hidden" data-testid="lavora-page">
      <SEO title="Lavora con Noi" description="Unisciti al team di psicologi e sessuologi di FunzionaBene. Scopri come candidarti per lavorare con noi online." path="/lavora-con-noi" />
      {/* Hero */}
      <section className="relative max-w-5xl mx-auto px-6 lg:px-10 py-20 lg:py-28">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-10 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Torna alla home
        </Link>

        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="relative">
          <div className="hidden md:block absolute right-0 top-0 opacity-90">
            <Mascotte name="peludo" size={170} animation="wiggle" />
          </div>
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Lavora con noi</span>
          <h1 className="mt-4 font-serif text-5xl sm:text-6xl lg:text-7xl text-[#0A0A0A] leading-[1.05] tracking-tight max-w-3xl">
            Costruiamo qualcosa di importante.<br />
            <em className="not-italic text-[#F58A1F]">Ti unisci?</em>
          </h1>
          <p className="mt-8 text-lg text-[#0A0A0A]/75 leading-relaxed max-w-2xl">
            FunzionaBene è una squadra in crescita — clinici, sviluppatori, designer — che vuole
            rendere la sessuologia italiana <strong className="text-[#0A0A0A]">accessibile, evidence-based e
            umana</strong>. Cerchiamo persone che condividono questa direzione.
          </p>
        </motion.div>
      </section>

      {/* Roles */}
      <section className="relative max-w-6xl mx-auto px-6 lg:px-10 pb-24 space-y-8" data-testid="roles">
        {ROLES.map((r, i) => {
          const Icon = r.icon;
          return (
            <motion.article
              key={r.titolo}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="brand-card !p-8 lg:!p-12"
              data-testid={`role-${i}`}
            >
              <div className="grid lg:grid-cols-12 gap-8 items-start">
                <div className="lg:col-span-3 flex lg:flex-col items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#F58A1F]/15 to-[#F5D419]/15 border border-[#F58A1F]/30 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-6 h-6 text-[#0A0A0A]" />
                  </div>
                  <Mascotte name={r.mascotName} size={90} animation="breathe" className="hidden lg:block" />
                </div>
                <div className="lg:col-span-9">
                  <h2 className="font-serif text-2xl lg:text-3xl text-[#0A0A0A] leading-tight">{r.titolo}</h2>
                  <p className="mt-1 text-sm tracking-wide text-[#0A0A0A]/55 italic">{r.sottotitolo}</p>
                  <p className="mt-5 text-base text-[#0A0A0A]/75 leading-relaxed">{r.desc}</p>

                  <div className="mt-7 grid sm:grid-cols-2 gap-7">
                    <div>
                      <div className="text-[10px] tracking-[0.2em] uppercase text-[#0A0A0A]/55 mb-3 flex items-center gap-2">
                        <Sparkles className="w-3 h-3" /> Cosa cerchiamo
                      </div>
                      <ul className="space-y-1.5 text-sm text-[#0A0A0A]/80">
                        {r.requisiti.map((req, idx) => (
                          <li key={idx} className="flex items-start gap-2 leading-relaxed">
                            <span className="text-[#0A0A0A]/40 mt-0.5">·</span> {req}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="text-[10px] tracking-[0.2em] uppercase text-[#0A0A0A]/55 mb-3 flex items-center gap-2">
                        <Sparkles className="w-3 h-3" /> Cosa offriamo
                      </div>
                      <ul className="space-y-1.5 text-sm text-[#0A0A0A]/80">
                        {r.cosaOffriamo.map((c, idx) => (
                          <li key={idx} className="flex items-start gap-2 leading-relaxed">
                            <span className="text-[#0A0A0A]/40 mt-0.5">·</span> {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <a
                    href={r.mailto}
                    data-testid={`role-${i}-cta`}
                    className="group mt-8 inline-flex items-center gap-3 px-7 py-3.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm tracking-wide transition-all"
                  >
                    Candidati per questo ruolo
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                  </a>
                </div>
              </div>
            </motion.article>
          );
        })}
      </section>

      {/* Closing note */}
      <section className="relative max-w-3xl mx-auto px-6 lg:px-10 pb-24 text-center">
        <p className="text-[#0A0A0A]/70 leading-relaxed">
          Non vedi il tuo ruolo nella lista, ma vuoi contribuire?
          Scrivici comunque a{" "}
          <a href="mailto:professionisti@funzionabene.it" className="text-[#F58A1F] hover:text-[#0A0A0A] underline underline-offset-4">
            professionisti@funzionabene.it
          </a>. Le persone curiose, in fondo, ci hanno sempre interessato di più.
        </p>
      </section>
    </main>
  );
}
