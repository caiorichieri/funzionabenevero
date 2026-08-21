import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

// One mascot per step — gentle visual narrative
const STEP_MASCOTS = ["embrulhado", "ovo", "pensativo", "curioso", "saltitante"];

const STEPS = [
  {
    key: "eta",
    label: "Qual è la tua fascia d'età?",
    helper: "Ci aiuta a consigliarti il terapeuta più adatto.",
    type: "single",
    options: ["18-25", "26-35", "36-45", "46-55", "56+"],
  },
  {
    key: "genere",
    label: "Come ti identifichi?",
    helper: "Rispondi come preferisci. Nessuna opzione è giusta o sbagliata.",
    type: "single",
    options: ["Donna", "Uomo", "Non binario", "Preferisco non rispondere"],
  },
  {
    key: "problemi",
    label: "Quali aree vorresti esplorare?",
    helper: "Puoi selezionare più di una. Sarai sempre libero di cambiarle.",
    type: "multi",
    options: [
      "Ansia e stress",
      "Relazioni di coppia",
      "Sessuologia e intimità",
      "Autostima e crescita personale",
      "Disturbi dell'umore",
      "Traumi e eventi difficili",
      "Dipendenze affettive",
      "Identità e orientamento",
    ],
  },
  {
    key: "orari",
    label: "Quando preferisci le sessioni?",
    helper: "Seleziona tutte le fasce compatibili con i tuoi impegni.",
    type: "multi",
    options: ["Mattina (8-12)", "Pomeriggio (12-18)", "Sera (18-21)", "Weekend"],
  },
  {
    key: "preferenza_terapeuta",
    label: "Preferenza di genere per il terapeuta?",
    helper: "Alcune persone si sentono più a loro agio con un genere specifico.",
    type: "single",
    options: ["Preferisco una donna", "Preferisco un uomo", "Non ho preferenze"],
  },
];

export default function QuestionnairePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const topRef = useRef(null);

  const current = STEPS[step];
  const progress = ((step + 1) / STEPS.length) * 100;

  // Scroll to top of the question when step changes (avoids landing on the
  // options list on mobile after picking a previous answer).
  useEffect(() => {
    if (topRef.current) {
      topRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [step]);

  const selectSingle = (opt) => {
    const next = { ...answers, [current.key]: opt };
    setAnswers(next);
    // Auto-advance only on intermediate single-select steps; last step requires explicit confirmation
    if (step < STEPS.length - 1) {
      setTimeout(() => goNext(next), 250);
    }
  };

  const toggleMulti = (opt) => {
    const prev = answers[current.key] || [];
    const next = prev.includes(opt) ? prev.filter((x) => x !== opt) : [...prev, opt];
    setAnswers({ ...answers, [current.key]: next });
  };

  const canProceed = () => {
    const v = answers[current.key];
    if (current.type === "single") return !!v;
    return Array.isArray(v) && v.length > 0;
  };

  const goNext = async (data = answers) => {
    if (step < STEPS.length - 1) {
      setStep(step + 1);
    } else {
      setLoading(true);
      try {
        const payload = {
          eta: data.eta,
          genere: data.genere,
          problemi: data.problemi || [],
          orari: data.orari || [],
          preferenza_terapeuta: data.preferenza_terapeuta,
        };
        const res = await axios.post(`${API}/public/matching`, payload);
        sessionStorage.setItem("fb_match_results", JSON.stringify(res.data));
        sessionStorage.setItem("fb_questionnaire", JSON.stringify(payload));
        navigate("/risultati");
      } catch (e) {
        setLoading(false);
      }
    }
  };

  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent" data-testid="questionnaire">
      <div className="sticky top-20 z-30 h-1 bg-white/5">
        <motion.div
          data-testid="progress-bar"
          className="h-full bg-[#0A0A0A]"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      <div ref={topRef} className="max-w-5xl mx-auto px-6 py-12 lg:py-20 scroll-mt-24">
        <div className="mb-8 flex items-center justify-between text-xs tracking-[0.2em] uppercase text-[#0A0A0A]/50">
          <span>Passo {step + 1} di {STEPS.length}</span>
          {step > 0 && (
            <button
              data-testid="questionnaire-back"
              onClick={() => setStep(step - 1)}
              className="flex items-center gap-1 hover:text-[#0A0A0A] transition-colors"
            >
              <ArrowLeft className="w-3 h-3" /> Indietro
            </button>
          )}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={current.key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            data-testid={`step-${current.key}`}
            className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-8 lg:gap-14 items-start"
          >
            {/* Mascotte column — hidden on mobile (shown at bottom below), sticky on desktop */}
            <div className="hidden lg:flex lg:sticky lg:top-32 items-center justify-center">
              <Mascotte
                name={STEP_MASCOTS[step % STEP_MASCOTS.length]}
                theme="light"
                size={200}
                animation={step === STEPS.length - 1 ? "wiggle" : "float"}
              />
            </div>

            {/* Question + options column */}
            <div>
              <h1 className="font-serif text-3xl lg:text-4xl text-[#0A0A0A] leading-tight text-left">
                {current.label}
              </h1>
              <p className="mt-3 text-[#0A0A0A]/65 text-left">{current.helper}</p>

              <div className="mt-8 space-y-3">
                {current.options.map((opt) => {
                  const isSelected =
                    current.type === "single"
                      ? answers[current.key] === opt
                      : (answers[current.key] || []).includes(opt);
                  return (
                    <button
                      key={opt}
                      data-testid={`opt-${current.key}-${opt.replace(/[^a-zA-Z0-9]/g, "-").toLowerCase()}`}
                      onClick={() => current.type === "single" ? selectSingle(opt) : toggleMulti(opt)}
                      className={`w-full flex items-center justify-between px-6 py-4 rounded-2xl border transition-all text-left ${
                        isSelected
                          ? "border-[#0A0A0A] bg-white/30 text-[#0A0A0A]"
                          : "border-[#0A0A0A]/10 bg-white/30 text-[#0A0A0A]/75 hover:border-[#6B8FA3]/60 hover:bg-white/60"
                      }`}
                    >
                      <span className="text-base">{opt}</span>
                      {isSelected && (
                        <div className="w-6 h-6 rounded-full bg-[#0A0A0A] flex items-center justify-center">
                          <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {(current.type === "multi" || step === STEPS.length - 1) && (
                <button
                  data-testid="questionnaire-next"
                  onClick={() => goNext()}
                  disabled={!canProceed() || loading}
                  className="mt-10 w-full inline-flex items-center justify-center gap-3 px-8 py-4 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg tracking-wide transition-all"
                >
                  {loading ? "Analisi in corso..." : step === STEPS.length - 1 ? "Trova i miei match" : "Continua"}
                  {!loading && <ArrowRight className="w-4 h-4" />}
                </button>
              )}

              {/* Mascotte — mobile only, shown at bottom */}
              <div className="mt-10 flex justify-center lg:hidden">
                <Mascotte
                  name={STEP_MASCOTS[step % STEP_MASCOTS.length]}
                  theme="light"
                  size={100}
                  animation={step === STEPS.length - 1 ? "wiggle" : "float"}
                />
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </main>
  );
}
