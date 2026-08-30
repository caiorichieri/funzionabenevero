import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Mail, MessageCircle, Briefcase, HeartHandshake, FileText, MapPin } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";
import { TITOLARE, DPO, WHATSAPP_NUMBER, PHONE_DISPLAY } from "@/data/legalInfo";
import SEO from "@/components/shared/SEO";

const CONTATTI = [
  {
    icon: HeartHandshake,
    titolo: "Supporto pazienti",
    desc: "Per dubbi sul tuo percorso, prenotazioni, fatturazione o per parlare con qualcuno prima di iniziare. Rispondiamo entro 24 ore.",
    email: "supporto@funzionabene.it",
    color: "#F58A1F",
    mascotName: "abbraccio",
  },
  {
    icon: Briefcase,
    titolo: "Professionisti e candidature",
    desc: "Sei un/a sessuologo/a, psicologo/a o ricercatore/trice? Per candidature, partnership scientifiche e proposte di stage.",
    email: "professionisti@funzionabene.it",
    color: "#C8B5E0",
    mascotName: "pensativo",
  },
  {
    icon: FileText,
    titolo: "Stampa & istituzioni",
    desc: "Interviste, comunicati, collaborazioni con università, ASL o istituzioni. Per parlare di sessualità in modo serio.",
    email: "stampa@funzionabene.it",
    color: "#8FC8D8",
    mascotName: "curioso",
  },
];

export default function ContattiPage() {
  return (
    <main className="min-h-[calc(100vh-80px)] relative bg-transparent overflow-hidden" data-testid="contatti-page">
      <SEO
        title="Contatti — Supporto, professionisti, stampa"
        description="Tre indirizzi, tre persone reali che leggono. Supporto pazienti, professionisti, stampa. Rispondiamo entro 24 ore. Per le urgenze, scrivici su WhatsApp."
        path="/contatti"
      />
      <section className="relative max-w-5xl mx-auto px-6 lg:px-10 py-20 lg:py-28">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-10 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Torna alla home
        </Link>

        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} className="relative">
          <div className="hidden md:block absolute right-0 top-0 opacity-90">
            <Mascotte name="coppia" size={170} animation="breathe" />
          </div>
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Contatti</span>
          <h1 className="mt-4 font-serif text-5xl sm:text-6xl lg:text-7xl text-[#0A0A0A] leading-[1.05] tracking-tight max-w-3xl">
            Parlare è sempre il primo passo.<br />
            <em className="not-italic text-[#F58A1F]">Anche con noi.</em>
          </h1>
          <p className="mt-8 text-lg text-[#0A0A0A]/75 leading-relaxed max-w-2xl">
            Tre indirizzi, tre persone reali che leggono. Risposte entro 24 ore.
            Per le urgenze, scrivici su WhatsApp.
          </p>
        </motion.div>
      </section>

      {/* WhatsApp banner */}
      <section className="relative max-w-5xl mx-auto px-6 lg:px-10 pb-12">
        <a
          href={`https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent("Ciao FunzionaBene, vorrei parlare con voi.")}`}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="contatti-whatsapp"
          className="brand-card group !p-7 lg:!p-9 flex flex-col sm:flex-row items-center gap-6 hover:!border-[#25D366]"
        >
          <div className="w-16 h-16 rounded-2xl bg-[#25D366] flex items-center justify-center flex-shrink-0">
            <MessageCircle className="w-7 h-7 text-white" strokeWidth={2.2} />
          </div>
          <div className="flex-1 text-center sm:text-left">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#0A0A0A]/55 mb-1">WhatsApp · Risposta veloce</div>
            <div className="font-serif text-xl lg:text-2xl text-[#0A0A0A]">{PHONE_DISPLAY}</div>
            <div className="text-sm text-[#0A0A0A]/65 mt-1">Lun–Ven 9:00–19:00 · Sab 9:00–13:00</div>
          </div>
          <span className="text-sm text-[#0A0A0A] font-medium tracking-wide group-hover:translate-x-1 transition-transform">
            Scrivici →
          </span>
        </a>
      </section>

      {/* Three cards */}
      <section className="relative max-w-6xl mx-auto px-6 lg:px-10 pb-20">
        <div className="grid md:grid-cols-3 gap-6">
          {CONTATTI.map((c, i) => {
            const Icon = c.icon;
            return (
              <motion.a
                key={c.titolo}
                href={`mailto:${c.email}`}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                data-testid={`contatti-card-${i}`}
                className="brand-card !p-7 group block"
              >
                <div className="flex items-start justify-between mb-5">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center"
                    style={{ backgroundColor: `${c.color}22`, border: `1px solid ${c.color}55` }}
                  >
                    <Icon className="w-5 h-5 text-[#0A0A0A]" />
                  </div>
                  <Mascotte name={c.mascotName} size={70} animation="breathe" />
                </div>
                <h2 className="font-serif text-2xl text-[#0A0A0A] leading-tight">{c.titolo}</h2>
                <p className="mt-3 text-sm text-[#0A0A0A]/65 leading-relaxed">{c.desc}</p>
                <div className="mt-6 inline-flex items-center gap-2 text-sm text-[#0A0A0A] font-medium border-b border-[#0A0A0A]/20 group-hover:border-[#F58A1F] pb-0.5 transition-colors">
                  <Mail className="w-3.5 h-3.5" />
                  {c.email}
                </div>
              </motion.a>
            );
          })}
        </div>
      </section>

      {/* Legal address */}
      <section className="relative max-w-3xl mx-auto px-6 lg:px-10 pb-24 text-center">
        <div className="inline-flex items-center justify-center gap-2 text-[#0A0A0A]/55 text-sm mb-3">
          <MapPin className="w-4 h-4" /> Sede legale
        </div>
        <p className="text-[#0A0A0A]/75 leading-relaxed">
          <strong>{TITOLARE.nome}</strong> — <em>{TITOLARE.brand}</em> è un marchio registrato.<br />
          {TITOLARE.via} · {TITOLARE.citta} · {TITOLARE.paese}<br />
          <span className="text-xs text-[#0A0A0A]/50">P.IVA {TITOLARE.pIva}</span>
        </p>

        <div className="mt-10 pt-8 border-t border-[#0A0A0A]/10 text-[#0A0A0A]/70 text-sm">
          <div className="text-xs uppercase tracking-[0.25em] text-[#0A0A0A]/55 mb-2">Responsabile della protezione dei dati (DPO)</div>
          <p className="leading-relaxed">
            <strong>{DPO.nome}</strong><br />
            {DPO.via} · {DPO.citta} · {DPO.paese}<br />
            <span className="text-xs text-[#0A0A0A]/50">
              C.F. {DPO.codiceFiscale} · P.IVA {DPO.pIva}
            </span><br />
            <a href={`mailto:${DPO.email}`} className="text-[#F58A1F] hover:underline text-sm">{DPO.email}</a>
          </p>
        </div>
      </section>
    </main>
  );
}
