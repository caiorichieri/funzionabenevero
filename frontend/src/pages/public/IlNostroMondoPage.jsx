import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

/**
 * "Il nostro mondo" — interactive section showcasing the brand mascots.
 * Each mascot represents an emotion / situation. Hover/tap reveals a short story.
 */
const WORLD = [
  {
    name: "abbraccio",
    anim: "breathe",
    title: "Quando hai bisogno di sentirti accolto",
    desc: "Senza giudizio. Senza fretta. Il primo passo è sempre il più piccolo, e qui non sei mai solo/a a farlo.",
    color: "#F58A1F",
    href: "/chi-siamo",
  },
  {
    name: "sereno",
    anim: "float",
    title: "Quando vuoi ritrovare la calma",
    desc: "Ansia, stress, pensieri intrusivi. Esistono strumenti, e funzionano davvero — anche quando sembra impossibile.",
    color: "#FFFFFF",
    href: "/aree-intervento",
  },
  {
    name: "coppia",
    anim: "breathe",
    title: "Quando siete in due",
    desc: "Conflitti, distanza, intimità che si è raffreddata. Uno spazio sicuro per parlare di tutto, senza dover scegliere chi ha ragione.",
    color: "#E89B9F",
    href: "/aree-intervento",
  },
  {
    name: "pensativo",
    anim: "float",
    title: "Quando hai dei dubbi",
    desc: "Non sai se è il momento giusto? Il nostro questionario in 2 minuti ti aiuta a capire da dove partire — gratis, senza impegno.",
    color: "#C8B5E0",
    href: "/questionario",
  },
  {
    name: "curioso",
    anim: "wiggle",
    title: "Quando hai voglia di capire",
    desc: "Articoli evidence-based, scritti dai nostri specialisti. Per chi ha bisogno di parole prima ancora che di un appuntamento.",
    color: "#8FC8D8",
    href: "/blog",
  },
  {
    name: "saltitante",
    anim: "float",
    title: "Quando sei pronto/a a iniziare",
    desc: "Il primo incontro è online, in totale riservatezza, nel tuo spazio sicuro. Senza filtri, senza preamboli.",
    color: "#D4906E",
    href: "/questionario",
  },
  {
    name: "ovo",
    anim: "wiggle",
    title: "Quando ti senti fragile",
    desc: "Va bene così. La fragilità è il punto da cui si parte — non un difetto da nascondere. Anzi: è ciò che ci rende capaci di trasformazione.",
    color: "#B8D5E0",
    href: "/aree-intervento",
  },
  {
    name: "peludo",
    anim: "wiggle",
    title: "Quando l'esterno non ti rappresenta",
    desc: "Identità, corpo, desiderio. Qui si parla di te con rispetto — e con la competenza di chi conosce bene questi temi.",
    color: "#C8E0A8",
    href: "/aree-intervento",
  },
  {
    name: "embrulhado",
    anim: "breathe",
    title: "Quando hai voglia solo di un rifugio",
    desc: "Anche solo per oggi. Il tuo spazio è qui, quando vuoi tu. Non sempre bisogna parlare: a volte serve solo sapere che c'è un posto.",
    color: "#F5C0A8",
    href: "/sedute-immersive",
  },
];

export default function IlNostroMondoPage() {
  const [active, setActive] = useState(null);

  return (
    <main className="relative min-h-[calc(100vh-80px)] overflow-hidden" data-testid="il-nostro-mondo">
      {/* soft warm halos */}
      <div className="absolute -top-32 -left-32 w-[700px] h-[700px] rounded-full bg-white/25 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-[800px] h-[800px] rounded-full bg-[#F58A1F]/10 blur-3xl pointer-events-none" />

      {/* Hero */}
      <section className="relative max-w-6xl mx-auto px-6 lg:px-10 pt-16 lg:pt-24 pb-12">
        <Link to="/" className="flex w-fit items-center gap-2 text-sm text-[#0A0A0A]/65 hover:text-[#0A0A0A] mb-12" data-testid="back-home">
          ← Torna alla home
        </Link>
        <div>
          <span className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A]/70">Il nostro mondo</span>
          <h1 className="mt-4 font-serif text-4xl sm:text-5xl lg:text-6xl text-[#0A0A0A] leading-[1.05] tracking-tight">
            Nove personaggi.<br />
            <em className="not-italic text-[#F58A1F]">Nove modi di sentirsi.</em>
          </h1>
        </div>
        <p className="mt-6 text-lg text-[#0A0A0A]/70 max-w-2xl leading-relaxed">
          Ogni emozione ha la sua voce. Tocca un personaggio per scoprire dove ti porta.
          Quello giusto per oggi, forse, non sarà quello giusto per domani.
        </p>
      </section>

      {/* Mascots grid */}
      <section className="relative max-w-7xl mx-auto px-6 lg:px-10 pb-24">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 gap-6 lg:gap-8">
          {WORLD.map((m, i) => (
            <motion.button
              key={m.name}
              type="button"
              data-testid={`world-mascot-${m.name}`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06 }}
              onMouseEnter={() => setActive(m.name)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(m.name)}
              onBlur={() => setActive(null)}
              onClick={() => (window.location.href = m.href)}
              className="brand-card group text-left p-7 lg:p-9 min-h-[280px] flex flex-col cursor-pointer"
            >
              <div className="flex justify-center mb-4">
                <Mascotte name={m.name} size={130} animation={m.anim} />
              </div>
              <AnimatePresence mode="wait">
                {active === m.name ? (
                  <motion.div
                    key="open"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.25 }}
                    className="mt-auto"
                  >
                    <h3 className="font-serif text-lg lg:text-xl text-[#0A0A0A] leading-snug">{m.title}</h3>
                    <p className="mt-2 text-sm text-[#0A0A0A]/65 leading-relaxed line-clamp-3">{m.desc}</p>
                    <span className="mt-3 inline-flex items-center gap-1.5 text-xs tracking-wide text-[#0A0A0A] font-medium">
                      Scopri <ArrowRight className="w-3 h-3" />
                    </span>
                  </motion.div>
                ) : (
                  <motion.h3
                    key="closed"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-auto font-serif text-base lg:text-lg text-[#0A0A0A]/75 text-center"
                  >
                    {m.title.split(" ").slice(0, 4).join(" ")}…
                  </motion.h3>
                )}
              </AnimatePresence>
            </motion.button>
          ))}
        </div>

        {/* Closing CTA */}
        <div className="mt-20 text-center">
          <p className="text-[#0A0A0A]/70 mb-6 text-lg">
            Non ti sei riconosciuto in nessuno? <strong className="text-[#0A0A0A]">Ce ne sarà uno per te.</strong>
          </p>
          <Link
            to="/questionario"
            data-testid="world-cta"
            className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg tracking-wide transition-all"
          >
            Trova il tuo specialista <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
