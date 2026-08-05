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

  const totalActive = days.reduce((s, d) => s + ((d.terapisti_count > 0 || d.appuntamenti_count > 0) ? 1 : 0), 0);
  const totalSlots = days.reduce((s, d) => s + (d.slot_count || 0), 0);
  const totalBookings = days.reduce((s, d) => s + (d.appuntamenti_count || 0), 0);

  return (
    <div className="space-y-6" data-testid="admin-calendario-page">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Calendario Terapisti</h1>
        <p className="text-[#0A0A0A]/65 mt-1">Panoramica mensile della copertura: quanti professionisti sono disponibili per ogni giorno.</p>
      </div>

      {/* Legend */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-4 flex flex-wrap items-center gap-4 text-sm">
        <span className="text-[#0A0A0A]/70 font-medium">Legenda:</span>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-red-100 border border-red-300"></div>Nessun dato</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-[#D4A017]/25 border border-[#D4A017]/50"></div>Solo prenotazioni</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-100 border border-green-300"></div>1-2 terapisti</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-400"></div>3-5 terapisti</div>
        <div className="flex items-center gap-2"><div className="w-4 h-4 rounded bg-green-700"></div>6+ terapisti</div>
        <div className="ml-auto text-[#0A0A0A]/70">
          <strong>{totalActive}</strong> giorni attivi · <strong>{totalSlots}</strong> slot · <strong className="text-[#D4A017]">{totalBookings}</strong> prenotazioni
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
              const bookings = info?.appuntamenti_count || 0;
              const isPast = d < new Date(today.getFullYear(), today.getMonth(), today.getDate());
              const isToday = key === `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

              let bg = "bg-red-50 border-red-100 text-[#0A0A0A]/60";
              if (count >= 6) bg = "bg-green-700 text-white border-green-800";
              else if (count >= 3) bg = "bg-green-400 text-white border-green-500";
              else if (count > 0) bg = "bg-green-100 text-green-900 border-green-300";
              else if (bookings > 0) bg = "bg-[#D4A017]/25 text-[#0A0A0A] border-[#D4A017]/50";
              if (isPast) bg = "bg-[#0A0A0A]/5 text-[#0A0A0A]/40 border-[#0A0A0A]/10";

              const hasContent = count > 0 || bookings > 0;
              return (
                <button
                  key={key}
                  data-testid={`admin-day-${key}`}
                  onClick={() => hasContent && setSelectedDay(info)}
                  disabled={!hasContent}
                  className={`aspect-square rounded-xl border-2 ${bg} ${isToday ? "ring-2 ring-[#0A0A0A]" : ""} transition-all p-2 flex flex-col items-center justify-center text-sm relative disabled:cursor-default`}
                >
                  <span className="font-medium">{d.getDate()}</span>
                  {count > 0 && (
                    <span className="text-[10px] mt-0.5 flex items-center gap-0.5">
                      <Users className="w-2.5 h-2.5" />{count}
                    </span>
                  )}
                  {bookings > 0 && (
                    <span className="text-[10px] mt-0.5 font-semibold text-[#D4A017] bg-white/80 rounded-full px-1.5">
                      {bookings} pren.
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
            <h3 className="font-semibold text-lg text-[#0A0A0A] font-[Outfit] capitalize">
              {new Date(selectedDay.data).toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
              <span className="ml-3 text-sm font-normal text-[#0A0A0A]/60">
                {selectedDay.terapisti_count} disponibili · {selectedDay.slot_count} slot · <span className="text-[#D4A017]">{selectedDay.appuntamenti_count} prenotazioni</span>
              </span>
            </h3>
            <button onClick={() => setSelectedDay(null)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Booked appointments (gold) */}
          {selectedDay.appuntamenti && selectedDay.appuntamenti.length > 0 && (
            <div className="mb-5">
              <div className="text-xs uppercase tracking-wide font-semibold text-[#D4A017] mb-2">Prenotazioni</div>
              <div className="space-y-2">
                {selectedDay.appuntamenti.map(a => (
                  <div key={a.id} className="bg-[#D4A017]/10 border border-[#D4A017]/30 rounded-xl p-3 flex items-center justify-between" data-testid={`appt-${a.id}`}>
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-[#0A0A0A] w-14">{a.ora}</span>
                      <div>
                        <div className="text-sm font-medium text-[#0A0A0A]">{a.paziente_nome}</div>
                        <div className="text-xs text-[#0A0A0A]/60">con {a.terapeuta_nome}</div>
                      </div>
                    </div>
                    <span className={`text-[10px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-full ${
                      a.stato === "confermato" ? "bg-green-100 text-green-800" :
                      a.stato === "completato" ? "bg-blue-100 text-blue-800" :
                      "bg-amber-100 text-amber-800"
                    }`}>{a.stato}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Availability */}
          {selectedDay.terapisti && selectedDay.terapisti.length > 0 ? (
            <>
              <div className="text-xs uppercase tracking-wide font-semibold text-green-700 mb-2">Disponibilità pubblicate</div>
              <div className="space-y-3">
                {selectedDay.terapisti.map(t => (
                  <div key={t.id} className="border border-[#0A0A0A]/10 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-[#0A0A0A]">{t.nome}</div>
                      <div className="flex gap-1">
                        {t.bozza && <span className="text-[10px] px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 font-semibold">bozza</span>}
                        {!t.documenti_verificati && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">non verificato</span>}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {t.slots.map(s => (
                        <span key={s} className="text-xs px-2 py-1 bg-green-100 text-green-900 rounded-md font-medium">{s}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            (!selectedDay.appuntamenti || selectedDay.appuntamenti.length === 0) && (
              <div className="text-sm text-[#0A0A0A]/55 text-center py-8">Nessun dato per questo giorno.</div>
            )
          )}
        </div>
      )}
    </div>
  );
}
