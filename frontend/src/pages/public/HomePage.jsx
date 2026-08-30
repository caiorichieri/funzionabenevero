import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight, ShieldCheck, Heart, Award, Lock, Sparkles, Check, X,
  Quote, AlertCircle, MessageCircle
} from "lucide-react";
import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { AREE_INTERVENTO, AREE_CATEGORIE, TESTIMONIANZE } from "@/data/areeIntervento";
import Mascotte from "@/components/shared/Mascotte";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import AppSection from "@/components/public/AppSection";
import SEO from "@/components/shared/SEO";

const HERO_BG = "/home-daily.jpg";

const STEPS = [
  { n: "01", title: "Compila il questionario", desc: "5 domande riservate, in 2 minuti. Nessun giudizio, nessun imbarazzo.", mascot: "embrulhado", anim: "float" },
  { n: "02", title: "Ricevi 3 abbinamenti", desc: "Ti presentiamo i 3 sessuologi più affini al tuo profilo e ai tuoi obiettivi. Scegli tu con chi iniziare.", mascot: "pensativo", anim: "breathe" },
  { n: "03", title: "Inizia il percorso", desc: "Online, nel tuo spazio sicuro — in modalità classica o immersiva, scegli tu insieme al tuo terapeuta.", mascot: "saltitante", anim: "wiggle" },
];

const BENEFITS = [
  {
    titolo: "Iper-specialisti",
    descrizione: "Non ci occupiamo di tutto: solo di sessuologia. Questo ci rende unici — e davvero bravi in ciò che conta per te.",
    icon: Award,
  },
  {
    titolo: "Sessioni immersive",
    descrizione: "Prima piattaforma italiana a offrire sessioni terapeutiche immersive per disfunzioni, fobie e blocchi. Sempre guidate dal tuo terapeuta.",
    icon: Sparkles,
    highlight: true,
  },
  {
    titolo: "Parla senza filtri",
    descrizione: "Uno spazio dove non serve fare giri di parole. Anche i temi che non racconti a nessuno, qui trovano ascolto.",
    icon: MessageCircle,
  },
  {
    titolo: "Riservatezza assoluta",
    descrizione: "Cifratura end-to-end, segreto professionale, zero dati condivisi. La tua intimità è intima davvero.",
    icon: Lock,
  },
  {
    titolo: "Specialisti verificati",
    descrizione: "Ogni professionista è iscritto all'Albo degli Psicologi italiano con polizza assicurativa attiva. Verifichiamo tutto, periodicamente.",
    icon: ShieldCheck,
  },
];

const SERVE_LIST = [
  "Ansia da prestazione e blocchi sessuali",
  "Disfunzioni erettili, eiaculazione precoce",
  "Anorgasmia, dispareunia, vaginismo",
  "Cali del desiderio, differenze nella coppia",
  "Identità di genere, orientamento, percorsi di affermazione",
  "Traumi sessuali e abusi",
  "Dipendenze sessuali e da pornografia",
  "Sessualità nelle diverse fasi di vita (gravidanza, menopausa, terza età)",
];

const NON_SERVE_LIST = [
  "Emergenze psichiatriche acute (in questo caso: 112 o TP 02.2327.2327)",
  "Prescrizione di farmaci (non siamo psichiatri)",
  "Diagnosi mediche di malattie organiche",
];

export default function HomePage() {
  const [terapisti, setTerapisti] = useState([]);

  useEffect(() => {
    axios.get(`${API}/public/terapisti`).then(r => setTerapisti(r.data.slice(0, 3))).catch(() => {});
  }, []);

  return (
    <main data-testid="homepage" className="relative bg-transparent overflow-hidden">
      <SEO
        title="Psicologi e Sessuologi Online — 100% Sessuologia"
        description="Prima piattaforma italiana 100% dedicata alla sessuologia. Psicologi e sessuologi iscritti all'Albo, prima sessione entro 48 ore. Online, riservato, cifrato."
        path="/"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "MedicalBusiness",
          "name": "FunzionaBene",
          "url": "https://funzionabene.it",
          "logo": "https://funzionabene.it/assets/logo.png",
          "description": "Piattaforma italiana di consulenza sessuologica online con psicologi e sessuologi iscritti all'Albo.",
          "medicalSpecialty": ["Psychiatric", "Psychology", "Sexology"],
          "areaServed": { "@type": "Country", "name": "Italia" },
          "availableLanguage": ["it", "en"],
          "priceRange": "€49-€90",
          "sameAs": ["https://www.instagram.com/funzionabene.it"]
        }}
      />
      {/* ────────── ATMOSPHERIC BACKDROP — gold ↔ steel-blue blooms only ────────── */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        {/* Vibrant gold bloom top-left */}
        <div className="absolute -top-32 -left-32 w-[900px] h-[900px] rounded-full bg-[#0A0A0A]/8 blur-3xl" />
        {/* Steel-blue bloom bottom-right */}
        <div className="absolute -bottom-32 -right-32 w-[1000px] h-[1000px] rounded-full bg-[#6B8FA3]/18 blur-3xl" />
        {/* Mid gold accent */}
        <div className="absolute top-[20%] right-[15%] w-[500px] h-[500px] rounded-full bg-white/25 blur-3xl" />
        {/* Mid blue accent */}
        <div className="absolute top-[55%] left-[15%] w-[600px] h-[600px] rounded-full bg-[#6B8FA3]/20 blur-3xl" />
        {/* Lower gold warmth */}
        <div className="absolute bottom-[20%] left-[40%] w-[500px] h-[500px] rounded-full bg-white/22 blur-3xl" />
      </div>

      {/* ────────── HERO ────────── */}
      <section className="relative">

        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 pt-20 lg:pt-32 pb-28 lg:pb-40">
          {/* Hero mascots — floating decoratively on the side */}
          <div className="hidden lg:block absolute right-10 top-32 opacity-90 pointer-events-none">
            <Mascotte name="abbraccio" theme="light" size={180} animation="breathe" />
          </div>
          <div className="hidden xl:block absolute right-56 top-72 opacity-70 pointer-events-none">
            <Mascotte name="saltitante" theme="light" size={110} animation="float" />
          </div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="max-w-4xl relative z-10"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-[#0A0A0A]/15 text-[#0A0A0A] text-xs tracking-[0.2em] uppercase mb-8">
              <Sparkles className="w-3.5 h-3.5" />
              Sessuologia online · Riservata · Senza giudizio
            </div>

            <h1 className="font-serif text-5xl sm:text-6xl lg:text-7xl leading-[1.05] text-[#0A0A0A] tracking-tight">
              Parla di tutto.
              <br /><em className="text-[#0A0A0A] not-italic">Anche di quello.</em>
            </h1>

            <p className="mt-8 text-lg lg:text-xl text-[#0A0A0A]/65 leading-relaxed max-w-2xl">
              Sessuologia online con specialisti dedicati. Percorsi tradizionali, guidati dal tuo terapeuta,
              nel <strong className="text-[#0A0A0A]">tuo spazio sicuro</strong>. Sempre.
            </p>

            <div className="mt-12 flex flex-col sm:flex-row gap-4">
              <div className="flex flex-col items-start">
                <PrenotaSubitoCTA
                  testid="hero-prenota-cta"
                  label="Prenota subito"
                  className="!px-9 !py-4 !text-base shadow-lg hover:shadow-2xl ring-1 ring-[#F58A1F]/30"
                />
                <span className="mt-2 text-xs text-[#0A0A0A]/55 pl-1">Parla con uno specialista nelle prossime ore</span>
              </div>
              <Link
                to="/questionario"
                data-testid="hero-start-btn"
                className="group inline-flex items-center justify-center gap-3 px-8 py-4 border-[1.5px] border-[#0A0A0A] text-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white rounded-2xl tracking-wide transition-all self-start"
              >
                Inizia il Questionario
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>

            <div className="mt-16 flex flex-wrap items-center gap-x-10 gap-y-6 text-xs text-[#0A0A0A]/65">
              <span className="flex items-center gap-3">
                <Mascotte name="abbraccio" theme="light" size={36} animation="breathe" />
                Riservato e cifrato
              </span>
              <span className="flex items-center gap-3">
                <Mascotte name="pensativo" theme="light" size={36} animation="float" />
                Specialisti iscritti all&apos;Albo
              </span>
              <span className="flex items-center gap-3">
                <Mascotte name="peludo" theme="light" size={36} animation="wiggle" />
                100% sessuologia
              </span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ────────── LA TUA APP (Presto disponibile) — subito dopo l'hero ────────── */}
      <AppSection />

      {/* ────────── HOW IT WORKS ────────── */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32" data-testid="how-it-works">
        <div className="max-w-2xl mb-16">
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Come funziona il questionario</span>
          <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
            Tre passi.<br />Nessuna attesa infinita.
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {STEPS.map((s, i) => {
            return (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                data-testid={`step-${s.n}`}
                className="relative p-8 lg:p-10 brand-card"
              >
                {/* Glow on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-[#0A0A0A]/0 to-[#0A0A0A]/0 group-hover:from-[#0A0A0A]/4 group-hover:to-transparent transition-all duration-700 pointer-events-none" />
                <div className="relative flex items-start justify-between mb-6">
                  <span className="font-serif text-5xl text-[#0A0A0A]/30 group-hover:text-[#0A0A0A]/70 transition-colors">{s.n}</span>
                  <Mascotte name={s.mascot} theme="light" size={80} maxHeight={80} animation={s.anim} />
                </div>
                <h3 className="font-serif text-2xl text-[#0A0A0A] mb-3 relative">{s.title}</h3>
                <p className="text-[#0A0A0A]/65 text-sm leading-relaxed relative">{s.desc}</p>
              </motion.div>
            );
          })}
        </div>

        {/* Discreet bypass — for users who don't want to follow the questionnaire flow */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="mt-10 text-center"
        >
          <span className="text-sm text-[#0A0A0A]/60">Hai bisogno di parlare subito?{" "}</span>
          <PrenotaSubitoCTA
            variant="compact"
            testid="come-funziona-bypass"
            label="Prenota uno specialista disponibile ora →"
            className="!bg-transparent !text-[#0A0A0A] !shadow-none hover:!shadow-none !px-2 !py-1 !font-medium underline underline-offset-4 decoration-[#F58A1F] decoration-2 hover:decoration-4"
          />
        </motion.div>
      </section>

      {/* ────────── SEDUTE IMMERSIVE (DIFFERENZIATORE) ────────── */}
      <section className="relative" data-testid="immersive-section">
        {/* Subtle darker overlay for emphasis */}
        <div className="absolute inset-0 " />
        <div className="absolute -top-20 -right-40 w-[500px] h-[500px] rounded-full bg-white/20 blur-3xl pointer-events-none" />

        <div className="relative max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-36 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-[#0A0A0A]/15 text-[#0A0A0A] text-xs tracking-[0.2em] uppercase mb-8">
              <Sparkles className="w-3.5 h-3.5" /> Il nostro differenziale
            </div>
            <h2 className="font-serif text-4xl lg:text-6xl text-[#0A0A0A] leading-[1.05]">
              Sessioni immersive.<br /><em className="text-[#0A0A0A] not-italic">La terapia, reimmaginata.</em>
            </h2>
            <p className="mt-8 text-lg text-[#0A0A0A]/65 leading-relaxed max-w-2xl">
              La sessualità è un affare così intimo che richiede un ambiente altrettanto intimo:
              <strong className="text-[#0A0A0A]"> riservato, solo tuo</strong>. Parlare di sessualità è già difficile —
              farlo sostenendo lo sguardo di chi ti ascolta, a volte, lo è ancora di più.
            </p>
            <p className="mt-4 text-base text-[#0A0A0A]/65 leading-relaxed max-w-2xl">
              Nell&apos;ambiente immersivo il tuo terapeuta è sempre con te, ti guida in tempo reale come in una sessione
              normale, ma la relazione passa attraverso un avatar, non attraverso il suo sguardo diretto. E l&apos;ambiente
              stesso ti porta fuori dal contesto reale che ti circonda: resti al sicuro a casa tua, ma per la durata
              della sessione non sei più ancorato/a al tuo salotto, alle tue abitudini, a tutto ciò che quel luogo
              ti ricorda. <strong className="text-[#0A0A0A]">Uno spazio che, per la prima volta, è davvero soltanto tuo.</strong>
            </p>
            <p className="mt-5 text-sm text-[#0A0A0A]/55 italic">
              FunzionaBene è la prima piattaforma italiana a integrare sessioni immersive nei percorsi di sessuologia.
            </p>

            <div className="mt-10 grid sm:grid-cols-2 gap-6">
              <div>
                <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">76%</div>
                <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
                  dei pazienti, in studi su terapia espositiva per ansia e fobie, preferisce la realtà virtuale all&apos;esposizione tradizionale<sup>*</sup>
                </div>
              </div>
              <div>
                <div className="font-serif text-4xl lg:text-5xl text-[#0A0A0A]">9×</div>
                <div className="text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/65 mt-2">
                  tasso di rifiuto del trattamento più basso in VR rispetto all&apos;esposizione tradizionale<sup>*</sup>
                </div>
              </div>
            </div>

            <div className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-[#0A0A0A]/10 text-xs text-[#0A0A0A]/75">
              <Check className="w-3.5 h-3.5" /> Incluse nel tuo percorso, nessun servizio extra da attivare
            </div>

            <div className="mt-10 flex flex-wrap gap-4">
              <Link
                to="/sedute-immersive"
                data-testid="immersive-deep-link"
                className="inline-flex items-center gap-3 px-7 py-3.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm tracking-wide transition-all"
              >
                Scopri come funziona <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/questionario"
                className="inline-flex items-center gap-2 px-7 py-3.5 border border-[rgba(28,28,28,0.12)] text-[#0A0A0A] hover:bg-[rgba(28,28,28,0.04)] rounded-full text-sm tracking-wide transition-all"
              >
                Inizia un percorso
              </Link>
            </div>

            <p className="mt-6 text-xs text-[#0A0A0A]/65 leading-relaxed">
              <sup>*</sup> Garcia-Palacios A. et al. — <em>studio sull&apos;accettabilità dell&apos;esposizione in VR vs in vivo per fobie specifiche</em>. Meta-analisi JMIR 2022 sull&apos;efficacia della VR-CBT per disturbi d&apos;ansia.
            </p>
          </div>

          {/* Right side: VR mascot centerpiece — replaces the photo */}
          <div className="lg:col-span-5 flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.92 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.9, ease: "easeOut" }}
              className="relative flex items-center justify-center w-full"
              data-testid="immersive-vr-stage"
            >
              {/* Soft gold halo behind the mascot */}
              <div className="absolute w-[420px] h-[420px] rounded-full bg-white/22 blur-3xl" />
              <div className="absolute w-[260px] h-[260px] rounded-full bg-[#0A0A0A]/10 blur-2xl" />
              <Mascotte name="vr" theme="light" size={360} animation="breathe" />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ────────── AREE DI INTERVENTO ────────── */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32" data-testid="aree-intervento">
        <div className="flex items-end justify-between mb-12 flex-wrap gap-4">
          <div className="max-w-2xl">
            <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Aree di intervento</span>
            <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
              Temi che qui<br />si possono dire.
            </h2>
            <p className="mt-6 text-[#0A0A0A]/65 text-lg">
              Nessun argomento è fuori posto. Qualunque sia la tua storia, c&apos;è uno specialista preparato ad ascoltarla.
            </p>
          </div>
          <Link to="/aree-intervento" className="text-sm text-[#6B8FA3] hover:text-[#94B2C2] tracking-wide">
            Vedi tutte le aree →
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AREE_INTERVENTO.slice(0, 12).map((a, i) => {
            const cat = AREE_CATEGORIE[a.categoria] || {};
            return (
              <motion.div
                key={a.slug}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: (i % 6) * 0.05 }}
                data-testid={`area-${a.slug}`}
                className="group p-6 brand-card"
              >
                <div className="flex items-start justify-between mb-3">
                  <span
                    className="text-[10px] tracking-[0.2em] uppercase px-2 py-0.5 rounded-full border"
                    style={{ color: cat.color, borderColor: `${cat.color}40`, background: `${cat.color}10` }}
                  >
                    {cat.label}
                  </span>
                </div>
                <h3 className="font-serif text-xl text-[#0A0A0A] leading-tight mb-2 group-hover:text-[#0A0A0A] transition-colors">{a.titolo}</h3>
                <p className="text-xs text-[#0A0A0A]/65 leading-relaxed line-clamp-3">{a.descrizione}</p>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-10 text-center">
          <Link
            to="/aree-intervento"
            className="inline-flex items-center gap-2 px-6 py-3 border border-[rgba(28,28,28,0.12)] text-[#0A0A0A] hover:bg-[rgba(28,28,28,0.04)] rounded-full text-sm tracking-wide transition-all"
          >
            Esplora tutte le {AREE_INTERVENTO.length} aree <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>

      {/* ────────── PERCHÉ FUNZIONABENE ────────── */}
      <section className="relative" data-testid="perche-section">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div className="max-w-2xl mb-16">
            <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Perché FunzionaBene</span>
            <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
              Non per tutti.<br />Per chi vuole davvero uno specialista.
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {BENEFITS.map((b, i) => {
              const Icon = b.icon;
              return (
                <motion.div
                  key={b.titolo}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.08 }}
                  data-testid={`benefit-${i}`}
                  className={`p-7 rounded-3xl border transition-all ${
                    b.highlight
                      ? "bg-gradient-to-br from-white via-white to-white/80 border-[#0A0A0A]/30"
                      : "bg-white border-[#0A0A0A]/10 hover:border-[#6B8FA3]/40"
                  }`}
                >
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-5 ${b.highlight ? "bg-[#0A0A0A]/10" : "bg-white"}`}>
                    <Icon className={`w-5 h-5 ${b.highlight ? "text-[#0A0A0A]" : "text-[#6B8FA3]"}`} />
                  </div>
                  <h3 className="font-serif text-2xl text-[#0A0A0A] mb-3 leading-tight">{b.titolo}</h3>
                  <p className="text-sm text-[#0A0A0A]/65 leading-relaxed">{b.descrizione}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

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

      {/* ────────── A COSA SERVE / NON SERVE ────────── */}
      <section className="relative" data-testid="serve-section">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32 grid lg:grid-cols-2 gap-10">
          <div className="p-10 brand-card">
            <div className="inline-flex items-center gap-2 text-[#0A0A0A] text-xs tracking-[0.2em] uppercase mb-5">
              <Check className="w-4 h-4" /> Ecco per cosa siamo qui
            </div>
            <h3 className="font-serif text-3xl text-[#0A0A0A] mb-8">A cosa serve FunzionaBene</h3>
            <ul className="space-y-4">
              {SERVE_LIST.map((s, i) => (
                <li key={i} className="flex items-start gap-3 text-[#0A0A0A]/80 text-sm leading-relaxed">
                  <Check className="w-4 h-4 text-[#0A0A0A] flex-shrink-0 mt-0.5" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="p-10 bg-white/70 border border-[#0A0A0A]/10 rounded-3xl">
            <div className="inline-flex items-center gap-2 text-[#0A0A0A]/65 text-xs tracking-[0.2em] uppercase mb-5">
              <AlertCircle className="w-4 h-4" /> Onestà prima di tutto
            </div>
            <h3 className="font-serif text-3xl text-[#0A0A0A] mb-8">A cosa non serve</h3>
            <ul className="space-y-4">
              {NON_SERVE_LIST.map((s, i) => (
                <li key={i} className="flex items-start gap-3 text-[#0A0A0A]/65 text-sm leading-relaxed">
                  <X className="w-4 h-4 text-[#C77474] flex-shrink-0 mt-0.5" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8 pt-6 border-t border-[#0A0A0A]/10">
              <Link to="/emergenze" className="text-sm text-[#0A0A0A] hover:text-[#0A0A0A]/70 inline-flex items-center gap-2">
                Se stai vivendo un&apos;emergenza → consulta i numeri di aiuto
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ────────── THERAPISTS PREVIEW ────────── */}
      {terapisti.length > 0 && (
        <section className="max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32" data-testid="therapists-preview">
          <div className="flex items-end justify-between mb-12 flex-wrap gap-4">
            <div>
              <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">I nostri specialisti</span>
              <h2 className="mt-4 font-serif text-4xl lg:text-5xl text-[#0A0A0A]">Professionisti, umani.</h2>
            </div>
            <Link to="/questionario" className="text-sm text-[#6B8FA3] hover:text-[#94B2C2] tracking-wide">
              Trova il tuo sessuologo →
            </Link>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {terapisti.map((t, i) => (
              <motion.div
                key={t._id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                data-testid={`therapist-preview-${i}`}
                className="p-8 brand-card"
              >
                {t.foto_url ? (
                  <img src={t.foto_url} alt={`${t.nome} ${t.cognome}`} className="w-20 h-20 rounded-full object-cover border border-[#0A0A0A]/10 mb-6" />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#0A0A0A]/10 to-[#6B8FA3]/15 border border-[#0A0A0A]/10 flex items-center justify-center mb-6">
                    <span className="font-serif text-3xl text-[#0A0A0A]">
                      {(t.nome || "?")[0]}{(t.cognome || "?")[0]}
                    </span>
                  </div>
                )}
                <h3 className="font-serif text-2xl text-[#0A0A0A]">Dr. {t.nome} {t.cognome}</h3>
                <p className="text-xs tracking-[0.15em] uppercase text-[#6B8FA3] mt-1">
                  {t.anni_esperienza ? `${t.anni_esperienza} anni di esperienza` : "Specialista"}
                </p>
                {Array.isArray(t.specializzazioni) && t.specializzazioni.length > 0 && (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {t.specializzazioni.slice(0, 2).map((s) => (
                      <span key={s} className="text-xs px-3 py-1 rounded-full bg-white text-[#0A0A0A] border border-[#0A0A0A]/15">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* ────────── CTA BAND ────────── */}
      <section className="max-w-7xl mx-auto px-6 lg:px-10 pb-24 lg:pb-32" data-testid="cta-band">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-white via-white to-[#E9D628]/30 border border-[#0A0A0A]/15 p-12 lg:p-20">
          <div className="absolute -top-20 -right-20 w-[400px] h-[400px] rounded-full bg-white/20 blur-3xl" />
          <div className="hidden md:block absolute right-12 bottom-12 lg:right-20 lg:bottom-20 opacity-80">
            <Mascotte name="abbraccio" theme="light" size={160} animation="breathe" />
          </div>
          <div className="relative max-w-2xl">
            <h2 className="font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">
              Un primo passo.<br />Il più difficile, il più importante.
            </h2>
            <p className="mt-6 text-[#0A0A0A]/65 text-lg leading-relaxed">
              Il questionario richiede 2 minuti. Puoi interromperlo in qualsiasi momento. Nessuna carta richiesta per iniziare.
            </p>
            <Link
              to="/questionario"
              data-testid="cta-start-btn"
              className="mt-10 inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg tracking-wide transition-all"
            >
              Inizia ora <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
