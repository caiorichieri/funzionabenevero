import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ChevronLeft, ChevronRight, Check, Info, Loader2, X, Copy } from "lucide-react";
import { toast } from "sonner";

const HOURS = Array.from({ length: 13 }, (_, i) => 8 + i); // 8:00 → 20:00
const MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
const WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

const isoDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function buildMonthGrid(year, month) {
  const firstOfMonth = new Date(year, month, 1);
  const dayOfWeek = (firstOfMonth.getDay() + 6) % 7;
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
  const [calendario, setCalendario] = useState({});
  const [appuntamenti, setAppuntamenti] = useState({}); // { "YYYY-MM-DD": [{ora, paziente_nome, stato}] }
  const [selectedDate, setSelectedDate] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pubStatus, setPubStatus] = useState({ pubblicato_at: null, bozza: false });

  const fetchCal = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API}/terapisti/me/calendario`, { withCredentials: true });
      setCalendario(data.calendario || {});
      setAppuntamenti(data.appuntamenti || {});
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
    setMonth(m); setYear(y); setSelectedDate(null);
  };

  const replicaSettimana = () => {
    if (!selectedDate) return;
    const src = new Date(selectedDate);
    const dow = (src.getDay() + 6) % 7;
    const monday = new Date(src.getFullYear(), src.getMonth(), src.getDate() - dow);
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
    setCalendario(prev => {
      const out = { ...prev };
      let addedDays = 0, addedSlots = 0;
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
      setCalendario(data.calendario || {});
      setPubStatus({ pubblicato_at: data.calendario_pubblicato_at, bozza: data.calendario_bozza });
      setDirty(false);
      if (data.dropped_past_slots > 0) {
        toast.warning(`${data.dropped_past_slots} slot troppo vicini (min 2 ore) sono stati rimossi.`);
      }
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

  const totalSlots = Object.values(calendario).reduce((s, a) => s + a.length, 0);

  return (
    <div className="space-y-3 flex flex-col h-full min-h-0" data-testid="terapista-calendario-page">
      {/* Compact header: title + status + month nav in one row */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-[#0A0A0A] font-[Outfit]">Calendario Disponibilità</h1>
          {dirty ? (
            <span className="text-xs px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 font-medium">Non salvato</span>
          ) : pubStatus.bozza ? (
            <span className="text-xs px-2.5 py-1 rounded-full bg-orange-100 text-orange-800 font-medium">Bozza</span>
          ) : pubStatus.pubblicato_at ? (
            <span className="text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-800 font-medium inline-flex items-center gap-1">
              <Check className="w-3 h-3" /> Pubblicato
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="prev-month" onClick={() => gotoMonth(-1)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm font-semibold text-[#0A0A0A] min-w-[130px] text-center">
            {MONTHS_IT[month]} {year}
          </span>
          <button data-testid="next-month" onClick={() => gotoMonth(1)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#0A0A0A]/60 hidden sm:inline">{totalSlots} slot totali</span>
          <button
            data-testid="save-draft-btn"
            disabled={saving || !dirty}
            onClick={() => save(false)}
            className="px-3 py-1.5 rounded-lg border border-[#0A0A0A]/20 text-[#0A0A0A] text-xs font-medium disabled:opacity-40 hover:bg-[#0A0A0A]/5"
          >
            Salva bozza
          </button>
          <button
            data-testid="publish-btn"
            disabled={saving}
            onClick={() => {
              if (window.confirm("Confermi la pubblicazione? Le tue disponibilità saranno visibili ai pazienti.")) save(true);
            }}
            className="px-3 py-1.5 rounded-lg bg-[#0A0A0A] text-white text-xs font-medium disabled:opacity-40 hover:opacity-90 inline-flex items-center gap-1"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <><Check className="w-3.5 h-3.5" />Pubblica</>}
          </button>
        </div>
      </div>

      {/* Info banner — compact single line */}
      <div className="bg-[#6B8FA3]/8 border border-[#6B8FA3]/25 rounded-xl px-3 py-2 flex items-center gap-2 text-xs text-[#0A0A0A]/75">
        <Info className="w-3.5 h-3.5 text-[#6B8FA3] flex-shrink-0" />
        <span>Clicca un giorno per gestire gli orari · <strong className="text-green-700">Verde</strong> = disponibile · <strong className="text-[#D4A017]">Oro</strong> = paziente prenotato · Sessione = 50 min</span>
      </div>

      {/* Calendar grid — height fills remaining viewport */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-3 shadow-sm flex-1 flex flex-col min-h-0">
        <div className="grid grid-cols-7 gap-1 mb-1 flex-shrink-0">
          {WEEKDAYS_IT.map(w => (
            <div key={w} className="text-center text-[10px] uppercase tracking-wide font-semibold text-[#0A0A0A]/55 py-1">{w}</div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1 flex-1 min-h-0">
          {cells.map((d, i) => {
            if (!d) return <div key={i} className="bg-[#0A0A0A]/[0.02] rounded-lg" />;
            const key = isoDate(d);
            const slots = calendario[key] || [];
            const appts = appuntamenti[key] || [];
            const bookedTimes = new Set(appts.map(a => a.ora));
            const freeSlots = slots.filter(s => !bookedTimes.has(s));
            const isToday = key === isoDate(today);
            const isPast = d < new Date(today.getFullYear(), today.getMonth(), today.getDate());
            const isSelected = selectedDate === key;
            const hasContent = slots.length > 0 || appts.length > 0;

            const cellBg = isPast
              ? "bg-[#0A0A0A]/[0.03] text-[#0A0A0A]/40 cursor-not-allowed border-[#0A0A0A]/5"
              : hasContent
                ? "bg-white hover:bg-green-50/40 border-green-200 cursor-pointer"
                : "bg-red-50/30 hover:bg-red-100/50 border-red-100 cursor-pointer";

            return (
              <button
                key={key}
                data-testid={`day-${key}`}
                onClick={() => !isPast && setSelectedDate(key)}
                disabled={isPast}
                className={`text-left rounded-lg border ${cellBg} ${isSelected ? "ring-2 ring-[#0A0A0A]" : ""} transition-all p-1.5 flex flex-col overflow-hidden`}
                style={{ minHeight: "70px" }}
              >
                <div className="flex items-center justify-between mb-1 flex-shrink-0">
                  <span className={`text-xs ${isToday ? "font-bold text-[#D4A017]" : "font-medium text-[#0A0A0A]/80"}`}>
                    {d.getDate()}
                  </span>
                  {slots.length > 0 && (
                    <span className="text-[9px] font-semibold text-green-700 bg-green-100 rounded-full px-1.5 leading-tight">
                      {slots.length}
                    </span>
                  )}
                </div>
                <div className="flex-1 flex flex-col gap-0.5 overflow-hidden">
                  {/* Booked appointments (gold, with patient name) */}
                  {appts.slice(0, 3).map((a) => (
                    <div key={a.id} className="text-[9px] leading-tight bg-[#D4A017]/15 text-[#0A0A0A] border border-[#D4A017]/40 rounded px-1 py-0.5 truncate flex items-center gap-1">
                      <span className="font-semibold">{a.ora}</span>
                      <span className="truncate">{a.paziente_nome}</span>
                    </div>
                  ))}
                  {/* Free slots (green) */}
                  {freeSlots.slice(0, Math.max(0, 4 - Math.min(3, appts.length))).map(s => (
                    <div key={s} className="text-[9px] leading-tight bg-green-100 text-green-800 rounded px-1 py-0.5">
                      {s}
                    </div>
                  ))}
                  {(appts.length + freeSlots.length) > 4 && (
                    <div className="text-[9px] text-[#0A0A0A]/50 leading-tight">
                      +{(appts.length + freeSlots.length) - 4} altri
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Day editor modal-ish inline (overlay slide-up) */}
      {selectedDate && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-end sm:items-center justify-center p-4" onClick={() => setSelectedDate(null)}>
          <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto p-6 shadow-2xl" onClick={e => e.stopPropagation()} data-testid="day-timegrid">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-lg text-[#0A0A0A] font-[Outfit] capitalize">
                {new Date(selectedDate).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
              </h3>
              <button onClick={() => setSelectedDate(null)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5" data-testid="close-day">
                <X className="w-4 h-4" />
              </button>
            </div>

            {(appuntamenti[selectedDate] || []).length > 0 && (
              <div className="mb-4 p-3 bg-[#D4A017]/10 border border-[#D4A017]/30 rounded-xl">
                <div className="text-xs font-semibold text-[#0A0A0A]/70 mb-2 uppercase tracking-wide">Pazienti prenotati</div>
                <div className="space-y-1">
                  {(appuntamenti[selectedDate] || []).map(a => (
                    <div key={a.id} className="text-sm text-[#0A0A0A] flex items-center gap-2">
                      <span className="font-bold">{a.ora}</span>
                      <span>{a.paziente_nome}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="text-xs font-semibold text-[#0A0A0A]/70 mb-2 uppercase tracking-wide">Orari disponibili</div>
            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-7 gap-2">
              {HOURS.map(h => {
                const hhmm = `${String(h).padStart(2, "0")}:00`;
                const on = (calendario[selectedDate] || []).includes(hhmm);
                const booked = (appuntamenti[selectedDate] || []).some(a => a.ora === hhmm);
                // Compute the actual datetime of this slot to compare against now+2h
                const [yy, mm, dd] = selectedDate.split("-").map(Number);
                const slotDt = new Date(yy, mm - 1, dd, h, 0, 0);
                const minSlot = new Date(Date.now() + 2 * 60 * 60 * 1000);
                const tooSoon = slotDt < minSlot;
                const disabled = booked || tooSoon;
                let cls = "bg-red-50 text-[#0A0A0A]/70 border-red-200 hover:bg-red-100";
                let title = "";
                if (booked) {
                  cls = "bg-[#D4A017]/20 text-[#D4A017] border-[#D4A017]/40 cursor-not-allowed";
                  title = "Slot già prenotato";
                } else if (tooSoon) {
                  cls = "bg-[#0A0A0A]/5 text-[#0A0A0A]/30 border-[#0A0A0A]/10 cursor-not-allowed line-through";
                  title = "Troppo vicino (min 2 ore da adesso)";
                } else if (on) {
                  cls = "bg-green-500 text-white border-green-500 hover:bg-green-600";
                }
                return (
                  <button
                    key={h}
                    data-testid={`slot-${selectedDate}-${hhmm}`}
                    onClick={() => !disabled && toggleSlot(selectedDate, h)}
                    disabled={disabled}
                    className={`py-2.5 px-2 rounded-lg border text-sm font-medium transition-all ${cls}`}
                    title={title}
                  >
                    {hhmm}
                  </button>
                );
              })}
            </div>
            <div className="mt-4 flex items-center justify-between gap-3">
              <p className="text-xs text-[#0A0A0A]/55">
                {(calendario[selectedDate] || []).length} slot · Ogni sessione dura 50 min
              </p>
              <button
                data-testid="replica-settimana-btn"
                onClick={replicaSettimana}
                className="inline-flex items-center gap-1.5 text-xs text-[#6B8FA3] hover:text-[#0A0A0A] font-medium px-3 py-1.5 rounded-lg hover:bg-[#6B8FA3]/10"
              >
                <Copy className="w-3.5 h-3.5" />
                Replica su settimana successiva
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
