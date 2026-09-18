import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { X, Calendar, MessageCircle, ArrowRight, Loader2 } from "lucide-react";

const GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"];
const WHATSAPP_NUMBER = "393451124503"; // Italy, no + (wa.me format)
const WHATSAPP_MSG = "Ciao Funzionabene, ho bisogno di piu orari per una terapia!";

function formatSlot(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const opts = { timeZone: "Europe/Rome" };
    const weekday = new Intl.DateTimeFormat("it-IT", { ...opts, weekday: "long" }).format(d);
    const giorno = weekday.charAt(0).toUpperCase() + weekday.slice(1);
    const dateStr = new Intl.DateTimeFormat("it-IT", { ...opts, day: "2-digit", month: "long" }).format(d);
    const timeStr = new Intl.DateTimeFormat("it-IT", { ...opts, hour: "2-digit", minute: "2-digit" }).format(d);
    return { giorno, dateStr, timeStr };
  } catch {
    return { giorno: "", dateStr: iso, timeStr: "" };
  }
}

/**
 * PrenotaSubitoModal — shows the 3 next available slots from the first verified
 * therapist on the platform. The user picks one and either books it (opens BookingSheet)
 * or jumps to WhatsApp asking for more options.
 *
 * Props:
 *  - open: boolean
 *  - onClose: () => void
 *  - onConfirm: ({ terapista, slot }) => void   // called when user picks a slot + clicks Prenota
 */
export default function PrenotaSubitoModal({ open, onClose, onConfirm }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [terapista, setTerapista] = useState(null);
  const [slots, setSlots] = useState([]);
  const [selectedIdx, setSelectedIdx] = useState(0);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      setSelectedIdx(0);
      try {
        // 1) Pick first verified therapist (demo for now, all users when more therapists are onboarded)
        const tList = await axios.get(`${API}/public/terapisti`).then(r => r.data || []);
        if (!tList.length) {
          if (!cancelled) setError("Al momento nessun terapeuta è disponibile online.");
          return;
        }
        const t = tList[0];
        // 2) Pull next 2 weeks of slots, take first 3 future ones
        const res = await axios.get(`${API}/terapisti/${t._id}/slots`, {
          params: { settimane: 2 },
        }).then(r => r.data || { slots: [] });
        const now = new Date();
        const future = (res.slots || [])
          .filter(s => s.disponibile !== false && new Date(s.data_ora) > now)
          .sort((a, b) => new Date(a.data_ora) - new Date(b.data_ora))
          .slice(0, 3);
        if (!cancelled) {
          setTerapista(t);
          setSlots(future);
          if (future.length === 0) {
            setError("Nessun orario disponibile nelle prossime 2 settimane. Scrivici su WhatsApp per più opzioni.");
          }
        }
      } catch (e) {
        if (!cancelled) setError("Errore nel caricamento degli orari. Riprova più tardi.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [open]);

  const handlePrenota = () => {
    if (!terapista || !slots[selectedIdx]) return;
    onConfirm({ terapista, slot: slots[selectedIdx] });
  };

  const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(WHATSAPP_MSG)}`;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed inset-0 z-50 bg-[#0A0A0A]/55 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={onClose}
          data-testid="prenota-subito-modal"
        >
          <motion.div
            initial={{ y: 30, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 30, opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="brand-card w-full max-w-lg p-7 lg:p-9"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="text-xs tracking-[0.25em] uppercase text-[#0A0A0A]/65">Prenota subito</span>
                <h2 className="mt-1.5 font-serif text-2xl lg:text-3xl text-[#0A0A0A] leading-tight">
                  I prossimi orari disponibili
                </h2>
              </div>
              <button
                onClick={onClose}
                aria-label="Chiudi"
                data-testid="prenota-modal-close"
                className="p-2 -mr-2 -mt-1 text-[#0A0A0A]/55 hover:text-[#0A0A0A]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-[#0A0A0A]/65 mb-6 leading-relaxed">
              Scegli l&apos;orario che preferisci, poi continua con la prenotazione e il pagamento.
              Riceverai conferma immediata via email.
            </p>

            {/* Body */}
            {loading && (
              <div className="flex flex-col items-center gap-3 py-10 text-[#0A0A0A]/60">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="text-sm">Carico gli orari…</span>
              </div>
            )}

            {!loading && error && (
              <div className="p-4 rounded-2xl bg-[#0A0A0A]/5 border border-[#0A0A0A]/10 text-sm text-[#0A0A0A]/80 mb-6">
                {error}
              </div>
            )}

            {!loading && !error && slots.length > 0 && (
              <>
                <div className="space-y-2.5 mb-6">
                  {slots.map((s, i) => {
                    const f = formatSlot(s.data_ora);
                    const selected = i === selectedIdx;
                    return (
                      <button
                        key={s.data_ora}
                        type="button"
                        data-testid={`prenota-slot-${i}`}
                        onClick={() => setSelectedIdx(i)}
                        className={`w-full text-left flex items-center justify-between gap-3 px-4 py-3.5 rounded-2xl border transition-all ${
                          selected
                            ? "border-[#F58A1F] bg-[#F58A1F]/8 ring-2 ring-[#F58A1F]/30"
                            : "border-[#0A0A0A]/12 bg-white hover:border-[#0A0A0A]/30"
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <Calendar className={`w-4 h-4 flex-shrink-0 ${selected ? "text-[#F58A1F]" : "text-[#0A0A0A]/55"}`} />
                          <div className="min-w-0">
                            <div className="text-sm font-medium text-[#0A0A0A] truncate">
                              {f.giorno} {f.dateStr}
                            </div>
                            <div className="text-xs text-[#0A0A0A]/60">
                              alle ore {f.timeStr}
                            </div>
                          </div>
                        </div>
                        {selected && (
                          <span className="text-xs font-medium text-[#F58A1F] flex-shrink-0">Selezionato</span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {terapista && (
                  <p className="text-xs text-[#0A0A0A]/55 mb-5 text-center">
                    Con il Dr. {terapista.nome} {terapista.cognome}
                    {terapista.prezzo_sessione ? ` · €${terapista.prezzo_sessione}/sessione` : ""}
                  </p>
                )}
              </>
            )}

            {/* Actions */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={handlePrenota}
                disabled={loading || !!error || slots.length === 0}
                data-testid="prenota-confirm"
                className="inline-flex items-center justify-center gap-2 px-5 py-3.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] disabled:opacity-40 disabled:cursor-not-allowed text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm tracking-wide transition-all"
              >
                Prenota subito
                <ArrowRight className="w-4 h-4" />
              </button>
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="prenota-whatsapp"
                className="inline-flex items-center justify-center gap-2 px-5 py-3.5 border-[1.5px] border-[#0A0A0A] text-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white rounded-2xl text-sm font-medium tracking-wide transition-all"
              >
                <MessageCircle className="w-4 h-4" />
                Più opzioni
              </a>
            </div>

            <p className="text-[11px] text-[#0A0A0A]/45 text-center mt-4 leading-relaxed">
              Hai bisogno di un orario diverso? Scrivici su WhatsApp con &laquo;Più opzioni&raquo;.
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
