import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Plus, CheckCircle, XCircle, Trash2, Eye, Clock, X, Edit2, Image as ImageIcon, Bold, Italic, List, Link as LinkIcon, LayoutTemplate } from "lucide-react";
import { safeHtml } from "@/utils/safeHtml";
import { BLOG_TEMPLATES } from "@/data/blogTemplates";
import BlogSeoAnalyzer from "@/components/admin/BlogSeoAnalyzer";

const CATEGORIE = ["Sessuologia","Terapia di coppia","Disfunzioni sessuali","Relazioni","Salute mentale","Altro"];

const STATO_BADGE = {
  bozza:      "bg-amber-100 text-amber-700",
  pubblicato: "bg-green-100 text-green-700",
  rifiutato:  "bg-red-100 text-red-700",
};

const STATO_LABEL = {
  bozza:      "In Revisione",
  pubblicato: "Pubblicato",
  rifiutato:  "Rifiutato",
};

function getSaveButtonLabel(saving, editing, publishLabel = "Pubblica") {
  if (saving) return "Salvataggio...";
  if (editing) return "Aggiorna";
  return publishLabel;
}

const EMPTY = { titolo: "", contenuto: "", categoria: "", tags: "", immagine_url: "" };

export default function AdminBlogPage() {
  const [articoli, setArticoli] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [filtro, setFiltro]     = useState("tutti");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing]   = useState(null);
  const [form, setForm]         = useState(EMPTY);
  const [saving, setSaving]     = useState(false);
  const [preview, setPreview]   = useState(null);
  const [error, setError]       = useState("");

  const load = useCallback(() => {
    setLoading(true);
    axios.get(`${API}/blog`, { withCredentials: true })
      .then(r => setArticoli(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditing(null); setForm(EMPTY); setError(""); setShowForm(true); };
  const openEdit   = (a) => {
    setEditing(a._id);
    setForm({
      titolo: a.titolo,
      contenuto: a.contenuto,
      categoria: a.categoria || "",
      tags: (a.tags || []).join(", "),
      immagine_url: a.immagine_url || "",
    });
    setError("");
    setShowForm(true);
  };

  const handleSave = async (e) => {
    e.preventDefault(); setSaving(true); setError("");
    const payload = { ...form, tags: form.tags ? form.tags.split(",").map(s=>s.trim()).filter(Boolean) : [] };
    try {
      if (editing) await axios.put(`${API}/blog/${editing}`, payload, { withCredentials: true });
      else         await axios.post(`${API}/blog`, payload, { withCredentials: true });
      setShowForm(false); load();
    } catch (err) {
      setError(err.response?.data?.detail || "Errore nel salvataggio");
    } finally { setSaving(false); }
  };

  const approva  = async (id) => { await axios.patch(`${API}/blog/${id}/approva`, {}, { withCredentials: true }); load(); };
  const rifiuta  = async (id) => { await axios.patch(`${API}/blog/${id}/rifiuta`, {}, { withCredentials: true }); load(); };
  const elimina  = async (id) => {
    if (!window.confirm("Eliminare questo articolo?")) return;
    await axios.delete(`${API}/blog/${id}`, { withCredentials: true }); load();
  };

  const filtered = filtro === "tutti" ? articoli : articoli.filter(a => a.stato === filtro);
  const contatori = {
    tutti: articoli.length,
    bozza: articoli.filter(a => a.stato === "bozza").length,
    pubblicato: articoli.filter(a => a.stato === "pubblicato").length,
    rifiutato: articoli.filter(a => a.stato === "rifiutato").length,
  };

  // ─── Editor toolbar helpers (image upload + inline formatting) ─────────
  const contenutoRef = useRef(null);
  const [uploading, setUploading] = useState(null); // null | "inline" | "cover"

  const insertAtCursor = (snippet) => {
    const ta = contenutoRef.current;
    if (!ta) { setForm(f => ({ ...f, contenuto: (f.contenuto || "") + snippet })); return; }
    const start = ta.selectionStart, end = ta.selectionEnd, val = ta.value;
    const next = val.slice(0, start) + snippet + val.slice(end);
    setForm(f => ({ ...f, contenuto: next }));
    // Restore cursor position after React commits the update
    setTimeout(() => {
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + snippet.length;
    }, 0);
  };

  const wrapSelection = (before, after = before) => {
    const ta = contenutoRef.current;
    if (!ta) return;
    const start = ta.selectionStart, end = ta.selectionEnd, val = ta.value;
    const selected = val.slice(start, end) || "...";
    const next = val.slice(0, start) + before + selected + after + val.slice(end);
    setForm(f => ({ ...f, contenuto: next }));
    setTimeout(() => {
      ta.focus();
      ta.selectionStart = start + before.length;
      ta.selectionEnd = start + before.length + selected.length;
    }, 0);
  };

  const uploadImage = async (kind, file) => {
    if (!file) return;
    if (!/^image\//.test(file.type)) { alert("Seleziona un file immagine (JPG, PNG, WEBP, GIF)."); return; }
    if (file.size > 5 * 1024 * 1024) { alert("Immagine troppo grande (max 5 MB)."); return; }
    setUploading(kind);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await axios.post(`${API}/blog/upload-image`, fd, { withCredentials: true });
      const url = r.data.url;
      if (kind === "cover") {
        setForm(f => ({ ...f, immagine_url: url }));
      } else {
        insertAtCursor(`\n<figure><img src="${url}" alt="" /></figure>\n`);
      }
    } catch (e) {
      alert(e.response?.data?.detail || "Errore durante l'upload");
    } finally {
      setUploading(null);
    }
  };

  const insertLink = () => {
    const href = window.prompt("URL del link:");
    if (!href) return;
    wrapSelection(`<a href="${href}" target="_blank" rel="noopener">`, "</a>");
  };

  const applyTemplate = (tpl) => {
    // If the user already typed something, ask before overwriting
    if ((form.titolo && form.titolo !== EMPTY.titolo) || (form.contenuto && form.contenuto.trim())) {
      if (!window.confirm(`Sostituire il contenuto attuale con il template "${tpl.label}"?`)) return;
    }
    setForm(f => ({
      ...f,
      titolo: tpl.titolo,
      contenuto: tpl.contenuto,
      tags: tpl.tags || f.tags,
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Blog</h1>
          <p className="text-[#0A0A0A]/65 mt-1">Gestisci e approva gli articoli dei terapisti</p>
        </div>
        <button data-testid="new-article-btn" onClick={openCreate}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium rounded-full transition-colors">
          <Plus className="w-4 h-4" /> Nuovo Articolo
        </button>
      </div>

      {/* Filtri */}
      <div className="flex gap-2 flex-wrap">
        {[
          { k: "tutti",      label: "Tutti" },
          { k: "bozza",      label: "In Revisione" },
          { k: "pubblicato", label: "Pubblicati" },
          { k: "rifiutato",  label: "Rifiutati" },
        ].map(f => (
          <button key={f.k} data-testid={`filtro-${f.k}`} onClick={() => setFiltro(f.k)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors flex items-center gap-2
              ${filtro === f.k ? "bg-[#0A0A0A] text-white" : "bg-white border border-[rgba(28,28,28,0.12)] text-[#0A0A0A]/75 hover:border-[#0A0A0A]"}`}>
            {f.label}
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${filtro === f.k ? "bg-white/20" : "bg-[rgba(28,28,28,0.08)]"}`}>
              {contatori[f.k]}
            </span>
          </button>
        ))}
      </div>

      {/* Alert revisione */}
      {contatori.bozza > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-3">
          <Clock className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <span className="text-amber-800 text-sm font-medium">
            {contatori.bozza} {contatori.bozza === 1 ? "articolo in attesa" : "articoli in attesa"} di approvazione
          </span>
        </div>
      )}

      {/* Lista articoli */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-[#0A0A0A]/50">
          <div className="text-4xl mb-3">📝</div>
          <div>Nessun articolo trovato</div>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(a => (
            <div key={a._id} data-testid={`articolo-${a._id}`}
              className="bg-white border border-[#0A0A0A]/10 rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap mb-2">
                    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATO_BADGE[a.stato] || "bg-gray-100 text-gray-600"}`}>
                      {STATO_LABEL[a.stato] || a.stato}
                    </span>
                    {a.categoria && (
                      <span className="text-xs bg-[#6B8FA3]/10 text-[#6B8FA3] px-2.5 py-1 rounded-full">{a.categoria}</span>
                    )}
                  </div>
                  <h3 className="font-semibold text-[#0A0A0A] text-lg leading-snug">{a.titolo}</h3>
                  <div className="text-sm text-[#0A0A0A]/55 mt-1 flex items-center gap-3">
                    <span>di <strong>{a.autore_nome}</strong></span>
                    <span>·</span>
                    <span>{new Date(a.created_at).toLocaleDateString("it-IT")}</span>
                  </div>
                  <p className="text-sm text-[#0A0A0A]/65 mt-2 line-clamp-2">{a.contenuto}</p>
                  {(a.tags||[]).length > 0 && (
                    <div className="flex gap-2 mt-2 flex-wrap">
                      {a.tags.map(t => (
                        <span key={t} className="text-xs bg-[rgba(28,28,28,0.06)] text-[#0A0A0A]/65 px-2 py-0.5 rounded-full">{t}</span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Azioni */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button data-testid={`preview-${a._id}`} onClick={() => setPreview(a)}
                    className="p-2 rounded-xl hover:bg-[#0A0A0A]/5 text-[#0A0A0A]/50" title="Anteprima">
                    <Eye className="w-4 h-4" />
                  </button>
                  <button data-testid={`edit-art-${a._id}`} onClick={() => openEdit(a)}
                    className="p-2 rounded-xl hover:bg-[#0A0A0A]/5 text-[#0A0A0A]/50" title="Modifica">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  {a.stato === "bozza" && (
                    <>
                      <button data-testid={`approva-${a._id}`} onClick={() => approva(a._id)}
                        className="p-2 rounded-xl hover:bg-green-50 text-green-600" title="Approva e Pubblica">
                        <CheckCircle className="w-4 h-4" />
                      </button>
                      <button data-testid={`rifiuta-${a._id}`} onClick={() => rifiuta(a._id)}
                        className="p-2 rounded-xl hover:bg-red-50 text-red-500" title="Rifiuta">
                        <XCircle className="w-4 h-4" />
                      </button>
                    </>
                  )}
                  <button data-testid={`elimina-${a._id}`} onClick={() => elimina(a._id)}
                    className="p-2 rounded-xl hover:bg-red-50 text-[#0A0A0A]/50 hover:text-red-600" title="Elimina">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal Crea/Modifica */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-6xl my-6">
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10">
              <h2 className="text-xl font-bold text-[#0A0A0A] font-[Outfit]">
                {editing ? "Modifica Articolo" : "Nuovo Articolo"}
              </h2>
              <button onClick={() => setShowForm(false)} className="p-2 rounded-xl hover:bg-[#0A0A0A]/5">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4">
              {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}

              {/* Template picker — only visible when creating a new article */}
              {!editing && (
                <div className="border border-[#0A0A0A]/10 rounded-2xl p-4 bg-gradient-to-br from-[#F58A1F]/5 to-[#F5D419]/5" data-testid="template-picker">
                  <div className="flex items-center gap-2 mb-3">
                    <LayoutTemplate className="w-4 h-4 text-[#F58A1F]" />
                    <span className="text-sm font-medium text-[#0A0A0A]">Parti da un modello (opzionale)</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {BLOG_TEMPLATES.map(tpl => (
                      <button
                        key={tpl.id}
                        type="button"
                        data-testid={`template-${tpl.id}`}
                        onClick={() => applyTemplate(tpl)}
                        className="text-left p-3 rounded-xl border border-[#0A0A0A]/10 bg-white hover:border-[#F58A1F] hover:shadow-sm transition-all"
                      >
                        <div className="text-sm font-semibold text-[#0A0A0A]">{tpl.label}</div>
                        <div className="text-xs text-[#0A0A0A]/55 mt-1 leading-snug">{tpl.description}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Meta row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-3">
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Titolo*</label>
                  <input data-testid="form-titolo" type="text" value={form.titolo} required
                    onChange={e => setForm({...form, titolo:e.target.value})}
                    placeholder="Titolo dell'articolo"
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Categoria</label>
                  <select value={form.categoria} onChange={e => setForm({...form, categoria:e.target.value})}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                    <option value="">Seleziona categoria</option>
                    {CATEGORIE.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Tag (virgola)</label>
                  <input type="text" value={form.tags} onChange={e => setForm({...form, tags:e.target.value})}
                    placeholder="sessuologia, coppia, ..."
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Immagine di copertina</label>
                  <div className="flex items-center gap-2">
                    <label className="flex-1 flex items-center gap-2 px-3 py-2.5 border border-dashed border-[#0A0A0A]/25 rounded-xl text-xs text-[#0A0A0A]/65 hover:bg-[#0A0A0A]/5 cursor-pointer">
                      <ImageIcon className="w-4 h-4" />
                      <span>{uploading === "cover" ? "Caricamento..." : (form.immagine_url ? "Sostituisci" : "Carica immagine")}</span>
                      <input
                        data-testid="upload-cover-image"
                        type="file" accept="image/*" className="hidden"
                        onChange={e => e.target.files?.[0] && uploadImage("cover", e.target.files[0])}
                      />
                    </label>
                    {form.immagine_url && (
                      <button type="button" onClick={() => setForm(f => ({ ...f, immagine_url: "" }))}
                        className="p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-100" title="Rimuovi">
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  {form.immagine_url && (
                    <img src={form.immagine_url.startsWith('http') ? form.immagine_url : `${API.replace('/api','')}${form.immagine_url}`}
                      alt="cover" className="mt-2 w-full h-24 object-cover rounded-xl border border-[#0A0A0A]/10" />
                  )}
                </div>
              </div>

              {/* Editor + Preview split */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-medium text-[#0A0A0A]">Contenuto* (HTML)</label>
                  <div className="text-xs text-[#0A0A0A]/50">{(form.contenuto || "").length} caratteri</div>
                </div>

                {/* Toolbar */}
                <div className="flex flex-wrap items-center gap-1 mb-2 p-1.5 bg-[#0A0A0A]/5 rounded-xl">
                  <button type="button" onClick={() => wrapSelection("<strong>", "</strong>")} title="Grassetto"
                    className="p-1.5 rounded-lg hover:bg-white text-[#0A0A0A]/70"><Bold className="w-4 h-4" /></button>
                  <button type="button" onClick={() => wrapSelection("<em>", "</em>")} title="Corsivo"
                    className="p-1.5 rounded-lg hover:bg-white text-[#0A0A0A]/70"><Italic className="w-4 h-4" /></button>
                  <button type="button" onClick={() => insertAtCursor("\n<h2>Titolo sezione</h2>\n")} title="Titolo H2"
                    className="p-1.5 px-2 rounded-lg hover:bg-white text-[#0A0A0A]/70 text-xs font-bold">H2</button>
                  <button type="button" onClick={() => insertAtCursor("\n<h3>Sottotitolo</h3>\n")} title="Titolo H3"
                    className="p-1.5 px-2 rounded-lg hover:bg-white text-[#0A0A0A]/70 text-xs font-bold">H3</button>
                  <button type="button" onClick={() => insertAtCursor("\n<p></p>\n")} title="Paragrafo"
                    className="p-1.5 px-2 rounded-lg hover:bg-white text-[#0A0A0A]/70 text-xs">P</button>
                  <button type="button" onClick={() => insertAtCursor("\n<ul>\n  <li>Punto</li>\n</ul>\n")} title="Lista"
                    className="p-1.5 rounded-lg hover:bg-white text-[#0A0A0A]/70"><List className="w-4 h-4" /></button>
                  <button type="button" onClick={insertLink} title="Link"
                    className="p-1.5 rounded-lg hover:bg-white text-[#0A0A0A]/70"><LinkIcon className="w-4 h-4" /></button>
                  <button type="button" onClick={() => insertAtCursor('\n<blockquote>Citazione</blockquote>\n')} title="Citazione"
                    className="p-1.5 px-2 rounded-lg hover:bg-white text-[#0A0A0A]/70 text-xs">""</button>
                  <div className="mx-1 h-5 w-px bg-[#0A0A0A]/15" />
                  <label className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-white text-[#0A0A0A]/70 cursor-pointer text-xs">
                    <ImageIcon className="w-4 h-4" />
                    <span>{uploading === "inline" ? "..." : "Immagine"}</span>
                    <input
                      data-testid="upload-inline-image"
                      type="file" accept="image/*" className="hidden"
                      onChange={e => e.target.files?.[0] && uploadImage("inline", e.target.files[0])}
                    />
                  </label>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {/* Editor */}
                  <textarea data-testid="form-contenuto" value={form.contenuto} required
                    ref={contenutoRef}
                    onChange={e => setForm({...form, contenuto:e.target.value})} rows={20}
                    placeholder='<p>Scrivi qui il contenuto in HTML. Usa la toolbar per formattare, aggiungere titoli, liste, link e immagini.</p>'
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none font-mono" />

                  {/* Right column: SEO analyzer + live preview */}
                  <div className="space-y-3">
                    <BlogSeoAnalyzer titolo={form.titolo} contenuto={form.contenuto} />
                    <div data-testid="live-preview" className="rounded-xl border border-[#0A0A0A]/10 bg-[#FAF9F6] p-5 overflow-auto max-h-[400px]">
                      <div className="text-[10px] uppercase tracking-widest text-[#0A0A0A]/40 mb-3">Anteprima</div>
                      {form.titolo && <h1 className="font-serif text-2xl text-[#0A0A0A] leading-tight mb-3">{form.titolo}</h1>}
                      {form.immagine_url && (
                        <img src={form.immagine_url.startsWith('http') ? form.immagine_url : `${API.replace('/api','')}${form.immagine_url}`}
                          alt="cover" className="w-full h-40 object-cover rounded-lg mb-4" />
                      )}
                      <div className="prose prose-sm max-w-none text-[#0A0A0A]" {...safeHtml(form.contenuto || '<p class="text-gray-400">L\'anteprima apparirà qui man mano che scrivi...</p>')} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-5 py-2.5 border border-[#0A0A0A]/15 rounded-full text-[#0A0A0A] hover:bg-[#0A0A0A]/5">
                  Annulla
                </button>
                <button data-testid="save-article-btn" type="submit" disabled={saving}
                  className="px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full font-medium disabled:opacity-50">
                  {getSaveButtonLabel(saving, editing, "Pubblica")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Anteprima */}
      {preview && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10">
              <div>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${STATO_BADGE[preview.stato]}`}>
                  {preview.stato}
                </span>
              </div>
              <button onClick={() => setPreview(null)} className="p-2 rounded-xl hover:bg-[#0A0A0A]/5">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <h2 className="text-2xl font-bold text-[#0A0A0A] font-[Outfit] mb-2">{preview.titolo}</h2>
              <div className="text-sm text-[#0A0A0A]/55 mb-4">
                di <strong>{preview.autore_nome}</strong> · {new Date(preview.created_at).toLocaleDateString("it-IT")}
              </div>
              {preview.immagine_url && (
                <img src={preview.immagine_url.startsWith('http') ? preview.immagine_url : `${API.replace('/api','')}${preview.immagine_url}`}
                  alt={preview.titolo} className="w-full h-48 object-cover rounded-xl mb-4" />
              )}
              <div className="prose text-[#0A0A0A] text-sm leading-relaxed max-w-none" {...safeHtml(preview.contenuto)} />
            </div>
            {preview.stato === "bozza" && (
              <div className="flex justify-end gap-3 p-6 border-t border-[#0A0A0A]/10">
                <button onClick={() => { rifiuta(preview._id); setPreview(null); }}
                  className="px-5 py-2.5 border border-red-200 text-red-600 rounded-full hover:bg-red-50 flex items-center gap-2">
                  <XCircle className="w-4 h-4" /> Rifiuta
                </button>
                <button onClick={() => { approva(preview._id); setPreview(null); }}
                  className="px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-full flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" /> Approva e Pubblica
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
