import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { BookHeart, ArrowLeft, Loader2, Check } from "lucide-react";

const MOODS = {
  felice:     { emoji: "😊", label: "Felice",     color: "from-emerald-400 to-teal-400" },
  sereno:     { emoji: "🙂", label: "Sereno",     color: "from-sky-400 to-cyan-400" },
  neutro:     { emoji: "😐", label: "Neutro",     color: "from-stone-300 to-stone-400" },
  ansioso:    { emoji: "😟", label: "Ansioso",    color: "from-amber-400 to-yellow-500" },
  triste:     { emoji: "😢", label: "Triste",     color: "from-blue-500 to-indigo-500" },
  arrabbiato: { emoji: "😠", label: "Arrabbiato", color: "from-red-500 to-orange-500" },
};

const formatDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const same = d.toDateString() === now.toDateString();
  const y = new Date(now); y.setDate(now.getDate() - 1);
  const yest = d.toDateString() === y.toDateString();
  const time = d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  if (same) return `Oggi · ${time}`;
  if (yest) return `Ieri · ${time}`;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "long" }) + ` · ${time}`;
};

export default function TerapeutaDiarioPazientePage() {
  const { pazienteId } = useParams();
  const [entries, setEntries] = useState([]);
  const [paziente, setPaziente] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, p] = await Promise.all([
        axios.get(`${API}/diario/paziente/${pazienteId}`, { withCredentials: true }),
        axios.get(`${API}/pazienti/${pazienteId}`, { withCredentials: true }).catch(() => ({ data: null })),
      ]);
      setEntries(d.data?.items || []);
      setPaziente(p.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Errore caricamento diario");
    } finally {
      setLoading(false);
    }
  }, [pazienteId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-[#F58A1F]" /></div>;

  return (
    <div className="space-y-4" data-testid="terapeuta-diario-page">
      <div className="flex items-center gap-3">
        <Link to="/terapeuta/pazienti" className="p-2 hover:bg-[#0A0A0A]/5 rounded-xl" data-testid="diario-back">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 text-[#0A0A0A]/60 text-xs uppercase tracking-widest font-medium">
            <BookHeart className="w-3.5 h-3.5" /> Diario emozionale
          </div>
          <h1 className="text-2xl font-bold text-[#0A0A0A] font-[Outfit]">
            {paziente ? `${paziente.nome} ${paziente.cognome}` : "Diario del paziente"}
          </h1>
          <p className="text-xs text-[#0A0A0A]/55 mt-0.5">
            {entries.length} {entries.length === 1 ? "nota condivisa" : "note condivise"} — solo lettura
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800">{error}</div>
      )}

      {entries.length === 0 ? (
        <div className="py-14 text-center bg-white rounded-2xl border border-dashed border-[#0A0A0A]/10">
          <BookHeart className="w-10 h-10 mx-auto text-[#F58A1F]/40 mb-3" />
          <p className="text-[#0A0A0A]/60 text-sm">Il paziente non ha ancora condiviso note nel diario.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((e) => {
            const mood = MOODS[e.mood] || MOODS.neutro;
            return (
              <div key={e.id} className="bg-white rounded-2xl p-4 shadow-sm border border-[#0A0A0A]/5" data-testid={`terapeuta-diario-entry-${e.id}`}>
                <div className="flex items-start gap-3">
                  <div className={`w-11 h-11 rounded-2xl bg-gradient-to-br ${mood.color} flex items-center justify-center text-2xl shadow-sm`}>
                    {mood.emoji}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-medium">{mood.label}</span>
                      <span className="text-[10px] text-[#0A0A0A]/40">·</span>
                      <span className="text-xs text-[#0A0A0A]/55">{formatDate(e.created_at)}</span>
                      {e.letto_da_terapeuta && (
                        <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                          <Check className="w-2.5 h-2.5" /> Letto
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-[#0A0A0A] leading-relaxed mt-1.5 whitespace-pre-wrap">{e.contenuto}</p>
                    {e.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {e.tags.map(t => (
                          <span key={t} className="text-[10px] px-2 py-0.5 bg-[#F58A1F]/10 text-[#F58A1F] rounded-full">#{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
