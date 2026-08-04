import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Loader2, Calendar, Check, AlertCircle, ArrowRight } from "lucide-react";
import { toast } from "sonner";

const MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];

const formatDateOra = (iso) => {
  const d = new Date(iso);
  return d.toLocaleString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

export default function RiprogrammaPage() {
  const { appuntamentoId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";

  const [state, setState] = useState({ loading: true, error: null, appuntamento: null, terapista: null });
  const [days, setDays] = useState([]);
  const [monthLoading, setMonthLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [success, setSuccess] = useState(null);
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const validate = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/riprogramma/${appuntamentoId}/validate?token=${encodeURIComponent(token)}`);
      setState({ loading: false, error: null, appuntamento: data.appuntamento, terapista: data.terapista });
    } catch (e) {
      setState({ loading: false, error: e.response?.data?.detail || "Link non valido o scaduto", appuntamento: null, terapista: null });
    }
  }, [appuntamentoId, token]);

  useEffect(() => { validate(); }, [validate]);

  const fetchMonth = useCallback(async () => {
    if (!state.terapista) return;
    setMonthLoading(true);
    try {
      const { data } = await axios.get(`${API}/public/terapisti/${state.terapista.id}/calendario?anno=${year}&mese=${month + 1}`);
      setDays(data.days || []);
    } catch (e) {
      toast.error("Errore caricamento disponibilità");
    } finally {
      setMonthLoading(false);
    }
  }, [state.terapista, year, month]);

  useEffect(() => { fetchMonth(); }, [fetchMonth]);

  const confirm = async () => {
    if (!selectedSlot) return;
    setConfirming(true);
    try {
      const { data } = await axios.post(`${API}/riprogramma/${appuntamentoId}/confirm`, {
        token,
        nuova_data_ora: selectedSlot.data_ora,
      });
      setSuccess(data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore durante la riprogrammazione");
    } finally {
      setConfirming(false);
    }
  };

  const gotoMonth = (delta) => {
    let m = month + delta;
    let y = year;
    if (m < 0) { m = 11; y--; }
    else if (m > 11) { m = 0; y++; }
    setMonth(m);
    setYear(y);
    setSelectedSlot(null);
  };

  if (state.loading) return (
    <div className="min-h-screen bg-[#F4EAA8] flex items-center justify-center">
      <Loader2 className="w-10 h-10 animate-spin text-[#0A0A0A]" />
    </div>
  );

  if (state.error) return (
    <div className="min-h-screen bg-[#F4EAA8] flex items-center justify-center p-6">
      <div className="max-w-md bg-white rounded-3xl p-8 shadow-lg text-center" data-testid="riprogramma-error">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-[#0A0A0A] mb-3 font-[Outfit]">Link non valido</h1>
        <p className="text-[#0A0A0A]/70 mb-4">{state.error}</p>
        <p className="text-sm text-[#0A0A0A]/60">
          Per un rimborso o assistenza, scrivi a <a href="mailto:assistenza@funzionabene.it" className="underline text-[#6B8FA3]">assistenza@funzionabene.it</a>
        </p>
      </div>
    </div>
  );

  if (success) return (
    <div className="min-h-screen bg-[#F4EAA8] flex items-center justify-center p-6">
      <div className="max-w-md bg-white rounded-3xl p-8 shadow-lg text-center" data-testid="riprogramma-success">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-[#0A0A0A] mb-3 font-[Outfit]">Appuntamento riprogrammato ✓</h1>
        <p className="text-[#0A0A0A]/70 mb-2">Nuova data:</p>
        <p className="text-lg font-semibold text-[#0A0A0A] mb-6">{formatDateOra(success.nuova_data_ora)}</p>
        <p className="text-sm text-[#0A0A0A]/60">Riceverai una nuova email di conferma con il link della videocall.</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F4EAA8] py-8 px-4" data-testid="riprogramma-page">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Current appointment */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <h1 className="text-2xl font-bold text-[#0A0A0A] font-[Outfit] mb-1">Riprogramma appuntamento</h1>
          <p className="text-[#0A0A0A]/60 text-sm mb-4">Scegli uno slot alternativo con lo stesso terapista. Nessun rimborso — l&apos;appuntamento viene spostato.</p>
          <div className="bg-[#F4EAA8]/50 rounded-2xl p-4 flex items-start gap-3">
            <Calendar className="w-5 h-5 text-[#0A0A0A]/60 mt-0.5" />
            <div className="text-sm">
              <div className="text-[#0A0A0A]/60 text-xs uppercase tracking-wide mb-1">Appuntamento attuale</div>
              <div className="font-semibold text-[#0A0A0A]">{formatDateOra(state.appuntamento.data_ora)}</div>
              {state.terapista && (
                <div className="text-[#0A0A0A]/70">Con Dr. {state.terapista.nome} {state.terapista.cognome}</div>
              )}
            </div>
          </div>
        </div>

        {/* Month selector */}
        <div className="bg-white rounded-3xl p-6 shadow-lg">
          <div className="flex items-center justify-between mb-4">
            <button onClick={() => gotoMonth(-1)} className="px-3 py-1.5 rounded-lg hover:bg-[#0A0A0A]/5 text-sm">← Precedente</button>
            <h2 className="text-lg font-semibold text-[#0A0A0A] font-[Outfit]">{MONTHS_IT[month]} {year}</h2>
            <button onClick={() => gotoMonth(1)} className="px-3 py-1.5 rounded-lg hover:bg-[#0A0A0A]/5 text-sm">Successivo →</button>
          </div>

          {monthLoading ? (
            <div className="py-16 flex justify-center"><Loader2 className="w-8 h-8 animate-spin" /></div>
          ) : days.length === 0 ? (
            <div className="py-16 text-center text-[#0A0A0A]/60">
              Nessuna disponibilità in questo mese. Prova un mese successivo.
            </div>
          ) : (
            <div className="space-y-4">
              {days.map(day => (
                <div key={day.data} className="border border-[#0A0A0A]/10 rounded-2xl p-4">
                  <div className="font-medium text-[#0A0A0A] mb-3">
                    {new Date(day.data).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" })}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {day.slots.map(slot => {
                      const isSelected = selectedSlot?.data_ora === slot.data_ora;
                      return (
                        <button
                          key={slot.data_ora}
                          disabled={!slot.disponibile}
                          onClick={() => setSelectedSlot(slot)}
                          data-testid={`slot-${slot.data_ora}`}
                          className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                            !slot.disponibile
                              ? "bg-[#0A0A0A]/5 text-[#0A0A0A]/30 cursor-not-allowed line-through"
                              : isSelected
                                ? "bg-[#0A0A0A] text-white ring-2 ring-[#D4A017]"
                                : "bg-green-100 text-green-900 hover:bg-green-200"
                          }`}
                        >
                          {slot.ora}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Confirm bar */}
        {selectedSlot && (
          <div className="bg-white rounded-3xl p-6 shadow-lg sticky bottom-4" data-testid="confirm-bar">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-xs text-[#0A0A0A]/60 uppercase tracking-wide mb-1">Nuovo appuntamento</div>
                <div className="font-semibold text-[#0A0A0A]">{formatDateOra(selectedSlot.data_ora)}</div>
              </div>
              <button
                onClick={confirm}
                disabled={confirming}
                data-testid="confirm-reschedule-btn"
                className="px-6 py-3 rounded-xl bg-[#0A0A0A] text-white font-medium text-sm inline-flex items-center gap-2 hover:opacity-90 disabled:opacity-50"
              >
                {confirming ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Conferma <ArrowRight className="w-4 h-4" /></>}
              </button>
            </div>
          </div>
        )}

        <p className="text-center text-xs text-[#0A0A0A]/50">
          Per un rimborso invece della riprogrammazione, scrivi a <a href="mailto:assistenza@funzionabene.it" className="underline">assistenza@funzionabene.it</a>
        </p>
      </div>
    </div>
  );
}
