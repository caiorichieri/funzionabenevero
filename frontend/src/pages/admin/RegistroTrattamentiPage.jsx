import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { FileText, Plus, Download, Archive, Pencil, X, ShieldCheck, Loader2, Trash2 } from "lucide-react";

const RUOLO_LABELS = {
  titolare: "Titolare",
  responsabile: "Responsabile",
  contitolare: "Contitolare",
};

const RUOLO_COLORS = {
  titolare: "bg-[#F58A1F]/15 text-[#F58A1F] border-[#F58A1F]/30",
  responsabile: "bg-blue-500/15 text-blue-700 border-blue-500/30",
  contitolare: "bg-purple-500/15 text-purple-700 border-purple-500/30",
};

const EMPTY_ENTRY = {
  codice: "",
  denominazione: "",
  ruolo: "titolare",
  finalita: "",
  base_giuridica: "",
  categorie_interessati: "",
  categorie_dati: "",
  categorie_particolari: "",
  destinatari: "",
  trasferimenti_extra_ue: "Nessun trasferimento extra-UE",
  misure_sicurezza: "",
  termini_cancellazione: "",
  note: "",
};

export default function RegistroTrattamentiPage() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // draft entry, or null
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/registro-trattamenti`, { withCredentials: true });
      setEntries(r.data?.items || []);
    } catch (e) {
      setError(e.response?.data?.detail || "Errore caricamento registro");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    const nextCode = `T-${String(entries.length + 1).padStart(2, "0")}`;
    setEditing({ ...EMPTY_ENTRY, codice: nextCode });
    setError("");
  };

  const openEdit = (entry) => {
    setEditing({ ...entry });
    setError("");
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const payload = { ...editing };
      delete payload.id;
      delete payload.created_at;
      delete payload.updated_at;
      delete payload.archived;
      if (editing.id) {
        await axios.put(`${API}/admin/registro-trattamenti/${editing.id}`, payload, { withCredentials: true });
      } else {
        await axios.post(`${API}/admin/registro-trattamenti`, payload, { withCredentials: true });
      }
      setEditing(null);
      await load();
    } catch (e) {
      setError(e.response?.data?.detail || "Errore salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const archive = async (id) => {
    await axios.post(`${API}/admin/registro-trattamenti/${id}/archive`, {}, { withCredentials: true });
    await load();
    setConfirmDelete(null);
  };

  const downloadPdf = async () => {
    setDownloading(true);
    try {
      const r = await axios.get(`${API}/admin/registro-trattamenti/export/pdf`, {
        withCredentials: true, responseType: "blob",
      });
      const blob = new Blob([r.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `registro_trattamenti_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError("Errore download PDF");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-64" data-testid="registro-loading">
      <Loader2 className="w-8 h-8 animate-spin text-[#F58A1F]" />
    </div>
  );

  return (
    <div className="space-y-6" data-testid="registro-trattamenti-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit] flex items-center gap-2">
            <ShieldCheck className="w-8 h-8 text-[#F58A1F]" />
            Registro dei Trattamenti
          </h1>
          <p className="text-[#0A0A0A]/65 mt-1 text-sm">
            Art. 30 GDPR — Registro delle attività di trattamento di BIDOC SRL. Pronto per il Garante.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={downloadPdf}
            disabled={downloading || entries.length === 0}
            data-testid="registro-export-pdf-btn"
            className="px-4 py-2.5 bg-[#0A0A0A] text-white rounded-full text-sm font-medium inline-flex items-center gap-2 hover:bg-[#0A0A0A]/85 disabled:opacity-50"
          >
            {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Esporta PDF
          </button>
          <button
            onClick={openCreate}
            data-testid="registro-add-btn"
            className="px-4 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold rounded-full text-sm inline-flex items-center gap-2 hover:opacity-90"
          >
            <Plus className="w-4 h-4" /> Nuova voce
          </button>
        </div>
      </div>

      {error && !editing && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800" data-testid="registro-error">
          {error}
        </div>
      )}

      {/* Entries list */}
      <div className="grid gap-3">
        {entries.length === 0 && (
          <div className="p-12 bg-white/60 border border-dashed border-[#0A0A0A]/20 rounded-2xl text-center text-[#0A0A0A]/55" data-testid="registro-empty">
            Nessuna voce nel registro. Clicca &quot;Nuova voce&quot; per iniziare.
          </div>
        )}
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm p-5 hover:shadow-md transition-shadow"
            data-testid={`registro-entry-${entry.codice}`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-mono text-xs bg-[#0A0A0A] text-white px-2 py-0.5 rounded-full">
                    {entry.codice}
                  </span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${RUOLO_COLORS[entry.ruolo] || "bg-gray-100"}`}>
                    {RUOLO_LABELS[entry.ruolo]}
                  </span>
                </div>
                <h3 className="font-semibold text-[#0A0A0A] text-base leading-tight">{entry.denominazione}</h3>
                <p className="text-sm text-[#0A0A0A]/70 mt-2 line-clamp-2">{entry.finalita}</p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs text-[#0A0A0A]/55">
                  <span><strong>Interessati:</strong> {(entry.categorie_interessati || "").slice(0, 60)}{entry.categorie_interessati?.length > 60 ? "…" : ""}</span>
                  <span><strong>Retention:</strong> {(entry.termini_cancellazione || "").slice(0, 60)}{entry.termini_cancellazione?.length > 60 ? "…" : ""}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={() => openEdit(entry)}
                  data-testid={`registro-edit-${entry.codice}`}
                  className="p-2 rounded-xl hover:bg-[#F58A1F]/10 text-[#F58A1F]"
                  title="Modifica"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setConfirmDelete(entry)}
                  data-testid={`registro-archive-${entry.codice}`}
                  className="p-2 rounded-xl hover:bg-red-50 text-red-600"
                  title="Archivia"
                >
                  <Archive className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Confirm archive modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4" data-testid="registro-confirm-archive">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl">
            <h3 className="text-lg font-bold text-[#0A0A0A] flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-600" />
              Archivia voce {confirmDelete.codice}?
            </h3>
            <p className="text-sm text-[#0A0A0A]/70 mt-2">
              La voce non comparirà più nel registro attivo, ma resterà tracciata per audit.
            </p>
            <div className="flex gap-3 mt-6 justify-end">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 rounded-full border border-[#0A0A0A]/15 text-sm"
                data-testid="registro-archive-cancel"
              >
                Annulla
              </button>
              <button
                onClick={() => archive(confirmDelete.id)}
                className="px-4 py-2 rounded-full bg-red-600 text-white text-sm font-medium"
                data-testid="registro-archive-confirm"
              >
                Archivia
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit/create modal */}
      {editing && (
        <div className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4" data-testid="registro-edit-modal">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[92vh] overflow-hidden flex flex-col shadow-2xl">
            <div className="p-5 border-b border-[#0A0A0A]/10 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-[#0A0A0A] flex items-center gap-2">
                  <FileText className="w-5 h-5 text-[#F58A1F]" />
                  {editing.id ? "Modifica voce" : "Nuova voce"}
                </h2>
                <p className="text-xs text-[#0A0A0A]/55 mt-1">Art. 30 GDPR — attività di trattamento</p>
              </div>
              <button onClick={() => setEditing(null)} className="p-2 hover:bg-[#0A0A0A]/5 rounded-xl">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Field label="Codice *" value={editing.codice} onChange={v => setEditing({ ...editing, codice: v })} testid="registro-field-codice" />
                <Field label="Ruolo *" value={editing.ruolo} onChange={v => setEditing({ ...editing, ruolo: v })} type="select" options={[
                  { value: "titolare", label: "Titolare" },
                  { value: "responsabile", label: "Responsabile" },
                  { value: "contitolare", label: "Contitolare" },
                ]} testid="registro-field-ruolo" />
                <Field label="Denominazione *" value={editing.denominazione} onChange={v => setEditing({ ...editing, denominazione: v })} className="sm:col-span-1" testid="registro-field-denominazione" />
              </div>
              <FieldArea label="Finalità del trattamento *" value={editing.finalita} onChange={v => setEditing({ ...editing, finalita: v })} testid="registro-field-finalita" />
              <FieldArea label="Base giuridica (art. 6 GDPR) *" value={editing.base_giuridica} onChange={v => setEditing({ ...editing, base_giuridica: v })} rows={2} testid="registro-field-base-giuridica" />
              <FieldArea label="Categorie di interessati *" value={editing.categorie_interessati} onChange={v => setEditing({ ...editing, categorie_interessati: v })} rows={2} testid="registro-field-interessati" />
              <FieldArea label="Categorie di dati personali *" value={editing.categorie_dati} onChange={v => setEditing({ ...editing, categorie_dati: v })} testid="registro-field-dati" />
              <FieldArea label="Categorie particolari (art. 9 GDPR)" value={editing.categorie_particolari} onChange={v => setEditing({ ...editing, categorie_particolari: v })} rows={2} testid="registro-field-particolari" />
              <FieldArea label="Categorie di destinatari" value={editing.destinatari} onChange={v => setEditing({ ...editing, destinatari: v })} rows={2} testid="registro-field-destinatari" />
              <FieldArea label="Trasferimenti extra-UE (art. 44-49)" value={editing.trasferimenti_extra_ue} onChange={v => setEditing({ ...editing, trasferimenti_extra_ue: v })} rows={2} testid="registro-field-transferimenti" />
              <FieldArea label="Misure di sicurezza (art. 32 GDPR) *" value={editing.misure_sicurezza} onChange={v => setEditing({ ...editing, misure_sicurezza: v })} testid="registro-field-sicurezza" />
              <FieldArea label="Termini di cancellazione *" value={editing.termini_cancellazione} onChange={v => setEditing({ ...editing, termini_cancellazione: v })} rows={2} testid="registro-field-cancellazione" />
              <FieldArea label="Note" value={editing.note} onChange={v => setEditing({ ...editing, note: v })} rows={2} testid="registro-field-note" />

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800" data-testid="registro-modal-error">
                  {error}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-[#0A0A0A]/10 flex items-center justify-end gap-3 bg-[#0A0A0A]/[0.02]">
              <button
                onClick={() => setEditing(null)}
                className="px-4 py-2 rounded-full border border-[#0A0A0A]/15 text-sm"
                data-testid="registro-modal-cancel"
              >
                Annulla
              </button>
              <button
                onClick={save}
                disabled={saving}
                className="px-5 py-2 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold text-sm inline-flex items-center gap-2 disabled:opacity-50"
                data-testid="registro-modal-save"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                Salva
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange, type = "text", options = [], testid = "" }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">{label}</label>
      {type === "select" ? (
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          data-testid={testid}
          className="w-full px-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm bg-white"
        >
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <input
          type={type}
          value={value || ""}
          onChange={e => onChange(e.target.value)}
          data-testid={testid}
          className="w-full px-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm"
        />
      )}
    </div>
  );
}

function FieldArea({ label, value, onChange, rows = 3, testid = "" }) {
  return (
    <div>
      <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">{label}</label>
      <textarea
        rows={rows}
        value={value || ""}
        onChange={e => onChange(e.target.value)}
        data-testid={testid}
        className="w-full px-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm leading-relaxed"
      />
    </div>
  );
}
