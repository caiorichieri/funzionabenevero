import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ChevronLeft, ChevronRight, Check, AlertCircle, Loader2, X, Copy } from "lucide-react";
import { toast } from "sonner";

const HOURS = Array.from({ length: 13 }, (_, i) => 8 + i); // 8:00 → 20:00
const MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
const WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

const isoDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function buildMonthGrid(year, month) {
  // month is 0-based
  const firstOfMonth = new Date(year, month, 1);
  const dayOfWeek = (firstOfMonth.getDay() + 6) % 7; // Monday-first (0=Mon)
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < dayOfWeek; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export default function TerapistaCalendarioPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [calendario, setCalendario] = useState({}); // { "YYYY-MM-DD": ["09:00", ...] }
  const [selectedDate, setSelectedDate] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pubStatus, setPubStatus] = useState({ pubblicato_at: null, bozza: false });

  const fetchCal = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/terapisti/me/calendario`, { withCredentials: true });
      setCalendario(data.calendario || {});
      setPubStatus({ pubblicato_at: data.calendario_pubblicato_at, bozza: data.calendario_bozza });
      setDirty(false);
    } catch (e) {
      toast.error("Errore nel caricare il calendario");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCal(); }, [fetchCal]);

  const cells = useMemo(() => buildMonthGrid(year, month), [year, month]);

  const gotoMonth = (delta) => {
    let m = month + delta;
    let y = year;
    if (m < 0) { m = 11; y--; }
    else if (m > 11) { m = 0; y++; }
    setMonth(m);
    setYear(y);
    setSelectedDate(null);
  };

  const replicaSettimana = () => {
    if (!selectedDate) return;
    const src = new Date(selectedDate);
    // Compute Monday of the week containing selectedDate
    const dow = (src.getDay() + 6) % 7; // 0=Mon
    const monday = new Date(src.getFullYear(), src.getMonth(), src.getDate() - dow);
    // Read the 7-day source week starting from Monday
    const sourceWeek = {};
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
      sourceWeek[i] = calendario[isoDate(d)] || [];
    }
    const hasAny = Object.values(sourceWeek).some(s => s.length > 0);
    if (!hasAny) {
      toast.warning("Questa settimana è vuota — aggiungi almeno uno slot prima di replicare");
      return;
    }
    // Target: next 7 days (Monday+7). Merge (union) with existing slots on target days.
    setCalendario(prev => {
      const out = { ...prev };
      let addedDays = 0;
      let addedSlots = 0;
      for (let i = 0; i < 7; i++) {
        const target = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 7 + i);
        const key = isoDate(target);
        const src2 = sourceWeek[i];
        if (src2.length > 0) {
          const existing = new Set(out[key] || []);
          const before = existing.size;
          src2.forEach(s => existing.add(s));
          if (existing.size > before) {
            out[key] = Array.from(existing).sort();
            addedDays++;
            addedSlots += (existing.size - before);
          }
        }
      }
      if (addedSlots > 0) {
        toast.success(`Aggiunti ${addedSlots} nuovi slot su ${addedDays} giorni della settimana successiva`);
      } else {
        toast.info("La settimana successiva ha già tutti gli slot — nulla da aggiungere");
      }
      return out;
    });
    setDirty(true);
  };

  const toggleSlot = (dateKey, hour) => {
    const hhmm = `${String(hour).padStart(2, "0")}:00`;
    setCalendario(prev => {
      const list = prev[dateKey] || [];
      const next = list.includes(hhmm) ? list.filter(x => x !== hhmm) : [...list, hhmm].sort();
      const out = { ...prev };
      if (next.length) out[dateKey] = next;
      else delete out[dateKey];
      return out;
    });
    setDirty(true);
  };

  const save = async (pubblica) => {
    setSaving(true);
    try {
      const { data } = await axios.put(
        `${API}/terapisti/me/calendario`,
        { calendario, pubblica },
        { withCredentials: true },
      );
      setPubStatus({ pubblicato_at: data.calendario_pubblicato_at, bozza: data.calendario_bozza });
      setDirty(false);
      toast.success(pubblica ? "Calendario pubblicato — ora sei visibile ai pazienti" : "Bozza salvata");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Errore nel salvare");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <Loader2 className="w-8 h-8 animate-spin text-[#0A0A0A]" />
    </div>
  );

  const totalSlots = Object.values(calendario).reduce((sum, arr) => sum + arr.length, 0);

  return (
    <div className="space-y-6" data-testid="terapista-calendario-page">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Calendario Disponibilità</h1>
          <p className="text-[#0A0A0A]/65 mt-1">Clicca su un giorno per aprire la griglia oraria. Verde = disponibile · Grigio = non disponibile.</p>
        </div>
        <div className="flex items-center gap-2">
          {dirty && (
            <span className="text-xs px-3 py-1.5 rounded-full bg-amber-100 text-amber-800 font-medium">Modifiche non salvate</span>
          )}
          {pubStatus.bozza && !dirty && (
            <span className="text-xs px-3 py-1.5 rounded-full bg-orange-100 text-orange-800 font-medium">In bozza</span>
          )}
          {!pubStatus.bozza && pubStatus.pubblicato_at && !dirty && (
            <span className="text-xs px-3 py-1.5 rounded-full bg-green-100 text-green-800 font-medium flex items-center gap-1">
              <Check className="w-3 h-3" /> Pubblicato
            </span>
          )}
        </div>
      </div>

      {/* Info banner */}
      <div className="bg-[#6B8FA3]/10 border border-[#6B8FA3]/30 rounded-2xl p-4 flex gap-3 items-start">
        <AlertCircle className="w-5 h-5 text-[#6B8FA3] flex-shrink-0 mt-0.5" />
        <div className="text-sm text-[#0A0A0A]/80">
          <strong>Come funziona</strong>: seleziona i giorni e le fasce orarie in cui vuoi ricevere pazienti. Salva come bozza per modificare, poi clicca <strong>Conferma e pubblica</strong> per rendere le disponibilità visibili. Le sessioni durano 50 minuti.
        </div>
      </div>

      {/* Calendar */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <button data-testid="prev-month" onClick={() => gotoMonth(-1)} className="p-2 rounded-lg hover:bg-[#0A0A0A]/5">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h2 className="text-xl font-semibold text-[#0A0A0A] font-[Outfit]">
            {MONTHS_IT[month]} {year}
          </h2>
          <button data-testid="next-month" onClick={() => gotoMonth(1)} className="p-2 rounded-lg hover:bg-[#0A0A0A]/5">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1 mb-2">
          {WEEKDAYS_IT.map(w => (
            <div key={w} className="text-center text-xs font-medium text-[#0A0A0A]/60 py-2">{w}</div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {cells.map((d, i) => {
            if (!d) return <div key={i} className="aspect-square" />;
            const key = isoDate(d);
            const slots = calendario[key] || [];
            const count = slots.length;
            const isToday = key === isoDate(today);
            const isPast = d < new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const isSelected = selectedDate === key;
            const bg = isPast
              ? "bg-[#0A0A0A]/5 text-[#0A0A0A]/40 cursor-not-allowed"
              : count > 0
                ? "bg-green-100 hover:bg-green-200 text-green-900 border-green-300"
                : "bg-red-50/60 hover:bg-red-100 text-[#0A0A0A]/60 border-red-100";
            return (
              <button
                key={key}
                data-testid={`day-${key}`}
                onClick={() => !isPast && setSelectedDate(key)}
                disabled={isPast}
                className={`aspect-square rounded-xl border ${bg} ${isSelected ? "ring-2 ring-[#0A0A0A]" : ""} ${isToday ? "font-bold" : ""} transition-all p-2 flex flex-col items-center justify-center text-sm relative`}
              >
                <span>{d.getDate()}</span>
                {count > 0 && (
                  <span className="absolute bottom-1 right-1 text-[10px] font-semibold bg-green-600 text-white rounded-full px-1.5 min-w-[18px] text-center">{count}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected day time grid */}
      {selectedDate && (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm" data-testid="day-timegrid">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg text-[#0A0A0A] font-[Outfit]">
              {new Date(selectedDate).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </h3>
            <button onClick={() => setSelectedDate(null)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5" data-testid="close-day">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
            {HOURS.map(h => {
              const hhmm = `${String(h).padStart(2, "0")}:00`;
              const on = (calendario[selectedDate] || []).includes(hhmm);
              return (
                <button
                  key={h}
                  data-testid={`slot-${selectedDate}-${hhmm}`}
                  onClick={() => toggleSlot(selectedDate, h)}
                  className={`py-3 px-2 rounded-xl border text-sm font-medium transition-all ${
                    on
                      ? "bg-green-500 text-white border-green-500 hover:bg-green-600"
                      : "bg-red-50 text-[#0A0A0A]/70 border-red-200 hover:bg-red-100"
                  }`}
                >
                  {hhmm}
                </button>
              );
            })}
          </div>
          <p className="text-xs text-[#0A0A0A]/55 mt-4">
            {(calendario[selectedDate] || []).length} slot selezionati · Ogni slot = 1 sessione di 50 minuti
          </p>
          <button
            data-testid="replica-settimana-btn"
            onClick={replicaSettimana}
            className="mt-3 inline-flex items-center gap-2 text-sm text-[#6B8FA3] hover:text-[#0A0A0A] font-medium px-3 py-1.5 rounded-lg hover:bg-[#6B8FA3]/10"
          >
            <Copy className="w-4 h-4" />
            Replica questa settimana su quella successiva
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="sticky bottom-4 bg-white border border-[#0A0A0A]/10 rounded-2xl p-4 shadow-lg flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="text-sm text-[#0A0A0A]/70">
          <strong>{totalSlots}</strong> slot totali disponibili nel calendario
        </div>
        <div className="flex gap-2">
          <button
            data-testid="save-draft-btn"
            disabled={saving || !dirty}
            onClick={() => save(false)}
            className="px-4 py-2.5 rounded-xl border border-[#0A0A0A]/20 text-[#0A0A0A] font-medium text-sm disabled:opacity-40 hover:bg-[#0A0A0A]/5"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Salva bozza"}
          </button>
          <button
            data-testid="publish-btn"
            disabled={saving}
            onClick={() => {
              if (window.confirm("Confermi la pubblicazione? Le tue disponibilità saranno visibili ai pazienti.")) {
                save(true);
              }
            }}
            className="px-4 py-2.5 rounded-xl bg-[#0A0A0A] text-white font-medium text-sm disabled:opacity-40 hover:opacity-90 inline-flex items-center gap-2"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Check className="w-4 h-4" />Conferma e pubblica</>}
          </button>
        </div>
      </div>
    </div>
  );
}
