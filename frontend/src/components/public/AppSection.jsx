import { motion } from "framer-motion";
import { Sparkles, BookOpen, Calendar, MessageCircle, Smile, Lock, Bell } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

/**
 * AppSection — homepage block introducing the upcoming mobile app.
 * Design: hand-drawn SVG phone, brand mascots inhabit the screen,
 * floating feature pills around. "Presto disponibile" badge.
 */
const FEATURES = [
  { icon: BookOpen, label: "Psicoeducazione su misura", desc: "Articoli, mini-lezioni e podcast scelti dal tuo terapeuta." },
  { icon: Calendar, label: "I tuoi appuntamenti, ovunque", desc: "Promemoria, riprogrammazione, accesso video — in tre tap." },
  { icon: Smile, label: "Diario emozionale", desc: "Note brevi che il tuo terapeuta legge prima della sessione, se vuoi." },
  { icon: MessageCircle, label: "Coach Sessuale", desc: "Un compagno digitale per domande tra una sessione e l'altra. Mai un sostituto del terapeuta." },
];

export default function AppSection() {
  return (
    <section
      className="relative max-w-7xl mx-auto px-6 lg:px-10 py-24 lg:py-32"
      data-testid="app-section"
    >
      {/* soft warm halo behind everything */}
      <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-[900px] h-[600px] rounded-full bg-[#F58A1F]/8 blur-3xl pointer-events-none" />

      <div className="relative grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        {/* ── LEFT: copy & features ── */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          className="lg:col-span-6"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white border border-[#0A0A0A]/15 mb-6">
            <Bell className="w-3.5 h-3.5 text-[#F58A1F]" />
            <span className="text-xs tracking-[0.2em] uppercase text-[#0A0A0A]">Presto disponibile</span>
          </div>
          <h2 className="font-serif text-4xl lg:text-6xl text-[#0A0A0A] leading-[1.05] tracking-tight">
            La tua app.<br />
            <em className="not-italic text-[#F58A1F]">Per i momenti tra una sessione e l&apos;altra.</em>
          </h2>
          <p className="mt-8 text-lg text-[#0A0A0A]/70 leading-relaxed max-w-xl">
            Un compagno digitale discreto, in italiano, che ti accompagna ogni giorno —
            senza mai sostituire il tuo terapeuta. Pensata insieme a chi la userà,
            sviluppata da chi sa cosa significa <strong className="text-[#0A0A0A]">prendersi cura davvero</strong>.
          </p>

          <ul className="mt-10 space-y-5">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <motion.li
                  key={f.label}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: i * 0.08 }}
                  className="flex gap-4 items-start"
                  data-testid={`app-feature-${i}`}
                >
                  <span className="flex-shrink-0 w-10 h-10 rounded-2xl bg-gradient-to-br from-[#F58A1F]/20 to-[#F5D419]/20 border border-[#F58A1F]/30 flex items-center justify-center mt-0.5">
                    <Icon className="w-4 h-4 text-[#0A0A0A]" />
                  </span>
                  <div>
                    <div className="font-serif text-lg text-[#0A0A0A]">{f.label}</div>
                    <div className="text-sm text-[#0A0A0A]/65 leading-relaxed">{f.desc}</div>
                  </div>
                </motion.li>
              );
            })}
          </ul>

          <div className="mt-10 flex flex-wrap gap-3 items-center">
            <a
              href="/scarica-app"
              data-testid="cta-scarica-app-section"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#0A0A0A] text-white text-sm font-semibold hover:bg-[#0A0A0A]/85 transition-colors"
            >
              <Sparkles className="w-4 h-4 text-[#F5D419]" /> Scarica l&apos;app
            </a>
            <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-[#0A0A0A]/12 text-xs text-[#0A0A0A]/75">
              <Lock className="w-3.5 h-3.5" /> Sicura, criptata, GDPR
            </span>
            <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-[#0A0A0A]/12 text-xs text-[#0A0A0A]/75">
              <Sparkles className="w-3.5 h-3.5" /> iOS &amp; Android
            </span>
          </div>
        </motion.div>

        {/* ── RIGHT: hand-drawn phone with inhabited screen ── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="lg:col-span-6 relative flex justify-center"
        >
          {/* Floating feature chips around the phone */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -left-2 lg:-left-8 top-12 z-20 inline-flex items-center gap-2.5 bg-white rounded-2xl shadow-lg border border-[#0A0A0A]/10 px-3 py-2.5 max-w-[200px]"
          >
            <span className="w-7 h-7 rounded-full bg-[#C8B5E0] flex items-center justify-center text-xs flex-shrink-0">📔</span>
            <div className="whitespace-nowrap">
              <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/55 leading-none">oggi</div>
              <div className="text-xs text-[#0A0A0A] font-medium leading-tight mt-0.5">Diario aggiornato</div>
            </div>
          </motion.div>

          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
            className="absolute right-2 lg:right-0 top-32 z-20 inline-flex items-center gap-2.5 bg-white rounded-2xl shadow-lg border border-[#0A0A0A]/10 px-3 py-2.5 max-w-[230px]"
          >
            <span className="w-7 h-7 rounded-full bg-[#8FC8D8] flex items-center justify-center text-xs flex-shrink-0">🎧</span>
            <div className="whitespace-nowrap">
              <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/55 leading-none">consigliato</div>
              <div className="text-xs text-[#0A0A0A] font-medium leading-tight mt-0.5">Esercizio respirazione · 5&apos;</div>
            </div>
          </motion.div>

          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
            className="absolute -right-2 lg:-right-6 bottom-20 z-20 inline-flex items-center gap-2.5 bg-white rounded-2xl shadow-lg border border-[#0A0A0A]/10 px-3 py-2.5 max-w-[210px]"
          >
            <span className="w-7 h-7 rounded-full bg-[#F58A1F] flex items-center justify-center text-xs flex-shrink-0">✨</span>
            <div className="whitespace-nowrap">
              <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/55 leading-none">domani 10:00</div>
              <div className="text-xs text-[#0A0A0A] font-medium leading-tight mt-0.5">Dr. Rossi · Sessione</div>
            </div>
          </motion.div>

          {/* The phone */}
          <PhoneFrame />
        </motion.div>
      </div>
    </section>
  );
}

/* ─────────── PHONE FRAME (custom SVG-styled) ─────────── */
function PhoneFrame() {
  return (
    <div className="relative w-[300px] sm:w-[340px] aspect-[9/19] rounded-[2.8rem] bg-[#0A0A0A] p-3 shadow-2xl shadow-[#F58A1F]/20">
      {/* speaker */}
      <div className="absolute top-3 left-1/2 -translate-x-1/2 w-24 h-5 bg-[#0A0A0A] rounded-b-2xl z-10 flex items-center justify-center">
        <span className="w-12 h-1 bg-[#0A0A0A] rounded-full" />
      </div>

      {/* screen */}
      <div className="relative w-full h-full rounded-[2.2rem] bg-gradient-to-b from-[#FFF8E7] to-[#FBE7B0] overflow-hidden">
        {/* status bar */}
        <div className="flex items-center justify-between px-6 pt-3 pb-2 text-[10px] text-[#0A0A0A]/70 font-medium">
          <span>09:41</span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[#0A0A0A]/20" />
            <span>100%</span>
          </span>
        </div>

        {/* app header */}
        <div className="px-5 pt-2 pb-3 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/55">Buongiorno,</div>
            <div className="font-serif text-lg text-[#0A0A0A] leading-tight">Anna</div>
          </div>
          <div className="w-9 h-9 rounded-full bg-[#F58A1F]/20 flex items-center justify-center">
            <Mascotte name="curioso" size={28} />
          </div>
        </div>

        {/* "today's session" card */}
        <div className="mx-4 mb-3 bg-[#0A0A0A] rounded-2xl p-3.5 text-white">
          <div className="text-[9px] uppercase tracking-widest text-white/55 mb-0.5">Oggi · 18:00</div>
          <div className="font-serif text-base leading-tight">Sessione con il Dr. Bianchi</div>
          <div className="mt-2.5 flex items-center justify-between">
            <span className="text-[10px] text-white/65">Online · 50 minuti</span>
            <span className="text-[10px] bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-bold px-2.5 py-1 rounded-full">Entra</span>
          </div>
        </div>

        {/* chat preview "Coach Sessuale" */}
        <div className="mx-4 bg-white/80 backdrop-blur rounded-2xl p-3.5 border border-[#0A0A0A]/8">
          <div className="flex items-center gap-2 mb-2.5">
            <span className="w-6 h-6 rounded-full bg-[#E89B9F] flex items-center justify-center text-[9px] font-bold text-white">CS</span>
            <span className="text-[11px] font-medium text-[#0A0A0A]">Coach Sessuale</span>
            <span className="text-[9px] text-[#0A0A0A]/45 ml-auto">ieri</span>
          </div>
          <div className="space-y-1.5">
            <div className="bg-[#0A0A0A]/6 rounded-lg rounded-bl-sm p-2 text-[10px] text-[#0A0A0A]/80 leading-snug max-w-[85%]">
              Come ti senti oggi rispetto a ieri?
            </div>
            <div className="ml-auto bg-gradient-to-br from-[#F58A1F]/85 to-[#F5D419]/85 rounded-lg rounded-br-sm p-2 text-[10px] text-[#0A0A0A] font-medium leading-snug max-w-[80%]">
              Meglio, anche se ho avuto un momento difficile in pausa pranzo.
            </div>
            <div className="bg-[#0A0A0A]/6 rounded-lg rounded-bl-sm p-2 text-[10px] text-[#0A0A0A]/80 leading-snug max-w-[85%]">
              Vuoi annotarlo nel diario? Lo leggeremo insieme stasera.
            </div>
          </div>
        </div>

        {/* bottom nav */}
        <div className="absolute bottom-3 left-0 right-0 px-6 flex items-center justify-around">
          {[
            { icon: "🏠", active: true },
            { icon: "📔", active: false },
            { icon: "💬", active: false },
            { icon: "👤", active: false },
          ].map((n, i) => (
            <span
              key={i}
              className={`w-9 h-9 rounded-2xl flex items-center justify-center text-base ${
                n.active ? "bg-[#0A0A0A]" : "bg-transparent"
              }`}
            >
              <span className={n.active ? "grayscale-0" : "grayscale opacity-50"}>{n.icon}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
