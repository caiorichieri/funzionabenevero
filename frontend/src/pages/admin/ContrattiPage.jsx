import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ScrollText, Plus, Check, History, ShieldCheck, X } from "lucide-react";

const KIND_LABELS = {
  mandato_all_incasso: "Mandato all'incasso con Rappresentanza",
};

const DEFAULT_NEW = { kind: "mandato_all_incasso", title: "", content_html: "" };

export default function ContrattiPage() {
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // draft object
  const [selectedForAudit, setSelectedForAudit] = useState(null);
  const [audit, setAudit] = useState({ loading: false, items: [] });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/contracts`, { withCredentials: true });
      setContracts(r.data?.items || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const currentMandato = contracts.find(c => c.kind === "mandato_all_incasso" && c.is_current);
  const history = contracts.filter(c => c.kind === "mandato_all_incasso" && !c.is_current);

  const startEditFromCurrent = () => {
    if (!currentMandato) {
      setEditing({ ...DEFAULT_NEW, title: KIND_LABELS.mandato_all_incasso });
      return;
    }
    setEditing({
      kind: currentMandato.kind,
      title: currentMandato.title,
      content_html: currentMandato.content_html,
    });
  };

  const publishNewVersion = async () => {
    if (!editing?.content_html?.trim()) return;
    setSaving(true);
    try {
      await axios.post(`${API}/admin/contracts`, editing, { withCredentials: true });
      setEditing(null);
      await load();
    } catch (e) {
      alert("Errore nel salvataggio: " + (e.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  const openAudit = async (contract) => {
    setSelectedForAudit(contract);
    setAudit({ loading: true, items: [] });
    try {
      const r = await axios.get(`${API}/admin/contracts/${contract.id}/acceptances`, { withCredentials: true });
      setAudit({ loading: false, items: r.data?.items || [] });
    } catch {
      setAudit({ loading: false, items: [] });
    }
  };

  if (loading) return <div className="p-6 text-[#0A0A0A]/60">Caricamento...</div>;

  return (
    <div className="space-y-8" data-testid="admin-contratti-page">
      <div>
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Contratti</h1>
        <p className="text-[#0A0A0A]/65 mt-1">
          Testi legali che i terapeuti devono accettare per operare sulla piattaforma. Ogni nuova versione è immutabile e tracciata.
        </p>
      </div>

      {/* Current mandato card */}
      <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm overflow-hidden" data-testid="mandato-card">
        <div className="p-6 border-b border-[#0A0A0A]/10 flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-[#F58A1F]/15 flex items-center justify-center flex-shrink-0">
              <ScrollText className="w-6 h-6 text-[#F58A1F]" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-[#0A0A0A]">{KIND_LABELS.mandato_all_incasso}</h2>
              <p className="text-sm text-[#0A0A0A]/60 mt-1">
                {currentMandato ? (
                  <>Versione <strong>#{currentMandato.version}</strong> attiva dal {new Date(currentMandato.effective_date).toLocaleDateString("it-IT")}</>
                ) : "Nessuna versione ancora pubblicata"}
              </p>
              {currentMandato && (
                <p className="text-[10px] text-[#0A0A0A]/40 mt-2 font-mono break-all">
                  hash: {currentMandato.content_hash}
                </p>
              )}
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {currentMandato && (
              <button
                onClick={() => openAudit(currentMandato)}
                data-testid="view-acceptances-btn"
                className="px-3 py-2 text-xs text-[#0A0A0A]/70 hover:bg-[#0A0A0A]/5 rounded-lg inline-flex items-center gap-1.5"
              >
                <ShieldCheck className="w-4 h-4" /> Accettazioni
              </button>
            )}
            <button
              onClick={startEditFromCurrent}
              data-testid="new-version-btn"
              className="px-4 py-2 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm inline-flex items-center gap-2 hover:opacity-90"
            >
              <Plus className="w-4 h-4" /> Nuova versione
            </button>
          </div>
        </div>
        {currentMandato && (
          <div className="p-6">
            <div
              className="prose prose-sm max-w-none text-[#0A0A0A]/85"
              dangerouslySetInnerHTML={{ __html: currentMandato.content_html }}
            />
          </div>
        )}
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm">
          <div className="p-5 border-b border-[#0A0A0A]/10 flex items-center gap-2">
            <History className="w-4 h-4 text-[#0A0A0A]/60" />
            <h3 className="font-semibold text-[#0A0A0A]">Versioni precedenti ({history.length})</h3>
          </div>
          <ul className="divide-y divide-[#0A0A0A]/10">
            {history.map(h => (
              <li key={h.id} className="p-4 flex items-center justify-between hover:bg-[#0A0A0A]/[0.02]">
                <div>
                  <div className="text-sm text-[#0A0A0A]">Versione <strong>#{h.version}</strong></div>
                  <div className="text-xs text-[#0A0A0A]/55">
                    Pubblicata il {new Date(h.created_at).toLocaleString("it-IT")}
                  </div>
                </div>
                <button
                  onClick={() => openAudit(h)}
                  className="text-xs text-[#F58A1F] hover:underline"
                >
                  Accettazioni
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Editor modal */}
      {editing && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" data-testid="contract-editor-modal">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-5 border-b border-[#0A0A0A]/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#0A0A0A]">Nuova versione del contratto</h3>
                <p className="text-xs text-[#0A0A0A]/60 mt-1">
                  Alla pubblicazione, la versione corrente verrà archiviata. I terapeuti dovranno accettare la nuova versione al prossimo login.
                </p>
              </div>
              <button onClick={() => setEditing(null)} className="text-[#0A0A0A]/50 hover:text-[#0A0A0A]">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 space-y-4 overflow-y-auto flex-1">
              <div>
                <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">Titolo</label>
                <input
                  data-testid="contract-title-input"
                  type="text" value={editing.title}
                  onChange={e => setEditing({ ...editing, title: e.target.value })}
                  className="w-full px-4 py-2.5 border border-[#0A0A0A]/15 rounded-xl"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">
                  Contenuto (HTML consentito: h2/h3/p/strong/em/ul/li/a)
                </label>
                <textarea
                  data-testid="contract-content-input"
                  value={editing.content_html}
                  onChange={e => setEditing({ ...editing, content_html: e.target.value })}
                  rows={22}
                  className="w-full px-4 py-3 border border-[#0A0A0A]/15 rounded-xl font-mono text-sm leading-relaxed"
                />
              </div>
              <details className="text-sm">
                <summary className="cursor-pointer text-[#F58A1F] font-medium">Anteprima</summary>
                <div className="mt-3 p-4 bg-[#0A0A0A]/[0.03] rounded-xl prose prose-sm max-w-none"
                     dangerouslySetInnerHTML={{ __html: editing.content_html }} />
              </details>
            </div>
            <div className="p-4 border-t border-[#0A0A0A]/10 flex justify-end gap-2">
              <button onClick={() => setEditing(null)} className="px-4 py-2 text-[#0A0A0A]/65 hover:bg-[#0A0A0A]/5 rounded-full text-sm">Annulla</button>
              <button
                onClick={publishNewVersion}
                disabled={saving || !editing.content_html.trim()}
                data-testid="publish-contract-btn"
                className="px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm disabled:opacity-40 inline-flex items-center gap-2"
              >
                <Check className="w-4 h-4" />
                {saving ? "Pubblicazione..." : "Pubblica nuova versione"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Acceptances audit modal */}
      {selectedForAudit && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" data-testid="audit-modal">
          <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-5 border-b border-[#0A0A0A]/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#0A0A0A]">Accettazioni · Versione #{selectedForAudit.version}</h3>
                <p className="text-xs text-[#0A0A0A]/60 mt-1">Traccia legale immutabile</p>
              </div>
              <button onClick={() => setSelectedForAudit(null)} className="text-[#0A0A0A]/50 hover:text-[#0A0A0A]">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              {audit.loading && <div className="text-sm text-[#0A0A0A]/60">Caricamento...</div>}
              {!audit.loading && audit.items.length === 0 && (
                <div className="text-sm text-[#0A0A0A]/60 p-6 text-center">Nessuna accettazione registrata per questa versione.</div>
              )}
              {!audit.loading && audit.items.length > 0 && (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-[#0A0A0A]/55">
                      <th className="p-2">User ID</th>
                      <th className="p-2">Ruolo</th>
                      <th className="p-2">IP anonimizzato</th>
                      <th className="p-2">Data</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.items.map(a => (
                      <tr key={a.id} className="border-t border-[#0A0A0A]/10">
                        <td className="p-2 font-mono text-xs">{a.user_id}</td>
                        <td className="p-2">{a.user_role}</td>
                        <td className="p-2 font-mono text-xs">{a.ip_anonymized || "—"}</td>
                        <td className="p-2 text-xs">{new Date(a.accepted_at).toLocaleString("it-IT")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
