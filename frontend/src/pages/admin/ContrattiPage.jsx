import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ScrollText, Plus, Check, History, ShieldCheck, X } from "lucide-react";

const KIND_LABELS = {
  mandato_all_incasso: "Mandato all'incasso (v1 legacy)",
  contratto_collaborazione: "Contratto di Collaborazione Professionale",
  privacy_visitatori: "Privacy · Visitatori del Sito",
  privacy_pazienti: "Privacy · Pazienti Registrati",
  privacy_terapeuti: "Privacy · Terapeuti (+ DPA art. 28 GDPR)",
  cookie_policy: "Cookie Policy",
  termini_pazienti: "Termini e Condizioni · Pazienti",
};

const KIND_ORDER = [
  "contratto_collaborazione",
  "privacy_pazienti",
  "privacy_terapeuti",
  "privacy_visitatori",
  "termini_pazienti",
  "cookie_policy",
  "mandato_all_incasso",
];

const DEFAULT_NEW = { kind: "contratto_collaborazione", title: "", content_html: "" };

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

  const currentByKind = Object.fromEntries(
    KIND_ORDER.map(k => [k, contracts.find(c => c.kind === k && c.is_current)])
  );
  const historyByKind = Object.fromEntries(
    KIND_ORDER.map(k => [k, contracts.filter(c => c.kind === k && !c.is_current)])
  );

  const startEditFromKind = (kind) => {
    const current = currentByKind[kind];
    if (!current) {
      setEditing({ kind, title: KIND_LABELS[kind] || kind, content_html: "" });
      return;
    }
    setEditing({
      kind: current.kind,
      title: current.title,
      content_html: current.content_html,
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
        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Documenti Legali</h1>
        <p className="text-[#0A0A0A]/65 mt-1">
          Contratti, informative privacy e cookie policy che regolano la piattaforma. Ogni modifica crea una nuova versione immutabile, tracciata con hash e data di pubblicazione.
        </p>
      </div>

      {/* Cards per ogni documento legale */}
      <div className="space-y-6">
        {KIND_ORDER.map(kind => {
          const current = currentByKind[kind];
          const history = historyByKind[kind];
          return (
            <div key={kind} className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm overflow-hidden" data-testid={`legal-doc-card-${kind}`}>
              <div className="p-6 border-b border-[#0A0A0A]/10 flex items-start justify-between gap-4">
                <div className="flex items-start gap-4 min-w-0">
                  <div className="w-12 h-12 rounded-xl bg-[#F58A1F]/15 flex items-center justify-center flex-shrink-0">
                    <ScrollText className="w-6 h-6 text-[#F58A1F]" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-lg sm:text-xl font-semibold text-[#0A0A0A]">{KIND_LABELS[kind]}</h2>
                    <p className="text-sm text-[#0A0A0A]/60 mt-1">
                      {current ? (
                        <>Versione <strong>#{current.version}</strong> attiva dal {new Date(current.effective_date).toLocaleDateString("it-IT")}
                          {history.length > 0 && <span className="ml-2 text-[#0A0A0A]/45">· {history.length} versioni precedenti</span>}
                        </>
                      ) : "Nessuna versione ancora pubblicata"}
                    </p>
                    {current && (
                      <p className="text-[10px] text-[#0A0A0A]/40 mt-2 font-mono break-all">
                        hash: {current.content_hash}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {current && (
                    <>
                      <button
                        onClick={() => openAudit(current)}
                        data-testid={`view-acceptances-btn-${kind}`}
                        className="px-3 py-2 text-xs text-[#0A0A0A]/70 hover:bg-[#0A0A0A]/5 rounded-lg inline-flex items-center gap-1.5"
                      >
                        <ShieldCheck className="w-4 h-4" /> Accettazioni
                      </button>
                      {current.version > 1 && (
                        <button
                          onClick={async () => {
                            if (!confirm(`Inviare email di aggiornamento MAJOR a tutti gli utenti che hanno accettato una versione precedente di "${KIND_LABELS[kind]}"?`)) return;
                            try {
                              const r = await axios.post(`${API}/admin/contracts/${current.id}/notify-major`, { include_terapeuti: true, include_pazienti: false }, { withCredentials: true });
                              alert(`Notifica inviata a ${r.data?.notified_count || 0} utenti.`);
                            } catch (e) {
                              alert("Errore: " + (e.response?.data?.detail || e.message));
                            }
                          }}
                          data-testid={`notify-major-btn-${kind}`}
                          className="px-3 py-2 text-xs text-orange-700 hover:bg-orange-50 rounded-lg inline-flex items-center gap-1.5 border border-orange-200"
                        >
                          📢 Notifica MAJOR
                        </button>
                      )}
                    </>
                  )}
                  <button
                    onClick={() => startEditFromKind(kind)}
                    data-testid={`new-version-btn-${kind}`}
                    className="px-4 py-2 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm inline-flex items-center gap-2 hover:opacity-90"
                  >
                    <Plus className="w-4 h-4" /> Nuova versione
                  </button>
                </div>
              </div>
              {current && (
                <details className="p-0">
                  <summary className="p-4 cursor-pointer text-sm text-[#F58A1F] hover:bg-[#0A0A0A]/[0.02] font-medium">
                    Mostra contenuto attuale
                  </summary>
                  <div className="p-6 pt-2 border-t border-[#0A0A0A]/10">
                    <div
                      className="prose prose-sm max-w-none text-[#0A0A0A]/85"
                      dangerouslySetInnerHTML={{ __html: current.content_html }}
                    />
                  </div>
                </details>
              )}
              {history.length > 0 && (
                <details className="border-t border-[#0A0A0A]/10">
                  <summary className="p-4 cursor-pointer text-sm text-[#0A0A0A]/65 hover:bg-[#0A0A0A]/[0.02] font-medium inline-flex items-center gap-2">
                    <History className="w-4 h-4" /> Versioni precedenti ({history.length})
                  </summary>
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
                </details>
              )}
            </div>
          );
        })}
      </div>

      {/* Editor modal */}
      {editing && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" data-testid="contract-editor-modal">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-5 border-b border-[#0A0A0A]/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[#0A0A0A]">
                  Nuova versione · {KIND_LABELS[editing.kind] || editing.kind}
                </h3>
                <p className="text-xs text-[#0A0A0A]/60 mt-1">
                  Alla pubblicazione, la versione corrente verrà archiviata. Gli utenti dovranno accettare la nuova versione al prossimo login.
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
