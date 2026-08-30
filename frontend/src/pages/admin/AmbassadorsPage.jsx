import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Plus, Edit2, Trash2, Upload, X, Eye, EyeOff, ImageIcon } from "lucide-react";

const EMPTY = { nome: "", ruolo: "", testimonianza: "", storia: "", ordine: 100, attivo: true };

export default function AdminAmbassadorsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);      // null | "new" | id
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [uploadingId, setUploadingId] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    axios.get(`${API}/admin/ambassadors`, { withCredentials: true })
      .then((r) => setItems(r.data || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => { setForm(EMPTY); setEditing("new"); setError(""); };
  const openEdit = (a) => {
    setForm({ nome: a.nome, ruolo: a.ruolo, testimonianza: a.testimonianza, storia: a.storia || "", ordine: a.ordine, attivo: a.attivo });
    setEditing(a.id); setError("");
  };
  const cancel = () => { setEditing(null); setForm(EMPTY); setError(""); };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      if (editing === "new") {
        await axios.post(`${API}/admin/ambassadors`, form, { withCredentials: true });
      } else {
        await axios.patch(`${API}/admin/ambassadors/${editing}`, form, { withCredentials: true });
      }
      cancel(); load();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore nel salvataggio");
    } finally { setSaving(false); }
  };

  const uploadFoto = async (id, file) => {
    if (!file) return;
    setUploadingId(id);
    try {
      const fd = new FormData();
      fd.append("file", file);
      await axios.post(`${API}/admin/ambassadors/${id}/foto`, fd, {
        withCredentials: true, headers: { "Content-Type": "multipart/form-data" },
      });
      load();
    } catch (err) {
      window.alert(err.response?.data?.detail || "Errore upload foto");
    } finally { setUploadingId(null); }
  };

  const remove = async (id) => {
    if (!window.confirm("Eliminare questo ambassador?")) return;
    await axios.delete(`${API}/admin/ambassadors/${id}`, { withCredentials: true });
    load();
  };

  return (
    <div data-testid="admin-ambassadors-page" className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Ambassador</h1>
          <p className="text-[#0A0A0A]/65 mt-1 text-sm">
            Persone con esperienza diretta che sostengono la pagina «Sessualità e Disabilità».
          </p>
        </div>
        <button
          data-testid="btn-new-ambassador"
          onClick={openNew}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white text-sm font-medium"
        >
          <Plus className="w-4 h-4" /> Nuovo ambassador
        </button>
      </div>

      {loading ? (
        <div className="text-center py-10 text-[#0A0A0A]/50">Caricamento...</div>
      ) : items.length === 0 ? (
        <div data-testid="empty" className="text-center py-12 bg-white border border-[#0A0A0A]/10 rounded-2xl text-[#0A0A0A]/55">
          Nessun ambassador. Clicca «Nuovo ambassador» per aggiungerne uno.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((a) => (
            <div key={a.id} data-testid={`amb-${a.id}`} className="bg-white border border-[#0A0A0A]/10 rounded-2xl overflow-hidden">
              <div className="relative h-40 bg-[#F8F5F0]">
                {a.foto_url ? (
                  <img src={a.foto_url} alt={a.nome} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#0A0A0A]/30">
                    <ImageIcon className="w-8 h-8" />
                  </div>
                )}
                {!a.attivo && (
                  <span className="absolute top-2 right-2 text-[10px] uppercase font-bold bg-red-500 text-white px-2 py-0.5 rounded-full">Nascosto</span>
                )}
                <label className="absolute bottom-2 right-2 cursor-pointer bg-white/90 hover:bg-white text-xs px-2 py-1 rounded-full inline-flex items-center gap-1">
                  <Upload className="w-3 h-3" /> {uploadingId === a.id ? "..." : "Foto"}
                  <input
                    type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
                    data-testid={`upload-foto-${a.id}`}
                    onChange={(e) => uploadFoto(a.id, e.target.files?.[0])}
                  />
                </label>
              </div>
              <div className="p-4">
                <div className="font-semibold">{a.nome}</div>
                <div className="text-xs text-[#F58A1F] uppercase tracking-wide mb-2">{a.ruolo}</div>
                <p className="text-xs text-[#0A0A0A]/65 italic line-clamp-2">«{a.testimonianza}»</p>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#0A0A0A]/8">
                  <span className="text-[10px] text-[#0A0A0A]/40">Ordine: {a.ordine}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <button data-testid={`edit-${a.id}`} onClick={() => openEdit(a)} className="p-1.5 rounded-lg hover:bg-[#0A0A0A]/5" title="Modifica">
                      <Edit2 className="w-4 h-4 text-[#0A0A0A]/60" />
                    </button>
                    <button data-testid={`delete-${a.id}`} onClick={() => remove(a.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-[#0A0A0A]/60 hover:text-red-600" title="Elimina">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal editor */}
      {editing && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div data-testid="ambassador-modal" className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10 sticky top-0 bg-white">
              <h2 className="text-lg font-bold font-[Outfit]">
                {editing === "new" ? "Nuovo ambassador" : "Modifica ambassador"}
              </h2>
              <button onClick={cancel} className="p-2 rounded-xl hover:bg-[#0A0A0A]/5">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={save} className="p-6 space-y-4">
              {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}
              <div>
                <label className="block text-sm font-medium mb-1">Nome</label>
                <input data-testid="fld-nome" type="text" required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Ruolo <span className="text-[#0A0A0A]/50">(es. Atleta paralimpico, Advocate)</span></label>
                <input data-testid="fld-ruolo" type="text" required value={form.ruolo} onChange={(e) => setForm({ ...form, ruolo: e.target.value })}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Testimonianza breve <span className="text-[#0A0A0A]/50">(max 280 caratteri)</span></label>
                <textarea data-testid="fld-testimonianza" required maxLength={280} rows={3} value={form.testimonianza}
                  onChange={(e) => setForm({ ...form, testimonianza: e.target.value })}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none" />
                <div className="text-xs text-[#0A0A0A]/45 text-right mt-1">{form.testimonianza.length}/280</div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Storia completa <span className="text-[#0A0A0A]/50">(facoltativa, mostrata nel modal quando l&apos;utente clicca sulla card)</span></label>
                <textarea data-testid="fld-storia" maxLength={3000} rows={7} value={form.storia}
                  onChange={(e) => setForm({ ...form, storia: e.target.value })}
                  className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none" />
                <div className="text-xs text-[#0A0A0A]/45 text-right mt-1">{form.storia.length}/3000</div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Ordine <span className="text-[#0A0A0A]/50">(più basso = prima)</span></label>
                  <input data-testid="fld-ordine" type="number" min={0} max={9999} value={form.ordine}
                    onChange={(e) => setForm({ ...form, ordine: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Stato</label>
                  <button type="button" data-testid="fld-attivo"
                    onClick={() => setForm({ ...form, attivo: !form.attivo })}
                    className={`w-full px-3 py-2.5 rounded-xl text-sm font-medium inline-flex items-center justify-center gap-2 ${form.attivo ? "bg-green-100 text-green-800 border border-green-200" : "bg-[#0A0A0A]/5 text-[#0A0A0A]/60 border border-[#0A0A0A]/10"}`}
                  >
                    {form.attivo ? <><Eye className="w-4 h-4" /> Visibile</> : <><EyeOff className="w-4 h-4" /> Nascosto</>}
                  </button>
                </div>
              </div>
              {editing !== "new" && (
                <p className="text-xs text-[#0A0A0A]/55">
                  💡 Per caricare o cambiare la foto, chiudi questa finestra e clicca «Foto» sulla card.
                </p>
              )}
              <div className="flex justify-end gap-3 pt-2 border-t border-[#0A0A0A]/10">
                <button type="button" onClick={cancel} className="px-5 py-2.5 border border-[#0A0A0A]/15 rounded-full text-[#0A0A0A] hover:bg-[#0A0A0A]/5">
                  Annulla
                </button>
                <button data-testid="btn-save" type="submit" disabled={saving}
                  className="px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full font-medium disabled:opacity-50">
                  {saving ? "Salvo..." : "Salva"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
