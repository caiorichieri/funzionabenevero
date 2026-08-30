import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Mascotte from "@/components/shared/Mascotte";
import PrenotaSubitoCTA from "@/components/public/PrenotaSubitoCTA";
import SEO from "@/components/shared/SEO";

const FALLBACK_FAQ = [
  {
    domanda: "Come funziona l'abbinamento con il terapeuta?",
    risposta: "Compilando un breve questionario di 5 domande, il nostro algoritmo confronta le tue esigenze (area di interesse, disponibilità, preferenze) con il profilo dei nostri specialisti e ti propone i 3 professionisti più affini.",
  },
  {
    domanda: "Le sessioni sono online o in presenza?",
    risposta: "La maggior parte delle sessioni avviene online tramite videochiamata sicura (Daily.co), ma alcuni terapeuti offrono anche sessioni in studio. Potrai scegliere in fase di prenotazione.",
  },
  {
    domanda: "Quanto costa una sessione?",
    risposta: "Le tariffe variano dai 49€ ai 90€ per sessione da 50 minuti, a seconda dello specialista. Il prezzo è sempre indicato chiaramente sul profilo del terapeuta prima di confermare la prenotazione.",
  },
  {
    domanda: "I miei dati sono protetti?",
    risposta: "Assolutamente sì. Tutti i dati sono cifrati e conservati in conformità al GDPR. Le conversazioni con il tuo terapeuta sono coperte dal segreto professionale.",
  },
  {
    domanda: "Posso cambiare terapeuta se non mi trovo bene?",
    risposta: "Certo. Senza alcuna domanda. Puoi sempre rifare il questionario e richiedere un nuovo abbinamento.",
  },
  {
    domanda: "I terapeuti sono davvero qualificati?",
    risposta: "Tutti i nostri specialisti sono psicologi iscritti all'Albo italiano con polizza assicurativa professionale attiva. Verifichiamo periodicamente le loro credenziali.",
  },
  {
    domanda: "Posso annullare una sessione?",
    risposta: "Sì, puoi annullare o riprogrammare fino a 24 ore prima della sessione senza alcun costo.",
  },
];

export default function FAQPage() {
  const [faqs, setFaqs] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    axios.get(`${API}/public/faq`).then(r => {
      setFaqs(r.data.length > 0 ? r.data : FALLBACK_FAQ);
    }).catch(() => setFaqs(FALLBACK_FAQ));
  }, []);

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent relative overflow-hidden" data-testid="faq-page">
      <SEO
        title="FAQ — Domande frequenti"
        description="Come funziona l'abbinamento, quanto costa una sessione, i tuoi dati sono protetti? Risposte chiare a tutte le domande sulla consulenza sessuologica online."
        path="/faq"
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": (faqs || []).slice(0, 20).map((f) => ({
            "@type": "Question",
            "name": f.domanda,
            "acceptedAnswer": { "@type": "Answer", "text": f.risposta },
          })),
        }}
      />
      {/* Continuous atmospheric backdrop */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true"><div className="absolute -top-32 -left-32 w-[700px] h-[700px] rounded-full bg-[#0A0A0A]/6 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-[800px] h-[800px] rounded-full bg-[#6B8FA3]/22 blur-3xl" />
      </div>

      <div className="relative max-w-3xl mx-auto px-6 lg:px-10 py-16 lg:py-24">
        <div className="text-center mb-16">
          <div className="flex justify-center mb-2">
            <Mascotte name="curioso" theme="light" size={120} animation="wiggle" />
          </div>
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Domande frequenti</span>
          <h1 className="mt-4 font-serif text-5xl lg:text-6xl text-[#0A0A0A] leading-tight">
            Cosa c&apos;è da sapere.
          </h1>
          <p className="mt-6 text-[#0A0A0A]/65">
            Risposte chiare alle domande più comuni. Se non trovi quella che cerchi, scrivici.
          </p>
        </div>

        <div className="divide-y divide-white/10 border-t border-b border-[#0A0A0A]/10">
          {faqs.map((f, i) => {
            const isOpen = open === i;
            return (
              <div key={i} data-testid={`faq-item-${i}`}>
                <button
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="w-full py-6 flex items-start justify-between gap-6 text-left group"
                >
                  <span className="font-serif text-xl text-[#0A0A0A] group-hover:text-[#0A0A0A] transition-colors">
                    {f.domanda}
                  </span>
                  <ChevronDown
                    className={`w-5 h-5 text-[#6B8FA3] flex-shrink-0 mt-1 transition-transform ${isOpen ? "rotate-180 text-[#0A0A0A]" : ""}`}
                  />
                </button>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <p className="pb-6 text-[#0A0A0A]/75 leading-relaxed">{f.risposta}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>

        <PrenotaSubitoCTA
          variant="banner"
          testid="faq-prenota"
          bannerTitle="Hai altre domande?"
          bannerCopy="Il modo più veloce per averne risposta è parlare con uno dei nostri specialisti. Scegli un orario e inizia."
          mascotName="curioso"
        />
      </div>
    </main>
  );
}
