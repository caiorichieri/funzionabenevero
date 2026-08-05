import { useState, useEffect } from "react";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { Download, ShieldCheck, Trash2, FileText, Info, Loader2 } from "lucide-react";

/**
 * "I miei consensi" — GDPR user rights area.
 * Available to any authenticated user (paziente or terapeuta).
 * - Portabilità art. 20 (download JSON)
 * - Oblio art. 17 (delete account)
 * - Consent management (toggle marketing / miglioramento / ricerca)
 * - History of consents
 * - Firme dei contratti + download ricevute
 */
export default function PrivacyUtentePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [consents, setConsents] = useState({ consents: {}, history: [] });
  const [signatures, setSignatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyConsent, setBusyConsent] = useState(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteText, setDeleteText] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [c, s] = await Promise.all([
        axios.get(`${API}/user/consents/mine`, { withCredentials: true }),
        axios.get(`${API}/contracts/signatures/mine`, { withCredentials: true }),
      ]);
      setConsents(c.data || { consents: {}, history: [] });
      setSignatures(s.data?.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (user) load(); }, [user]);

  const toggleConsent = async (type, granted) => {
    setBusyConsent(type);
    try {
      await axios.post(`${API}/user/consents/update`, { consent_type: type, granted }, { withCredentials: true });
      await load();
    } finally {
      setBusyConsent(null);
    }
  };

  const downloadExport = async () => {
    const r = await axios.get(`${API}/user/gdpr/export`, { withCredentials: true });
    const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `funzionabene_miei_dati_${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const submitDelete = async () => {
    if (deleteText.trim().toUpperCase() !== "CANCELLA") return;
    setDeleting(true);
    try {
      await axios.post(`${API}/user/gdpr/delete-account`, {
        confirm_text: "CANCELLA",
        motivazione: deleteReason.trim() || null,
      }, { withCredentials: true });
      await logout();
      navigate("/", { replace: true });
    } catch (e) {
      alert("Errore: " + (e.response?.data?.detail || e.message));
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <div className="p-6 flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-[#F58A1F]" /></div>;

  const CONSENT_TYPES = [
    { key: "marketing", label: "Comunicazioni promozionali", desc: "Email/SMS su nuovi servizi, iniziative e offerte di Funzionabene." },
    { key: "miglioramento", label: "Miglioramento del servizio", desc: "Uso dei tuoi dati (anonimizzati) per analisi statistiche e miglioramento della piattaforma." },
    { key: "ricerca", label: "Ricerca scientifica", desc: "Uso dei tuoi dati anonimizzati per ricerche in ambito psicologico e clinico." },
  ];

  return (
    <div className="space-y-6" data-testid="privacy-utente-page">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#0A0A0A] font-[Outfit]">I miei dati e consensi</h1>
        <p className="text-[#0A0A0A]/65 mt-1 text-sm">
          Gestisci i tuoi consensi, scarica i tuoi dati (portabilità art. 20 GDPR) o cancella il tuo account (oblio art. 17 GDPR).
        </p>
      </div>

      {/* Firme (solo terapeuti) */}
      {user?.role === "terapeuta" && (
        <section className="bg-white rounded-2xl border border-[#0A0A0A]/10 p-5 sm:p-6 shadow-sm" data-testid="privacy-signatures-section">
          <h2 className="text-lg font-semibold text-[#0A0A0A] mb-3 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#F58A1F]" /> Documenti firmati
          </h2>
          {signatures.length === 0 ? (
            <div className="text-sm text-[#0A0A0A]/60 py-2" data-testid="privacy-signatures-empty">
              Non hai ancora firmato alcun documento.{" "}
              <button
                onClick={() => navigate("/terapeuta/firma-documenti")}
                className="text-[#F58A1F] underline font-medium"
                data-testid="go-to-firma-btn"
              >
                Vai al modulo di firma
              </button>.
            </div>
          ) : (
            <ul className="divide-y divide-[#0A0A0A]/10">
              {signatures.map(s => (
                <li key={s.receipt_id} className="py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-[#0A0A0A]">
                      {s.documents.map(d => d.kind).join(", ")}
                    </div>
                    <div className="text-xs text-[#0A0A0A]/55">
                      Firmato il {new Date(s.signed_at).toLocaleString("it-IT")}
                      {s.signature_name && <> · da {s.signature_name}</>}
                    </div>
                  </div>
                  {(s.storage_path || s.receipt_id) && (
                    <a
                      href={`${API}/contracts/receipt/${s.receipt_id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-[#0A0A0A]/15 rounded-full text-xs hover:bg-[#0A0A0A]/5"
                      data-testid={`download-receipt-${s.receipt_id}`}
                    >
                      <Download className="w-3.5 h-3.5" /> Ricevuta PDF
                    </a>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* Consensi */}
      <section className="bg-white rounded-2xl border border-[#0A0A0A]/10 p-5 sm:p-6 shadow-sm" data-testid="privacy-consents-section">
        <h2 className="text-lg font-semibold text-[#0A0A0A] mb-3">Consensi attivi</h2>
        <p className="text-sm text-[#0A0A0A]/65 mb-4">
          Puoi attivare o revocare in qualsiasi momento i consensi facoltativi. La revoca ha effetto immediato e non pregiudica la fruizione del servizio principale.
        </p>
        <div className="divide-y divide-[#0A0A0A]/10">
          {CONSENT_TYPES.map(c => {
            const granted = !!consents.consents?.[c.key];
            return (
              <div key={c.key} className="py-4 flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="text-sm font-medium text-[#0A0A0A]">{c.label}</div>
                  <div className="text-xs text-[#0A0A0A]/60 mt-0.5">{c.desc}</div>
                </div>
                <button
                  onClick={() => toggleConsent(c.key, !granted)}
                  disabled={busyConsent === c.key}
                  data-testid={`consent-toggle-${c.key}`}
                  className={`relative inline-flex w-11 h-6 rounded-full flex-shrink-0 transition-colors ${granted ? "bg-green-500" : "bg-[#0A0A0A]/15"} disabled:opacity-50`}
                >
                  <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${granted ? "translate-x-5" : ""}`} />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Storico consensi */}
      {consents.history?.length > 0 && (
        <section className="bg-white rounded-2xl border border-[#0A0A0A]/10 p-5 sm:p-6 shadow-sm" data-testid="privacy-history-section">
          <h2 className="text-lg font-semibold text-[#0A0A0A] mb-3 flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#0A0A0A]/60" /> Storico consensi
          </h2>
          <ul className="divide-y divide-[#0A0A0A]/10 max-h-80 overflow-y-auto">
            {consents.history.map((h, idx) => (
              <li key={idx} className="py-2 text-xs text-[#0A0A0A]/70 flex items-center justify-between gap-2">
                <span>
                  <span className={h.action === "grant" ? "text-green-700" : "text-red-700"}>
                    {h.action === "grant" ? "Concesso" : "Revocato"}
                  </span>
                  {" "}consenso <strong>{h.consent_type}</strong>
                </span>
                <span className="text-[#0A0A0A]/45 font-mono text-[10px]">
                  {new Date(h.timestamp).toLocaleString("it-IT")}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Portabilità */}
      <section className="bg-white rounded-2xl border border-[#0A0A0A]/10 p-5 sm:p-6 shadow-sm" data-testid="privacy-export-section">
        <h2 className="text-lg font-semibold text-[#0A0A0A] mb-1 flex items-center gap-2">
          <Download className="w-5 h-5 text-[#F58A1F]" /> Scarica i miei dati
        </h2>
        <p className="text-sm text-[#0A0A0A]/65 mb-4">
          Esporta in un file JSON tutti i dati personali che BIDOC SRL detiene su di te (portabilità ex art. 20 GDPR).
        </p>
        <button
          onClick={downloadExport}
          className="px-5 py-2.5 bg-[#0A0A0A] text-white rounded-full text-sm font-medium hover:bg-[#0A0A0A]/85 inline-flex items-center gap-2"
          data-testid="gdpr-export-btn"
        >
          <Download className="w-4 h-4" /> Scarica in formato JSON
        </button>
      </section>

      {/* Cancellazione */}
      <section className="bg-white rounded-2xl border border-red-200 p-5 sm:p-6 shadow-sm" data-testid="privacy-delete-section">
        <h2 className="text-lg font-semibold text-red-800 mb-1 flex items-center gap-2">
          <Trash2 className="w-5 h-5" /> Cancella il mio account
        </h2>
        <p className="text-sm text-[#0A0A0A]/70 mb-4">
          Puoi richiedere in qualsiasi momento la cancellazione del tuo account (diritto all&apos;oblio ex art. 17 GDPR).
          I dati saranno cancellati entro 15 giorni, fatti salvi gli obblighi di conservazione previsti dalla legge
          (dati fiscali per 10 anni, dati clinici del terapeuta per 5 anni ex Codice Deontologico Psicologi).
        </p>
        {!deleteOpen && (
          <button
            onClick={() => setDeleteOpen(true)}
            className="px-5 py-2.5 border border-red-300 text-red-700 rounded-full text-sm font-medium hover:bg-red-50"
            data-testid="gdpr-delete-open-btn"
          >
            Richiedi cancellazione
          </button>
        )}
        {deleteOpen && (
          <div className="border-t border-red-200 pt-4 mt-2 space-y-3" data-testid="gdpr-delete-form">
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800 flex gap-2">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>Azione irreversibile. Il tuo account sarà disattivato immediatamente e cancellato entro 15 giorni.</span>
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">Motivazione (facoltativa)</label>
              <textarea
                value={deleteReason}
                onChange={e => setDeleteReason(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-[#0A0A0A]/15 rounded-xl text-sm"
                placeholder="Es. Non uso più il servizio…"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">
                Digita &quot;CANCELLA&quot; per confermare
              </label>
              <input
                type="text"
                value={deleteText}
                onChange={e => setDeleteText(e.target.value)}
                placeholder="CANCELLA"
                data-testid="gdpr-delete-confirm-input"
                className="w-full px-4 py-2.5 border border-red-300 rounded-xl text-sm font-mono"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setDeleteOpen(false); setDeleteText(""); setDeleteReason(""); }}
                className="px-4 py-2 border border-[#0A0A0A]/15 text-[#0A0A0A] rounded-full text-sm hover:bg-[#0A0A0A]/5"
              >
                Annulla
              </button>
              <button
                onClick={submitDelete}
                disabled={deleteText.trim().toUpperCase() !== "CANCELLA" || deleting}
                data-testid="gdpr-delete-submit-btn"
                className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-full text-sm font-medium disabled:opacity-40 inline-flex items-center gap-2"
              >
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Conferma cancellazione
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
