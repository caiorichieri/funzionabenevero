import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Plus, Calendar, Clock, Video, CheckCircle, XCircle, X } from "lucide-react";
import SedutaLogsSection from "./SedutaLogsSection";

const STATI_COLORS = {
  prenotato: "bg-blue-100 text-blue-700",
  confermato: "bg-green-100 text-green-700",
  completato: "bg-[#6B8FA3]/10 text-[#6B8FA3]",
  cancellato: "bg-red-100 text-red-700"
};

const EMPTY = { terapeuta_id: "", paziente_id: "", data_ora: "", durata_minuti: 50, tipo: "online", note: "" };

export default function AppuntamentiPage() {
  const [appuntamenti, setAppuntamenti] = useState([]);
  const [terapisti, setTerapisti] = useState([]);
  const [pazienti, setPazienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      axios.get(`${API}/appuntamenti`, { withCredentials: true }),
      axios.get(`${API}/terapisti`, { withCredentials: true }),
      axios.get(`${API}/pazienti`, { withCredentials: true })
    ]).then(([a, t, p]) => {
      setAppuntamenti(a.data); setTerapisti(t.data); setPazienti(p.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    try {
      await axios.post(`${API}/appuntamenti`, { ...form, durata_minuti: Number(form.durata_minuti) }, { withCredentials: true });
      setShowForm(false); setForm(EMPTY); load();
    } catch (err) {
      setError(err.response?.data?.detail || "Errore nel salvataggio");
    } finally { setSaving(false); }
  };

  const updateStato = async (id, stato) => {
    await axios.patch(`${API}/appuntamenti/${id}/stato`, { stato }, { withCredentials: true });
    load();
  };

  const deleteApp = async (id) => {
    if (!window.confirm("Eliminare questo appuntamento?")) return;
    await axios.delete(`${API}/appuntamenti/${id}`, { withCredentials: true });
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Appuntamenti</h1>
          <p className="text-[#0A0A0A]/65 mt-1">{appuntamenti.length} sessioni totali</p>
        </div>
        <button data-testid="add-appuntamento-btn" onClick={() => { setForm(EMPTY); setError(""); setShowForm(true); }}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium rounded-full transition-colors">
          <Plus className="w-4 h-4" /> Nuovo Appuntamento
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" /></div>
      ) : appuntamenti.length === 0 ? (
        <div className="text-center py-12 text-[#0A0A0A]/55">Nessun appuntamento trovato</div>
      ) : (
        <div className="space-y-3">
          {appuntamenti.map(a => (
            <div key={a._id} data-testid={`appuntamento-${a._id}`}
              className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-white/30 flex flex-col items-center justify-center flex-shrink-0">
                  <Calendar className="w-5 h-5 text-[#0A0A0A]" />
                </div>
                <div>
                  <div className="font-semibold text-[#0A0A0A]">
                    {a.terapeuta_nome || "Terapeuta"} → {a.paziente_nome || "Paziente"}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-sm text-[#0A0A0A]/55">
                    <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{new Date(a.data_ora).toLocaleString("it-IT")}</span>
                    <span>{a.durata_minuti} min</span>
                    {a.tipo === "online" && <span className="flex items-center gap-1"><Video className="w-3.5 h-3.5" /> Online</span>}
                  </div>
                  {a.note && <div className="text-xs text-[#0A0A0A]/55 mt-1">{a.note}</div>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${STATI_COLORS[a.stato] || "bg-gray-100 text-gray-700"}`}>
                  {a.stato}
                </span>
                {a.stato === "prenotato" && (
                  <button onClick={() => updateStato(a._id, "confermato")} title="Conferma"
                    className="p-2 rounded-lg hover:bg-green-50 text-green-600">
                    <CheckCircle className="w-4 h-4" />
                  </button>
                )}
                {["prenotato","confermato"].includes(a.stato) && (
                  <button onClick={() => updateStato(a._id, "cancellato")} title="Cancella"
                    className="p-2 rounded-lg hover:bg-red-50 text-red-600">
                    <XCircle className="w-4 h-4" />
                  </button>
                )}
                {a.stato === "confermato" && (
                  <button onClick={() => updateStato(a._id, "completato")} title="Completa"
                    className="p-2 rounded-lg hover:bg-[#6B8FA3]/10 text-[#6B8FA3]">
                    <CheckCircle className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <SedutaLogsSection />

      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10">
              <h2 className="text-xl font-bold text-[#0A0A0A] font-[Outfit]">Nuovo Appuntamento</h2>
              <button onClick={() => setShowForm(false)}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4">
              {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Terapeuta*</label>
                <select data-testid="app-terapeuta" value={form.terapeuta_id} required
                  onChange={e => setForm({...form, terapeuta_id:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                  <option value="">Seleziona terapeuta</option>
                  {terapisti.map(t => <option key={t._id} value={t._id}>{t.nome} {t.cognome}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Paziente*</label>
                <select data-testid="app-paziente" value={form.paziente_id} required
                  onChange={e => setForm({...form, paziente_id:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                  <option value="">Seleziona paziente</option>
                  {pazienti.map(p => <option key={p._id} value={p._id}>{p.nome} {p.cognome}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data e Ora*</label>
                <input data-testid="app-data" type="datetime-local" value={form.data_ora} required
                  onChange={e => setForm({...form, data_ora:e.target.value})}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Durata (min)</label>
                  <select value={form.durata_minuti} onChange={e => setForm({...form, durata_minuti:Number(e.target.value)})}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                    {[30,45,50,60,90].map(d => <option key={d} value={d}>{d} minuti</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Tipo</label>
                  <select value={form.tipo} onChange={e => setForm({...form, tipo:e.target.value})}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                    <option value="online">Online</option>
                    <option value="in_presenza">In Presenza</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Note</label>
                <textarea value={form.note} onChange={e => setForm({...form, note:e.target.value})} rows={2}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none" />
              </div>

              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-5 py-2.5 border border-[#0A0A0A]/15 rounded-full text-[#0A0A0A] hover:bg-[#0A0A0A]/5">
                  Annulla
                </button>
                <button data-testid="save-appuntamento-btn" type="submit" disabled={saving}
                  className="px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full font-medium disabled:opacity-50">
                  {saving ? "Salvataggio..." : "Crea Appuntamento"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
