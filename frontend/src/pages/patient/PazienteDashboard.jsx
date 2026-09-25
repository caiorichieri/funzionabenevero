import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { Calendar, Clock, Video, User, Save, CheckCircle, MessageCircle, Sparkles, FileText, Star } from "lucide-react";
import ChatPanel from "@/components/shared/ChatPanel";
import Mascotte from "@/components/shared/Mascotte";
import { formatApiError } from "@/lib/apiError";
import { formatItalianDateTime } from "@/lib/dateFormat";

function canJoin(dataOra, _durata = 50) {
  const now = new Date();
  const start = new Date(dataOra);
  const openAt = new Date(start.getTime() - 15 * 60000);
  const closeAt = new Date(start.getTime() + 15 * 60000);
  return now >= openAt && now <= closeAt;
}

function isStillActive(dataOra, _durata = 50) {
  // Keep the appointment in the "prossime" list until the join window closes
  // (start + 15 min). After that it becomes a passata / no-show.
  const start = new Date(dataOra);
  const closeAt = new Date(start.getTime() + 15 * 60000);
  return closeAt > new Date();
}

export default function PazienteDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [profilo, setProfilo] = useState(null);
  const [appuntamenti, setAppuntamenti] = useState([]);
  const [pendingReviews, setPendingReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editProfile, setEditProfile] = useState(false);
  const [form, setForm] = useState({
    nome:"", cognome:"", data_nascita:"", genere:"",
    codice_fiscale:"", telefono:"", citta:"", cap:""
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [cfError, setCfError] = useState("");

  const fetchData = useCallback(() => {
    Promise.all([
      axios.get(`${API}/pazienti/profilo/me`, { withCredentials: true }).catch(() => null),
      axios.get(`${API}/appuntamenti`, { withCredentials: true }).catch(() => ({ data: [] })),
      axios.get(`${API}/reviews/pending-appointments`, { withCredentials: true }).catch(() => ({ data: [] }))
    ]).then(([p, a, r]) => {
      if (p) {
        setProfilo(p.data);
        setForm({
          nome: p.data.nome||"", cognome: p.data.cognome||"",
          data_nascita: p.data.data_nascita||"", genere: p.data.genere||"",
          codice_fiscale: p.data.codice_fiscale||"", telefono: p.data.telefono||"",
          citta: p.data.citta||"", cap: p.data.cap||""
        });
      }
      setAppuntamenti(a.data);
      setPendingReviews(r.data || []);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const validateCF = (cf) => {
    cf = cf.toUpperCase().trim();
    if (cf.length !== 16) return false;
    const allowed = /^[A-Z0-9]{16}$/;
    return allowed.test(cf);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setCfError("");
    if (form.codice_fiscale && !validateCF(form.codice_fiscale)) {
      setCfError("Codice fiscale non valido (deve essere 16 caratteri alfanumerici)");
      return;
    }
    setSaving(true);
    try {
      const res = await axios.put(`${API}/pazienti/profilo/me`, form, { withCredentials: true });
      setProfilo(res.data); setSaved(true); setEditProfile(false);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setCfError(formatApiError(err, "Errore nel salvataggio"));
    } finally { setSaving(false); }
  };

  const prossime = appuntamenti.filter(a => isStillActive(a.data_ora, a.durata_minuti));
  const passate = appuntamenti.filter(a => !isStillActive(a.data_ora, a.durata_minuti));
  // Identify the therapist from the most-recent session (if any) so the patient
  // can always book another session with them without going through the
  // matching questionnaire again.
  const mioTerapeuta = (() => {
    const all = [...appuntamenti].sort((a, b) => new Date(b.data_ora) - new Date(a.data_ora));
    for (const a of all) {
      if (a.terapeuta_id) {
        return { id: a.terapeuta_id, nome: a.terapeuta_nome || "il tuo terapeuta" };
      }
    }
    return null;
  })();

  if (loading) return <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" /></div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Benvenuto, {user?.nome}!</h1>
        <p className="text-[#0A0A0A]/65 mt-1">Gestisci il tuo profilo e le tue sessioni</p>
      </div>

      {saved && <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm flex items-center gap-2"><CheckCircle className="w-4 h-4" /> Profilo aggiornato!</div>}

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-[#0A0A0A]/55 text-sm"><Calendar className="w-4 h-4" /> Sessioni Prenotate</div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{prossime.length}</div>
        </div>
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-[#0A0A0A]/55 text-sm"><Clock className="w-4 h-4" /> Sessioni Completate</div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{passate.filter(a=>a.stato==="completato").length}</div>
        </div>
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-[#0A0A0A]/55 text-sm"><User className="w-4 h-4" /> Totale Sessioni</div>
          <div className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">{appuntamenti.length}</div>
        </div>
      </div>

      {/* Profile */}
      <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">Il mio Profilo</h3>
          <button data-testid="edit-profile-btn" onClick={() => setEditProfile(!editProfile)}
            className="text-sm text-[#0A0A0A] hover:text-[#0A0A0A]/70">
            {editProfile ? "Annulla" : "Modifica"}
          </button>
        </div>

        {!editProfile ? (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            {[
              ["Nome", `${profilo?.nome||""} ${profilo?.cognome||""}`],
              ["Data di Nascita", profilo?.data_nascita ? new Date(profilo.data_nascita).toLocaleDateString("it-IT") : "—"],
              ["Genere", profilo?.genere || "—"],
              ["Codice Fiscale", profilo?.codice_fiscale || "—"],
              ["Telefono", profilo?.telefono || "—"],
              ["Città", profilo?.citta || "—"]
            ].map(([l, v]) => (
              <div key={l}>
                <div className="text-[#0A0A0A]/55 text-xs mb-0.5">{l}</div>
                <div className="text-[#0A0A0A] font-medium">{v}</div>
              </div>
            ))}
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            {cfError && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{cfError}</div>}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Nome</label>
                <input type="text" value={form.nome} onChange={e=>setForm({...form,nome:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Cognome</label>
                <input type="text" value={form.cognome} onChange={e=>setForm({...form,cognome:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data di Nascita</label>
                <input type="date" value={form.data_nascita} onChange={e=>setForm({...form,data_nascita:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Genere</label>
                <select value={form.genere} onChange={e=>setForm({...form,genere:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                  <option value="">Seleziona</option>
                  {["M","F","Non binario","Preferisco non specificare"].map(g=><option key={g} value={g}>{g}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Codice Fiscale</label>
              <input data-testid="paziente-cf-input" type="text" value={form.codice_fiscale}
                onChange={e=>setForm({...form,codice_fiscale:e.target.value.toUpperCase()})} maxLength={16}
                placeholder="RSSMRA90E15H501Z"
                className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Telefono</label>
                <input type="tel" value={form.telefono} onChange={e=>setForm({...form,telefono:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Città</label>
                <input type="text" value={form.citta} onChange={e=>setForm({...form,citta:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
            </div>
            <button data-testid="save-paziente-profile-btn" type="submit" disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full font-medium transition-colors disabled:opacity-50">
              <Save className="w-4 h-4" />
              {saving ? "Salvataggio..." : "Salva Modifiche"}
            </button>
          </form>
        )}
      </div>

      {/* Prenota nuova seduta — CTA sempre visibile quando c'è un terapeuta noto */}
      {mioTerapeuta && (
        <div className="bg-gradient-to-br from-[#0A0A0A] to-[#1a1a1a] rounded-2xl p-6 shadow-md text-white flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between">
          <div className="min-w-0 flex-1">
            <div className="text-[10px] tracking-[0.22em] uppercase font-semibold text-[#F5D419] mb-1">Il tuo terapeuta</div>
            <div className="font-bold text-lg text-white truncate">Dr. {mioTerapeuta.nome}</div>
            <p className="text-sm text-white/65 mt-1">Prenota una nuova seduta scegliendo tra gli orari disponibili sul suo profilo.</p>
          </div>
          <Link
            to={`/terapeuti/${mioTerapeuta.id}?prenota=1`}
            data-testid="dashboard-prenota-mio-terapeuta"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm hover:opacity-90 transition-opacity flex-shrink-0 whitespace-nowrap"
          >
            <Calendar className="w-4 h-4" /> Prenota una seduta
          </Link>
        </div>
      )}

      {/* Le mie fatture — link diretto per il paziente */}
      <Link
        to="/paziente/fatture"
        data-testid="dashboard-fatture-link"
        className="flex items-center gap-3 p-4 rounded-2xl bg-white border border-[#0A0A0A]/10 hover:border-[#0A0A0A]/20 hover:shadow-sm transition-all"
      >
        <div className="w-10 h-10 rounded-xl bg-[#F5D419]/15 flex items-center justify-center flex-shrink-0">
          <FileText className="w-5 h-5 text-[#F58A1F]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-[#0A0A0A] text-sm">Le mie fatture</div>
          <div className="text-xs text-[#0A0A0A]/55">Scarica le fatture sanitarie · Detraibili al 19% (730)</div>
        </div>
        <span className="text-[#0A0A0A]/40 text-lg">→</span>
      </Link>

      {/* Recensioni da lasciare — appare solo se ci sono sedute completate non ancora recensite */}
      {pendingReviews.length > 0 && (
        <div className="bg-gradient-to-br from-[#F5D419]/10 to-[#F58A1F]/10 border border-[#F5D419]/40 rounded-2xl p-5 shadow-sm" data-testid="pending-reviews-section">
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-[#F58A1F] fill-[#F58A1F]" />
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">
              Com'è andata la tua {pendingReviews.length === 1 ? "seduta" : `${pendingReviews.length} sedute`}?
            </h3>
          </div>
          <p className="text-sm text-[#0A0A0A]/70 mb-4">
            La tua opinione aiuta altri pazienti a scegliere. Ci vogliono 30 secondi.
          </p>
          <div className="space-y-2">
            {pendingReviews.slice(0, 3).map((r) => (
              <div
                key={r.appuntamento_id}
                className="flex items-center justify-between gap-3 p-3 bg-white rounded-xl border border-[#0A0A0A]/8"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm text-[#0A0A0A] truncate">
                    Dr. {r.terapista_nome} {r.terapista_cognome}
                  </div>
                  <div className="text-xs text-[#0A0A0A]/55">{formatItalianDateTime(r.data_ora)}</div>
                </div>
                <Link
                  to={`/recensione/${r.appuntamento_id}`}
                  data-testid={`leave-review-${r.appuntamento_id}`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white text-xs font-medium transition-colors flex-shrink-0 whitespace-nowrap"
                >
                  <Star className="w-3 h-3" /> Lascia recensione
                </Link>
              </div>
            ))}
          </div>
          {pendingReviews.length > 3 && (
            <p className="text-xs text-[#0A0A0A]/50 mt-3 text-center">
              +{pendingReviews.length - 3} altre sedute in attesa di recensione
            </p>
          )}
        </div>
      )}

      {/* Prossime sessioni */}
      {prossime.length > 0 ? (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-6 shadow-sm">
          <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4">Prossime Sessioni</h3>
          <div className="space-y-3">
            {prossime.map(a => {
              const joinable = canJoin(a.data_ora, a.durata_minuti);
              return (
                <div key={a._id} className="flex items-center justify-between py-3 border-b border-[rgba(28,28,28,0.06)] last:border-0 gap-3">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-white/30 flex items-center justify-center flex-shrink-0">
                      <Video className="w-4 h-4 text-[#0A0A0A]" />
                    </div>
                    <div className="min-w-0">
                      <div className="font-medium text-[#0A0A0A] text-sm truncate">{a.terapeuta_nome || "Terapeuta"}</div>
                      <div className="text-xs text-[#0A0A0A]/55">{formatItalianDateTime(a.data_ora)} · {a.durata_minuti} min</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">{a.stato}</span>
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
      ) : (
        <div className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-10 shadow-sm flex flex-col sm:flex-row items-center gap-8" data-testid="paziente-empty-sessions">
          <Mascotte name="embrulhado" size={120} animation="breathe" />
          <div className="flex-1 text-center sm:text-left">
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] text-lg mb-2">Ancora nessuna sessione</h3>
            <p className="text-sm text-[#0A0A0A]/65 mb-5 max-w-md">
              Quando inizi un percorso, le tue prossime sedute compariranno qui. Non c&apos;è fretta — fai un passo alla volta.
            </p>
            <a href="/questionario" className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full text-sm font-medium transition-colors">
              Trova il tuo specialista →
            </a>
          </div>
        </div>
      )}

      {/* Messaggi privati */}
      <div className="mt-6 bg-white rounded-2xl border border-[#0A0A0A]/10 p-5">
        <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] mb-4 flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-[#0A0A0A]" /> Messaggi con il tuo terapeuta
        </h3>
        <ChatPanel role="paziente" />
      </div>
    </div>
  );
}
