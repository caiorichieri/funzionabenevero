import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { AREE_INTERVENTO, AREE_CATEGORIE } from "@/data/areeIntervento";
import Mascotte from "@/components/shared/Mascotte";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import SEO from "@/components/shared/SEO";

export default function AreeInterventoPage() {
  // Group by category
  const grouped = AREE_INTERVENTO.reduce((acc, a) => {
    if (!acc[a.categoria]) acc[a.categoria] = [];
    acc[a.categoria].push(a);
    return acc;
  }, {});

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent relative overflow-hidden" data-testid="aree-intervento-page">
      <SEO
        title="Aree di intervento — Sessuologia clinica"
        description="Disfunzioni sessuali, ansia da prestazione, coppia, identità e orientamento, trauma: le aree cliniche in cui i nostri psicologi e sessuologi lavorano ogni giorno."
        path="/aree-intervento"
      />
      {/* Continuous atmospheric backdrop */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true"><div className="absolute -top-32 -left-32 w-[700px] h-[700px] rounded-full bg-[#0A0A0A]/6 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-[800px] h-[800px] rounded-full bg-[#6B8FA3]/22 blur-3xl" />
      </div>

      <div className="relative max-w-6xl mx-auto px-6 lg:px-10 py-16 lg:py-24">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-10 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Torna alla home
        </Link>

        <div className="max-w-3xl mb-16 relative">
          <div className="hidden md:block absolute -right-4 -top-8 opacity-90">
            <Mascotte name="pensativo" theme="light" size={140} animation="breathe" />
          </div>
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Aree di intervento</span>
          <h1 className="mt-4 font-serif text-5xl lg:text-6xl text-[#0A0A0A] leading-[1.05]">
            Tutto quello di cui ci occupiamo.
          </h1>
          <p className="mt-6 text-[#0A0A0A]/65 text-lg leading-relaxed">
            {AREE_INTERVENTO.length} aree cliniche, tutte nell'ambito della sessuologia.
            Se non sei sicuro in quale rientri, <Link to="/questionario" className="text-[#0A0A0A] hover:text-[#0A0A0A]/70 underline">il questionario ti aiuta a capirlo in 2 minuti</Link>.
          </p>
        </div>

        {Object.entries(grouped).map(([cat, items], idx) => {
          const catInfo = AREE_CATEGORIE[cat] || {};
          return (
            <section key={cat} className="mb-16" data-testid={`cat-${cat.toLowerCase()}`}>
              <div className="flex items-center gap-4 mb-6">
                <span className="inline-block w-12 h-[2px] rounded-full" style={{ background: catInfo.color }} />
                <h2 className="text-xs tracking-[0.25em] uppercase" style={{ color: catInfo.color }}>
                  {catInfo.label || cat}
                </h2>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((a, i) => (
                  <motion.div
                    key={a.slug}
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.35, delay: (i % 3) * 0.07 }}
                    data-testid={`area-detail-${a.slug}`}
                    className="brand-card p-6"
                  >
                    <h3 className="font-serif text-xl text-[#0A0A0A] mb-3 leading-tight">{a.titolo}</h3>
                    <p className="text-sm text-[#0A0A0A]/65 leading-relaxed">{a.descrizione}</p>
                  </motion.div>
                ))}
              </div>
            </section>
          );
        })}

        <PrenotaSubitoCTA
          variant="banner"
          testid="aree-prenota"
          bannerTitle="Hai già un'idea chiara?"
          bannerCopy="Scegli direttamente un orario disponibile e prenota la prima sessione. Veloce, riservato, in italiano."
          mascotName="saltitante"
        />

        <div className="mt-12 text-center p-10 bg-gradient-to-br from-[#0A0A0A]/10 via-[#0A0A0A]/8 to-transparent border border-[#0A0A0A]/20 rounded-3xl">
          <h2 className="font-serif text-3xl lg:text-4xl text-[#0A0A0A] mb-4">Non sai da dove iniziare?</h2>
          <p className="text-[#0A0A0A]/65 max-w-xl mx-auto mb-8">
            Il nostro questionario in 2 minuti individua le aree più rilevanti per te e ti propone i 3 specialisti più affini.
          </p>
          <Link
            to="/questionario"
            data-testid="aree-cta-btn"
            className="inline-flex items-center gap-3 px-8 py-4 border-[1.5px] border-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white text-[#0A0A0A] rounded-2xl tracking-wide transition-all"
          >
            Inizia il Questionario <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </main>
  );
}
