import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Video, Clock, User, AlertCircle, CheckCircle2, ChevronDown } from "lucide-react";
import { formatItalianDateTime } from "@/lib/dateFormat";

/**
 * Admin panel: attendance logs for video sessions.
 * Backed by `GET /api/admin/seduta-logs`. Each row shows the outcome computed
 * at start+15min (no-show detection) and the raw Daily.co participant snapshot.
 */
const OUTCOME_META = {
  entrambi_presenti: { label: "Entrambi presenti", color: "bg-green-50 text-green-700 border-green-200", icon: CheckCircle2 },
  no_show_paziente: { label: "No-show paziente", color: "bg-orange-50 text-orange-800 border-orange-200", icon: AlertCircle },
  no_show_terapeuta: { label: "No-show terapeuta", color: "bg-red-50 text-red-700 border-red-200", icon: AlertCircle },
  no_show_entrambi: { label: "Nessuno entrato", color: "bg-red-50 text-red-800 border-red-200", icon: AlertCircle },
};

export default function SedutaLogsSection() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [outcome, setOutcome] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [expanded, setExpanded] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (outcome) params.outcome = outcome;
      if (fromDate) params.from_date = new Date(fromDate).toISOString();
      if (toDate) params.to_date = new Date(new Date(toDate).getTime() + 86400000).toISOString();
      const r = await axios.get(`${API}/admin/seduta-logs`, { params, withCredentials: true });
      setItems(r.data?.items || []);
    } catch (e) {
      console.error("[SedutaLogsSection] load failed:", e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [outcome, fromDate, toDate]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-5 shadow-sm" data-testid="admin-seduta-logs">
      <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2 className="text-lg font-bold text-[#0A0A0A] font-[Outfit] flex items-center gap-2">
            <Video className="w-5 h-5" /> Log sedute
          </h2>
          <p className="text-xs text-[#0A0A0A]/55 mt-1">
            Presenze registrate al check di start+15 min. I dati sono snapshot da Daily.co conservati insieme all&apos;appuntamento.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-4">
        <select
          value={outcome}
          onChange={e => setOutcome(e.target.value)}
          data-testid="seduta-logs-outcome"
          className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-xs bg-white"
        >
          <option value="">Tutti gli esiti</option>
          {Object.entries(OUTCOME_META).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <input
          type="date" value={fromDate}
          onChange={e => setFromDate(e.target.value)}
          data-testid="seduta-logs-from"
          className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-xs"
          placeholder="Dal"
        />
        <input
          type="date" value={toDate}
          onChange={e => setToDate(e.target.value)}
          data-testid="seduta-logs-to"
          className="px-3 py-2 border border-[#0A0A0A]/15 rounded-full text-xs"
          placeholder="Al"
        />
        <button
          onClick={() => { setOutcome(""); setFromDate(""); setToDate(""); }}
          className="px-3 py-2 text-xs text-[#0A0A0A]/60 hover:text-[#0A0A0A] rounded-full border border-[#0A0A0A]/15"
        >
          Reset filtri
        </button>
      </div>

      {loading ? (
        <div className="py-8 text-center text-[#0A0A0A]/55 text-sm">Caricamento…</div>
      ) : items.length === 0 ? (
        <div className="py-8 text-center text-[#0A0A0A]/55 text-sm" data-testid="seduta-logs-empty">
          Nessun log disponibile con i filtri attuali.
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(it => {
            const meta = OUTCOME_META[it.outcome] || { label: it.outcome || "—", color: "bg-gray-100 text-gray-700", icon: Clock };
            const Icon = meta.icon;
            const isOpen = expanded === it.id;
            return (
              <div
                key={it.id}
                data-testid={`seduta-log-row-${it.appuntamento_id}`}
                className={`border rounded-xl p-3 transition-shadow ${isOpen ? "shadow-md" : "shadow-sm hover:shadow-md"}`}
              >
                <button
                  type="button"
                  className="w-full flex items-center justify-between gap-3 text-left"
                  onClick={() => setExpanded(isOpen ? null : it.id)}
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold border ${meta.color}`}>
                      <Icon className="w-3 h-3" /> {meta.label}
                    </span>
                    <div className="min-w-0 text-sm">
                      <div className="font-medium text-[#0A0A0A] truncate">
                        Dr. {it.terapeuta?.nome || "—"} · Pz. {it.paziente?.iniziali || "—"}
                      </div>
                      <div className="text-xs text-[#0A0A0A]/55">
                        {it.data_ora ? formatItalianDateTime(it.data_ora) : "—"}
                      </div>
                    </div>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-[#0A0A0A]/40 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                </button>
                {isOpen && (
                  <div className="mt-3 pt-3 border-t border-[#0A0A0A]/5 space-y-2 text-xs text-[#0A0A0A]/70" data-testid={`seduta-log-detail-${it.appuntamento_id}`}>
                    <div className="grid grid-cols-2 gap-2">
                      <div>Paziente entrato: <strong className={it.paziente_joined ? "text-green-700" : "text-red-700"}>{it.paziente_joined ? "sì" : "no"}</strong></div>
                      <div>Terapeuta entrato: <strong className={it.terapeuta_joined ? "text-green-700" : "text-red-700"}>{it.terapeuta_joined ? "sì" : "no"}</strong></div>
                      <div>Snapshot: {it.snapshot_at ? new Date(it.snapshot_at).toLocaleString("it-IT", { timeZone: "Europe/Rome" }) : "—"}</div>
                      <div>Room: <span className="font-mono">{it.room_name || "—"}</span></div>
                    </div>
                    {(it.presenze || []).length > 0 ? (
                      <div className="mt-2">
                        <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/40 mb-1">Partecipanti (Daily.co)</div>
                        <ul className="space-y-1">
                          {it.presenze.map((p, i) => (
                            <li key={i} className="flex items-center gap-2 pl-2 border-l-2 border-[#0A0A0A]/10">
                              <User className="w-3 h-3 text-[#0A0A0A]/40" />
                              <span>{p.user_name || "—"}</span>
                              {p.join_time && <span className="text-[#0A0A0A]/45">· join {new Date(p.join_time).toLocaleString("it-IT", { timeZone: "Europe/Rome" })}</span>}
                              {p.duration_seconds != null && <span className="text-[#0A0A0A]/45">· {Math.round(p.duration_seconds / 60)} min</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className="text-[#0A0A0A]/45">Nessun partecipante registrato in stanza.</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
