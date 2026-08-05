import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { useAuth } from "@/contexts/AuthContext";
import { Calendar, Clock, Users, ShieldCheck, Video, FileText, MessageCircle } from "lucide-react";
import ChatPanel from "@/components/shared/ChatPanel";

function canJoin(dataOra, durata = 50) {
  const now = new Date();
  const start = new Date(dataOra);
  const end = new Date(start.getTime() + durata * 60000);
  const openAt = new Date(start.getTime() - 15 * 60000);
  const closeAt = new Date(end.getTime() + 15 * 60000);
  return now >= openAt && now <= closeAt;
}

export default function TerapistaDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [profilo, setProfilo] = useState(null);
  const [appuntamenti, setAppuntamenti] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(() => {
    Promise.all([
      axios.get(`${API}/terapisti/profilo/me`, { withCredentials: true }).catch(() => null),
      axios.get(`${API}/appuntamenti`, { withCredentials: true }).catch(() => ({ data: [] }))
    ]).then(([p, a]) => {
      if (p) setProfilo(p.data);
      setAppuntamenti(a.data);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const oggi = appuntamenti.filter(a => {
    const d = new Date(a.data_ora);
    const now = new Date();
    return d.toDateString() === now.toDateString();
  });
  const prossime = appuntamenti.filter(a => new Date(a.data_ora) > new Date()).slice(0, 5);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">
          Benvenuta, {user?.nome}!
        </h1>
        <p className="text-[#0A0A0A]/65 mt-1">Ecco il riepilogo della tua attività</p>
      </div>

      {/* Autocertificazione alert */}
      {profilo && !profilo.autocertificazione_firmata && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
          <ShieldCheck className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-amber-800">Autocertificazione non firmata</div>
            <div className="text-sm text-amber-600 mt-1">
              Completa il tuo profilo e firma l&apos;autocertificazione per essere visibile ai pazienti.
            </div>
            <a href="/terapeuta/profilo"
              className="mt-2 inline-block text-sm font-medium text-amber-700 hover:text-amber-800">
              Vai al profilo →
            </a>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <Calendar className="w-5 h-5 text-[#0A0A0A]" />
            <span className="text-sm text-[#0A0A0A]/55">Sessioni oggi</span>
          </div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{oggi.length}</div>
        </div>
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <Clock className="w-5 h-5 text-[#6B8FA3]" />
            <span className="text-sm text-[#0A0A0A]/55">Prossime sessioni</span>
          </div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{prossime.length}</div>
        </div>
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-5 h-5 text-green-600" />
            <span className="text-sm text-[#0A0A0A]/55">Totale sessioni</span>
          </div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{appuntamenti.length}</div>
        </div>
      </div>

      {/* Profile completion */}
      {profilo && (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">Completamento Profilo</h3>
            <a href="/terapeuta/profilo" className="text-sm text-[#0A0A0A] hover:text-[#0A0A0A]/70">Modifica</a>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Biografia", done: !!profilo.bio },
              { label: "Albo Iscrizione", done: !!profilo.albo_numero },
              { label: "Assicurazione", done: !!profilo.assicurazione_numero_polizza },
              { label: "Autocertificazione", done: profilo.autocertificazione_firmata },
              { label: "Disponibilità", done: (profilo.disponibilita || []).length > 0 },
              { label: "Specializzazioni", done: (profilo.specializzazioni || []).length > 0 },
              { label: "Prezzo Sessione", done: !!profilo.prezzo_sessione },
              { label: "Foto Profilo", done: false }
            ].map(item => (
              <div key={item.label} className={`flex items-center gap-2 p-3 rounded-xl text-sm
                ${item.done ? "bg-green-50 text-green-700" : "bg-[rgba(28,28,28,0.04)] text-[#0A0A0A]/55"}`}>
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${item.done ? "bg-green-500" : "bg-[rgba(28,28,28,0.2)]"}`} />
                {item.label}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prossime sessioni */}
      {prossime.length > 0 && (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Prossime Sessioni</h3>
          <div className="space-y-3">
            {prossime.map(a => {
              const joinable = canJoin(a.data_ora, a.durata_minuti);
              return (
                <div key={a._id} className="flex items-center justify-between py-3 border-b border-[rgba(28,28,28,0.06)] last:border-0 gap-3">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-[#6B8FA3]/10 flex items-center justify-center flex-shrink-0">
                      <Video className="w-4 h-4 text-[#6B8FA3]" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-[#0A0A0A] text-sm truncate">{a.paziente_nome || "Paziente"}</div>
                      <div className="text-xs text-[#0A0A0A]/55">
                        {new Date(a.data_ora).toLocaleString("it-IT")} · {a.durata_minuti} min
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      a.stato === "confermato" ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-700"
                    }`}>{a.stato}</span>
                    {joinable && (
                      <button
                        data-testid={`join-video-${a._id}`}
                        onClick={() => navigate(`/seduta/${a._id}`)}
                        className="px-4 py-2 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full text-xs font-medium flex items-center gap-1.5"
                      >
                        <Video className="w-3 h-3" /> Entra
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Messaggi privati con i pazienti */}
      <div className="mt-6 bg-white rounded-2xl border border-[#0A0A0A]/10 p-5">
        <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4 flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-[#0A0A0A]" /> Messaggi con i pazienti
        </h3>
        <ChatPanel role="terapeuta" />
      </div>
    </div>
  );
}
