import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Plus, Search, Edit2, Trash2, ShieldCheck, ShieldX, ChevronDown, ChevronUp, X, CheckCircle, XCircle, Download } from "lucide-react";

const EMPTY_FORM = {
  nome: "", cognome: "", telefono: "", bio: "", anni_esperienza: "",
  genere: "", albo_numero: "", albo_ordine: "", albo_iscrizione_data: "",
  assicurazione_compagnia: "", assicurazione_numero_polizza: "", assicurazione_scadenza: "",
  prezzo_sessione: "", approccio_terapeutico: "", specializzazioni: "", lingue: "",
  iban: ""
};

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function getInsuranceExpiryColor(scadenzaIso) {
  const scad = new Date(scadenzaIso);
  const now = new Date();
  if (scad < now) return "text-red-600";
  if (scad < new Date(now.getTime() + THIRTY_DAYS_MS)) return "text-orange-600";
  return "text-green-600";
}

function getSaveButtonLabel(saving, editing, createLabel) {
  if (saving) return "Salvataggio...";
  if (editing) return "Aggiorna";
  return createLabel;
}

export default function TerapistiPage() {
  const [terapisti, setTerapisti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    axios.get(`${API}/terapisti`, { withCredentials: true })
      .then(r => setTerapisti(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setError("");
    setShowForm(true);
  };

  const openEdit = (t) => {
    setEditing(t._id);
    setForm({
      nome: t.nome || "", cognome: t.cognome || "", telefono: t.telefono || "",
      bio: t.bio || "", anni_esperienza: t.anni_esperienza || "",
      genere: t.genere || "", albo_numero: t.albo_numero || "",
      albo_ordine: t.albo_ordine || "", albo_iscrizione_data: t.albo_iscrizione_data || "",
      assicurazione_compagnia: t.assicurazione_compagnia || "",
      assicurazione_numero_polizza: t.assicurazione_numero_polizza || "",
      assicurazione_scadenza: t.assicurazione_scadenza || "",
      prezzo_sessione: t.prezzo_sessione || "",
      approccio_terapeutico: t.approccio_terapeutico || "",
      specializzazioni: (t.specializzazioni || []).join(", "),
      lingue: (t.lingue || []).join(", "),
      iban: t.iban || ""
    });
    setError("");
    setShowForm(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      anni_esperienza: form.anni_esperienza ? Number(form.anni_esperienza) : null,
      prezzo_sessione: form.prezzo_sessione ? Number(form.prezzo_sessione) : null,
      specializzazioni: form.specializzazioni ? form.specializzazioni.split(",").map(s => s.trim()).filter(Boolean) : [],
      lingue: form.lingue ? form.lingue.split(",").map(s => s.trim()).filter(Boolean) : []
    };
    try {
      if (editing) {
        await axios.put(`${API}/terapisti/${editing}`, payload, { withCredentials: true });
      } else {
        await axios.post(`${API}/terapisti`, payload, { withCredentials: true });
      }
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Eliminare questo terapeuta?")) return;
    await axios.delete(`${API}/terapisti/${id}`, { withCredentials: true });
    load();
  };

  const handleAutocert = async (id) => {
    if (!window.confirm("Firmare l'autocertificazione per questo terapeuta?")) return;
    await axios.post(`${API}/terapisti/${id}/autocertificazione`, {}, { withCredentials: true });
    load();
  };

  const handleToggleVerifica = async (t) => {
    const nextVal = !t.documenti_verificati;
    const msg = nextVal
      ? "Confermi di aver verificato i documenti e rendi il terapeuta visibile nel sito pubblico?"
      : "Rimuovi la verifica: il terapeuta non sarà più visibile nel sito pubblico. Procedere?";
    if (!window.confirm(msg)) return;
    await axios.patch(`${API}/admin/terapisti/${t._id}/verifica`, { verificato: nextVal }, { withCredentials: true });
    load();
  };

  const downloadDoc = (id, tipo) => {
    window.open(`${API}/admin/terapisti/${id}/documenti/${tipo}/download`, "_blank", "noopener");
  };

  const filtered = terapisti.filter(t =>
    `${t.nome} ${t.cognome} ${t.albo_numero || ""}`.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Terapisti</h1>
          <p className="text-[#0A0A0A]/65 mt-1">{terapisti.length} professionisti registrati</p>
        </div>
        <button data-testid="add-terapista-btn" onClick={openCreate}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium rounded-full transition-colors">
          <Plus className="w-4 h-4" /> Aggiungi Terapeuta
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#0A0A0A]/50" />
        <input data-testid="terapisti-search" type="text" value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Cerca per nome o numero Albo..."
          className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
      </div>

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-[#0A0A0A] border-t-transparent rounded-full animate-spin" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-[#0A0A0A]/55">Nessun terapeuta trovato</div>
      ) : (
        <div className="space-y-3">
          {filtered.map(t => (
            <div key={t._id} data-testid={`terapista-row-${t._id}`}
              className="bg-white border border-[#0A0A0A]/10 rounded-2xl shadow-sm overflow-hidden">
              <div className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-white/30 flex items-center justify-center font-semibold text-[#0A0A0A] font-[Outfit]">
                    {t.nome?.[0]}{t.cognome?.[0]}
                  </div>
                  <div>
                    <div className="font-semibold text-[#0A0A0A]">{t.nome} {t.cognome}</div>
                    <div className="text-sm text-[#0A0A0A]/55">
                      {t.albo_numero ? `Albo n. ${t.albo_numero}` : "Albo non inserito"} ·{" "}
                      {t.prezzo_sessione ? `€${t.prezzo_sessione}/sessione` : "Tariffa n.d."}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {t.documenti_verificati
                    ? <span data-testid={`badge-verificato-${t._id}`} className="flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full"><ShieldCheck className="w-3 h-3" /> Pubblico</span>
                    : <span data-testid={`badge-non-verificato-${t._id}`} className="flex items-center gap-1 text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full"><ShieldX className="w-3 h-3" /> Non pubblico</span>
                  }
                  <button data-testid={`toggle-verifica-${t._id}`} onClick={() => handleToggleVerifica(t)}
                    className={`p-2 rounded-xl ${t.documenti_verificati ? "hover:bg-red-50 text-red-600" : "hover:bg-green-50 text-green-600"}`}
                    title={t.documenti_verificati ? "Rimuovi verifica" : "Verifica documenti"}>
                    {t.documenti_verificati ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                  </button>
                  <button data-testid={`edit-terapista-${t._id}`} onClick={() => openEdit(t)}
                    className="p-2 rounded-xl hover:bg-[#0A0A0A]/5 text-[#0A0A0A]/55">
                    <Edit2 className="w-4 h-4" />
                  </button>
                  {!t.autocertificazione_firmata && (
                    <button data-testid={`autocert-${t._id}`} onClick={() => handleAutocert(t._id)}
                      className="p-2 rounded-xl hover:bg-green-50 text-green-600" title="Firma autocertificazione manuale">
                      <ShieldCheck className="w-4 h-4" />
                    </button>
                  )}
                  <button data-testid={`delete-terapista-${t._id}`} onClick={() => handleDelete(t._id)}
                    className="p-2 rounded-xl hover:bg-red-50 text-[#0A0A0A]/55 hover:text-red-600">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <button onClick={() => setExpanded(expanded === t._id ? null : t._id)}
                    className="p-2 rounded-xl hover:bg-[#0A0A0A]/5 text-[#0A0A0A]/55">
                    {expanded === t._id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Expanded details */}
              {expanded === t._id && (
                <div className="px-5 pb-5 border-t border-[rgba(28,28,28,0.06)] pt-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                  {/* Dati Professionali */}
                  <div>
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Dati Professionali</div>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-[#0A0A0A]/55">Albo:</span> <span className="text-[#0A0A0A] font-medium">{t.albo_numero || "—"}</span></div>
                      <div><span className="text-[#0A0A0A]/55">Ordine:</span> <span className="text-[#0A0A0A]">{t.albo_ordine || "—"}</span></div>
                      <div><span className="text-[#0A0A0A]/55">Iscrizione:</span> <span className="text-[#0A0A0A]">{t.albo_iscrizione_data || "—"}</span></div>
                      <div><span className="text-[#0A0A0A]/55">Esperienza:</span> <span className="text-[#0A0A0A]">{t.anni_esperienza ? `${t.anni_esperienza} anni` : "—"}</span></div>
                      <div><span className="text-[#0A0A0A]/55">Tariffa:</span> <span className="text-[#0A0A0A] font-semibold">{t.prezzo_sessione ? `€${t.prezzo_sessione}` : "—"}</span></div>
                    </div>
                  </div>

                  {/* Assicurazione */}
                  <div>
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Assicurazione</div>
                    <div className="space-y-2 text-sm">
                      <div><span className="text-[#0A0A0A]/55">Compagnia:</span> <span className="text-[#0A0A0A]">{t.assicurazione_compagnia || "—"}</span></div>
                      <div><span className="text-[#0A0A0A]/55">N. Polizza:</span> <span className="text-[#0A0A0A]">{t.assicurazione_numero_polizza || "—"}</span></div>
                      <div>
                        <span className="text-[#0A0A0A]/55">Scadenza:</span>{" "}
                        {t.assicurazione_scadenza ? (
                          <span className={`font-medium ${getInsuranceExpiryColor(t.assicurazione_scadenza)}`}>
                            {new Date(t.assicurazione_scadenza).toLocaleDateString("it-IT")}
                          </span>
                        ) : "—"}
                      </div>
                    </div>
                    {/* Specializzazioni sotto assicurazione */}
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mt-4 mb-2">Specializzazioni</div>
                    <div className="flex flex-wrap gap-1.5">
                      {(t.specializzazioni || []).map(s => (
                        <span key={s} className="text-xs bg-white/30 text-[#0A0A0A] px-2 py-1 rounded-full">{s}</span>
                      ))}
                      {(!t.specializzazioni || t.specializzazioni.length === 0) && <span className="text-sm text-[#0A0A0A]/55">—</span>}
                    </div>
                  </div>

                  {/* Disponibilità */}
                  <div>
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">
                      Disponibilità Settimanale
                    </div>
                    {(t.disponibilita || []).length === 0 ? (
                      <div className="text-sm text-[#0A0A0A]/50 italic">Nessuna disponibilità impostata</div>
                    ) : (
                      <div className="space-y-2">
                        {(t.disponibilita || []).map((d, i) => (
                          <div key={`${d.giorno}-${i}`} className="flex items-center gap-2">
                            <span className="text-xs font-semibold w-20 text-[#0A0A0A]">{d.giorno}</span>
                            <span className="text-xs bg-[#6B8FA3]/10 text-[#6B8FA3] px-2 py-1 rounded-full font-mono">
                              {d.ora_inizio} → {d.ora_fine}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Bio */}
                  <div>
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Biografia</div>
                    {t.bio ? (
                      <p className="text-sm text-[#0A0A0A]/75 leading-relaxed">
                        {t.bio.slice(0, 200)}{t.bio.length > 200 ? "..." : ""}
                      </p>
                    ) : (
                      <span className="text-sm text-[#0A0A0A]/50 italic">Nessuna biografia</span>
                    )}
                    {(t.lingue || []).length > 0 && (
                      <>
                        <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mt-4 mb-2">Lingue</div>
                        <div className="flex flex-wrap gap-1.5">
                          {t.lingue.map(l => (
                            <span key={l} className="text-xs bg-[rgba(28,28,28,0.06)] text-[#0A0A0A]/75 px-2 py-1 rounded-full">{l}</span>
                          ))}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Documenti & Verifica */}
                  <div className="md:col-span-2 xl:col-span-4 border-t border-[rgba(28,28,28,0.06)] pt-4">
                    <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">
                      Documenti & Verifica (DPR 445/2000)
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {["cv","assicurazione","laurea"].map((tipo) => {
                        const meta = (t.documenti || {})[tipo];
                        const labels = { cv: "Curriculum Vitae", assicurazione: "Assicurazione", laurea: "Laurea / Abilitazione" };
                        return (
                          <div key={tipo} className={`p-3 rounded-xl border ${meta ? "border-green-200 bg-green-50/30" : "border-[#0A0A0A]/10 bg-[rgba(28,28,28,0.02)]"}`}>
                            <div className="text-xs font-semibold text-[#0A0A0A]">{labels[tipo]}</div>
                            {meta ? (
                              <>
                                <div className="text-xs text-[rgba(28,28,28,0.55)] mt-1 truncate">{meta.filename} · {(meta.size/1024).toFixed(1)} KB</div>
                                <button
                                  data-testid={`admin-download-${tipo}-${t._id}`}
                                  type="button"
                                  onClick={() => downloadDoc(t._id, tipo)}
                                  className="mt-2 inline-flex items-center gap-1 text-xs text-[#0A0A0A] hover:underline"
                                >
                                  <Download className="w-3 h-3" /> Scarica
                                </button>
                              </>
                            ) : (
                              <div className="text-xs text-[#0A0A0A]/50 italic mt-1">Non caricato</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 text-xs text-[#0A0A0A]/65 flex flex-wrap gap-x-5 gap-y-1">
                      <span>Autocertificazione DPR 445: <strong className={t.autocertificazione_dpr445 || t.autocertificazione_firmata ? "text-green-700" : "text-amber-700"}>
                        {t.autocertificazione_dpr445 || t.autocertificazione_firmata ? "Firmata" : "Non firmata"}
                      </strong></span>
                      {t.autocertificazione_data && <span>Data: <strong className="text-[#0A0A0A]">{new Date(t.autocertificazione_data).toLocaleDateString("it-IT")}</strong></span>}
                      {t.autocertificazione_ip && <span>IP: <span className="font-mono">{t.autocertificazione_ip}</span></span>}
                      <span>Visibile pubblicamente: <strong className={t.documenti_verificati ? "text-green-700" : "text-red-600"}>{t.documenti_verificati ? "Sì" : "No"}</strong></span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal Form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl my-8">
            <div className="flex items-center justify-between p-6 border-b border-[#0A0A0A]/10">
              <h2 className="text-xl font-bold text-[#0A0A0A] font-[Outfit]">
                {editing ? "Modifica Terapeuta" : "Nuovo Terapeuta"}
              </h2>
              <button onClick={() => setShowForm(false)} className="p-2 rounded-xl hover:bg-[#0A0A0A]/5">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
              {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">{error}</div>}

              <div className="grid grid-cols-2 gap-4">
                {[["nome","Nome*"], ["cognome","Cognome*"]].map(([k,l]) => (
                  <div key={k}>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">{l}</label>
                    <input data-testid={`form-${k}`} type="text" value={form[k]}
                      onChange={e => setForm({...form,[k]:e.target.value})} required={k==="nome"||k==="cognome"}
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Genere</label>
                  <select data-testid="form-genere" value={form.genere} onChange={e => setForm({...form, genere:e.target.value})}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] bg-white">
                    <option value="">Seleziona</option>
                    <option value="M">Uomo</option>
                    <option value="F">Donna</option>
                    <option value="Altro">Non binario/Altro</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Telefono</label>
                  <input type="tel" value={form.telefono} onChange={e => setForm({...form, telefono:e.target.value})}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
              </div>

              <div className="border-t border-[#0A0A0A]/10 pt-4">
                <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Iscrizione Albo</div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">N. Albo</label>
                    <input data-testid="form-albo_numero" type="text" value={form.albo_numero} onChange={e => setForm({...form, albo_numero:e.target.value})}
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Data Iscrizione</label>
                    <input type="date" value={form.albo_iscrizione_data} onChange={e => setForm({...form, albo_iscrizione_data:e.target.value})}
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Anni di Esp.</label>
                    <input type="number" value={form.anni_esperienza} onChange={e => setForm({...form, anni_esperienza:e.target.value})} min="0"
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                </div>
                <div className="mt-3">
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Ordine di appartenenza</label>
                  <input type="text" value={form.albo_ordine} onChange={e => setForm({...form, albo_ordine:e.target.value})} placeholder="Es. Ordine degli Psicologi della Lombardia"
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                </div>
              </div>

              <div className="border-t border-[#0A0A0A]/10 pt-4">
                <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Assicurazione Professionale</div>
                <div className="grid grid-cols-3 gap-3">
                  {[["assicurazione_compagnia","Compagnia"],["assicurazione_numero_polizza","N. Polizza"]].map(([k,l]) => (
                    <div key={k}>
                      <label className="block text-sm font-medium text-[#0A0A0A] mb-1">{l}</label>
                      <input type="text" value={form[k]} onChange={e => setForm({...form,[k]:e.target.value})}
                        className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                    </div>
                  ))}
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Scadenza</label>
                    <input data-testid="form-assicurazione_scadenza" type="date" value={form.assicurazione_scadenza} onChange={e => setForm({...form, assicurazione_scadenza:e.target.value})}
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                </div>
                <div className="mt-3">
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">IBAN (per il bonifico mensile del 70%)</label>
                  <input
                    data-testid="form-iban"
                    type="text"
                    value={form.iban}
                    onChange={e => setForm({...form, iban: e.target.value.toUpperCase().replace(/\s/g, "")})}
                    placeholder="IT60 X054 2811 1010 0000 0123 456"
                    maxLength={34}
                    className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                  <p className="text-[10px] text-[#0A0A0A]/50 mt-1">IBAN italiano: 27 caratteri (IT + 2 cifre di controllo + 23 alfanumerici). Verrà mostrato in Pagamenti al momento del bonifico.</p>
                </div>
              </div>

              <div className="border-t border-[#0A0A0A]/10 pt-4">
                <div className="text-xs font-semibold text-[#0A0A0A]/55 uppercase tracking-wider mb-3">Profilo Professionale</div>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Specializzazioni (virgola)</label>
                      <input type="text" value={form.specializzazioni} onChange={e => setForm({...form, specializzazioni:e.target.value})} placeholder="Sessuologia, Terapia di coppia"
                        className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Lingue (virgola)</label>
                      <input type="text" value={form.lingue} onChange={e => setForm({...form, lingue:e.target.value})} placeholder="Italiano, Inglese"
                        className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Prezzo Sessione (€)</label>
                    <input data-testid="form-prezzo" type="number" value={form.prezzo_sessione} onChange={e => setForm({...form, prezzo_sessione:e.target.value})} min="0" step="5"
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Approccio Terapeutico</label>
                    <input type="text" value={form.approccio_terapeutico} onChange={e => setForm({...form, approccio_terapeutico:e.target.value})} placeholder="Es. Cognitivo-Comportamentale"
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Biografia</label>
                    <textarea data-testid="form-bio" value={form.bio} onChange={e => setForm({...form, bio:e.target.value})} rows={3} placeholder="Breve descrizione del professionista..."
                      className="w-full px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none" />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-5 py-2.5 border border-[#0A0A0A]/15 rounded-full text-[#0A0A0A] hover:bg-[#0A0A0A]/5 transition-colors">
                  Annulla
                </button>
                <button data-testid="save-terapista-btn" type="submit" disabled={saving}
                  className="px-5 py-2.5 bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white rounded-full font-medium transition-colors disabled:opacity-50">
                  {getSaveButtonLabel(saving, editing, "Crea Terapeuta")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
