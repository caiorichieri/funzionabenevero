import { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ChevronLeft, ChevronRight, Loader2, Users, X } from "lucide-react";
import { toast } from "sonner";

const MONTHS_IT = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"];
const WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

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

export default function AdminCalendarioPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [days, setDays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState(null);

  const fetchMonth = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`${API}/admin/calendario?anno=${year}&mese=${month + 1}`, { withCredentials: true });
      setDays(data.days || []);
    } catch (e) {
      toast.error("Errore nel caricare il calendario");
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => { fetchMonth(); }, [fetchMonth]);

  const dayMap = useMemo(() => {
    const m = new Map();
    days.forEach(d => m.set(d.data, d));
    return m;
  }, [days]);

  const cells = useMemo(() => buildMonthGrid(year, month), [year, month]);

  const gotoMonth = (delta) => {
    let m = month + delta;
    let y = year;
    if (m < 0) { m = 11; y--; }
    else if (m > 11) { m = 0; y++; }
    setMonth(m);
    setYear(y);
    setSelectedDay(null);
  };

  const totalActive = days.reduce((s, d) => s + (d.terapisti_count > 0 ? 1 : 0), 0);
  const totalSlots = days.reduce((s, d) => s + (d.slot_count || 0), 0);

  return (
    <div className="space-y-6" data-testid="admin-calendario-page">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Calendario Terapisti</h1>
        <p className="text-[#0A0A0A]/65 mt-1">Panoramica mensile della copertura: quanti professionisti sono disponibili per ogni giorno.</p>
      </div>

      {/* Legend */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-4 flex flex-wrap items-center gap-4 text-sm">
        <span className="text-[#0A0A0A]/70 font-medium">Legenda:</span>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-red-100 border border-red-300"></div>Nessuno</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-100 border border-green-300"></div>1-2 terapisti</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-400"></div>3-5 terapisti</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-700"></div>6+ terapisti</div>
        <div className="ml-auto text-[#0A0A0A]/70">
          <strong>{totalActive}</strong> giorni coperti · <strong>{totalSlots}</strong> slot totali
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

        {loading ? (
          <div className="py-24 flex justify-center"><Loader2 className="w-8 h-8 animate-spin" /></div>
        ) : (
          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (!d) return <div key={i} className="aspect-square" />;
              const y = d.getFullYear();
              const mm = String(d.getMonth() + 1).padStart(2, "0");
              const dd = String(d.getDate()).padStart(2, "0");
              const key = `${y}-${mm}-${dd}`;
              const info = dayMap.get(key);
              const count = info?.terapisti_count || 0;
              const isPast = d < new Date(today.getFullYear(), today.getMonth(), today.getDate());
              const isToday = key === `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

              let bg = "bg-red-50 border-red-100 text-[#0A0A0A]/60";
              if (count >= 6) bg = "bg-green-700 text-white border-green-800";
              else if (count >= 3) bg = "bg-green-400 text-white border-green-500";
              else if (count > 0) bg = "bg-green-100 text-green-900 border-green-300";
              if (isPast) bg = "bg-[#0A0A0A]/5 text-[#0A0A0A]/40 border-[#0A0A0A]/10";

              return (
                <button
                  key={key}
                  data-testid={`admin-day-${key}`}
                  onClick={() => count > 0 && setSelectedDay(info)}
                  disabled={count === 0}
                  className={`aspect-square rounded-xl border-2 ${bg} ${isToday ? "ring-2 ring-[#0A0A0A]" : ""} transition-all p-2 flex flex-col items-center justify-center text-sm relative disabled:cursor-default`}
                >
                  <span className="font-medium">{d.getDate()}</span>
                  {count > 0 && (
                    <span className="text-[10px] mt-0.5 flex items-center gap-0.5">
                      <Users className="w-2.5 h-2.5" />{count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Day drill-down */}
      {selectedDay && (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm" data-testid="admin-day-detail">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-lg text-[#0A0A0A] font-[Outfit]">
              {new Date(selectedDay.data).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
              <span className="ml-3 text-sm font-normal text-[#0A0A0A]/60">{selectedDay.terapisti_count} terapisti · {selectedDay.slot_count} slot</span>
            </h3>
            <button onClick={() => setSelectedDay(null)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-3">
            {selectedDay.terapisti.map(t => (
              <div key={t.id} className="border border-[#0A0A0A]/10 rounded-xl p-4">
                <div className="font-medium text-[#0A0A0A]">{t.nome}</div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {t.slots.map(s => (
                    <span key={s} className="text-xs px-2 py-1 bg-green-100 text-green-900 rounded-md font-medium">{s}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
