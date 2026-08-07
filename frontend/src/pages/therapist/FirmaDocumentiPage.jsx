import { sanitizeHtml } from "@/utils/safeHtml";
import { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { Check, FileText, ChevronRight, ScrollText, Loader2, ShieldCheck, Download } from "lucide-react";

/**
 * Signature flow — terapisti must read all pending legal documents
 * (scroll to 95%) and then type their full name to sign them all in one action.
 * Receipt PDF is generated server-side and archived in Object Storage.
 */
export default function FirmaDocumentiPage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();

  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [readMap, setReadMap] = useState({});  // { contract_id: true }
  const [signatureName, setSignatureName] = useState("");
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState(null);
  const [successReceipt, setSuccessReceipt] = useState(null);
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/contracts/pending/mine`, { withCredentials: true });
      setPending(r.data?.pending || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user && user.role === "terapeuta") load();
    else if (user && user.role !== "terapeuta") navigate("/", { replace: true });
  }, [user, load, navigate]);

  // Detect scroll to 95% of the current doc
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const pct = (el.scrollTop + el.clientHeight) / el.scrollHeight;
      if (pct >= 0.95 && pending[currentIdx]) {
        setReadMap(prev => ({ ...prev, [pending[currentIdx].contract_id]: true }));
      }
    };
    el.addEventListener("scroll", onScroll);
    onScroll();
    return () => el.removeEventListener("scroll", onScroll);
  }, [currentIdx, pending]);

  const [docHtml, setDocHtml] = useState("");
  const [docLoading, setDocLoading] = useState(false);
  useEffect(() => {
    if (!pending[currentIdx]) return;
    setDocLoading(true);
    setDocHtml("");
    axios.get(`${API}/contracts/current/${pending[currentIdx].kind}`)
      .then(r => setDocHtml(r.data?.content_html || ""))
      .catch(() => setDocHtml("<p>Errore caricamento documento.</p>"))
      .finally(() => setDocLoading(false));
  }, [currentIdx, pending]);

  const allRead = pending.length > 0 && pending.every(p => readMap[p.contract_id]);
  const expectedName = `${user?.nome || ""} ${user?.cognome || ""}`.trim();
  const nameMatches = signatureName.trim().toLowerCase() === expectedName.toLowerCase();
  const canSign = allRead && nameMatches && !signing;

  const submit = async () => {
    setError(null);
    setSigning(true);
    try {
      const r = await axios.post(`${API}/contracts/sign`, {
        contract_ids: pending.map(p => p.contract_id),
        signature_name: signatureName.trim(),
        scrolled_all: true,
      }, { withCredentials: true });
      setSuccessReceipt(r.data);
      if (refresh) await refresh();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSigning(false);
    }
  };

  if (loading) return <div className="min-h-screen bg-[#F5D419]/10 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-[#F58A1F]" /></div>;

  if (successReceipt) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#F5D419]/20 via-[#F58A1F]/10 to-white flex items-center justify-center p-6">
        <div className="bg-white rounded-3xl border border-[#0A0A0A]/10 shadow-xl max-w-lg w-full p-8 text-center" data-testid="firma-success">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
            <ShieldCheck className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2">Documenti firmati!</h1>
          <p className="text-[#0A0A0A]/70 mb-6">
            La ricevuta di sottoscrizione ti è stata inviata via email. Puoi anche scaricarla ora.
          </p>
          <div className="bg-[#F5D419]/10 rounded-xl p-4 text-left text-sm space-y-1 mb-6">
            <div><strong>Receipt ID:</strong> <span className="font-mono text-xs">{successReceipt.receipt_id?.slice(0, 16)}…</span></div>
            <div><strong>Documenti:</strong> {successReceipt.documents_signed?.length || 0}</div>
            <div><strong>Firmato il:</strong> {new Date(successReceipt.signed_at).toLocaleString("it-IT")}</div>
          </div>
          <div className="flex gap-3 justify-center">
            <a
              href={`${API}/contracts/receipt/${successReceipt.receipt_id}`}
              download
              className="px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm inline-flex items-center gap-2"
              data-testid="download-receipt-btn"
            >
              <Download className="w-4 h-4" /> Scarica ricevuta
            </a>
            <button
              onClick={() => navigate("/terapeuta")}
              className="px-5 py-2.5 border border-[#0A0A0A]/15 text-[#0A0A0A] rounded-full text-sm hover:bg-[#0A0A0A]/5"
              data-testid="go-to-dashboard-btn"
            >
              Vai alla dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (pending.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#F5D419]/20 via-[#F58A1F]/10 to-white flex items-center justify-center p-6">
        <div className="bg-white rounded-3xl border border-[#0A0A0A]/10 shadow-xl max-w-md w-full p-8 text-center" data-testid="firma-none-pending">
          <ShieldCheck className="w-16 h-16 text-green-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2">Tutto in ordine!</h1>
          <p className="text-[#0A0A0A]/70 mb-6">Non hai documenti in attesa di firma.</p>
          <button
            onClick={() => navigate("/terapeuta")}
            className="px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm"
            data-testid="go-to-dashboard-btn"
          >
            Vai alla dashboard
          </button>
        </div>
      </div>
    );
  }

  const current = pending[currentIdx];
  const currentRead = current && !!readMap[current.contract_id];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F5D419]/20 via-[#F58A1F]/10 to-white p-4 sm:p-6" data-testid="firma-documenti-page">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-[#0A0A0A] flex items-center gap-2">
            <ScrollText className="w-7 h-7 text-[#F58A1F]" />
            Firma dei documenti legali
          </h1>
          <p className="text-[#0A0A0A]/70 text-sm mt-1">
            Prima di iniziare a operare sulla piattaforma devi leggere e firmare i seguenti documenti.
            Scorri fino in fondo ogni documento per abilitare la firma.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          {/* Sidebar: doc list */}
          <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm p-4 h-fit" data-testid="firma-sidebar">
            <div className="text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-3">Documenti ({pending.length})</div>
            <ul className="space-y-1">
              {pending.map((p, idx) => (
                <li key={p.contract_id}>
                  <button
                    onClick={() => setCurrentIdx(idx)}
                    data-testid={`firma-doc-tab-${p.kind}`}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-start gap-2 transition-colors ${
                      idx === currentIdx ? "bg-[#F58A1F]/10 border border-[#F58A1F]/30" : "hover:bg-[#0A0A0A]/[0.03]"
                    }`}
                  >
                    {readMap[p.contract_id]
                      ? <Check className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
                      : <FileText className="w-4 h-4 text-[#0A0A0A]/40 flex-shrink-0 mt-0.5" />
                    }
                    <span className={`flex-1 ${readMap[p.contract_id] ? "text-[#0A0A0A]/60" : "text-[#0A0A0A]"}`}>{p.title}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="mt-4 pt-3 border-t border-[#0A0A0A]/10 text-xs text-[#0A0A0A]/60">
              {allRead ? "Tutti letti ✓" : `${Object.keys(readMap).length}/${pending.length} letti`}
            </div>
          </div>

          {/* Main: doc content + signature form */}
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-[#0A0A0A]/10 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-[#0A0A0A]/10 flex items-center justify-between">
                <div>
                  <div className="text-xs text-[#0A0A0A]/55">Documento {currentIdx + 1} di {pending.length}</div>
                  <div className="font-semibold text-[#0A0A0A]">{current?.title}</div>
                </div>
                <div className="text-xs text-[#0A0A0A]/50 font-mono hidden sm:block">
                  v{current?.version}
                </div>
              </div>
              <div
                ref={scrollRef}
                data-testid="firma-doc-scroll"
                className="max-h-[500px] overflow-y-auto p-6 prose prose-sm max-w-none text-[#0A0A0A]/85"
              >
                {docLoading
                  ? <div className="py-16 text-center text-[#0A0A0A]/55">Caricamento…</div>
                  : <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(docHtml) }} />
                }
              </div>
              <div className={`p-3 border-t text-sm flex items-center justify-between ${currentRead ? "bg-green-50 border-green-200" : "bg-[#F5D419]/10 border-[#F58A1F]/20"}`}>
                <div className={currentRead ? "text-green-800" : "text-[#0A0A0A]/70"}>
                  {currentRead ? "✓ Documento letto" : "Scorri fino in fondo per confermare la lettura"}
                </div>
                {currentIdx < pending.length - 1 && (
                  <button
                    onClick={() => setCurrentIdx(currentIdx + 1)}
                    className="text-[#F58A1F] text-sm font-medium hover:underline inline-flex items-center gap-1"
                    data-testid="firma-next-doc"
                  >
                    Prossimo documento <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Signature form (bottom) */}
            <div className={`bg-white rounded-2xl border shadow-sm p-6 transition-opacity ${allRead ? "border-[#F58A1F]/40" : "border-[#0A0A0A]/10 opacity-70"}`} data-testid="firma-signature-form">
              <div className="mb-4">
                <div className="text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">Passo finale</div>
                <div className="font-semibold text-[#0A0A0A]">Firma i documenti</div>
                <div className="text-sm text-[#0A0A0A]/65 mt-1">
                  {allRead
                    ? "Digita il tuo nome e cognome esattamente come da anagrafica per completare la sottoscrizione."
                    : "Completa la lettura di tutti i documenti per abilitare la firma."
                  }
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-1">
                    Nome e cognome (deve corrispondere a: <strong>{expectedName}</strong>)
                  </label>
                  <input
                    type="text"
                    value={signatureName}
                    onChange={e => setSignatureName(e.target.value)}
                    disabled={!allRead}
                    placeholder={expectedName}
                    data-testid="firma-signature-name-input"
                    className="w-full px-4 py-3 border border-[#0A0A0A]/15 rounded-xl text-base disabled:bg-[#0A0A0A]/5 disabled:cursor-not-allowed"
                  />
                  {signatureName && !nameMatches && (
                    <p className="text-xs text-red-600 mt-1">Il nome digitato deve corrispondere esattamente a &quot;{expectedName}&quot;.</p>
                  )}
                </div>
                <div className="text-xs text-[#0A0A0A]/50 leading-relaxed">
                  Firmando dichiari di aver letto e accettato integralmente i documenti sopra elencati.
                  La firma elettronica è valida ai sensi dell&apos;art. 20 D.Lgs. 82/2005 (CAD) e del Reg. UE 910/2014 (eIDAS).
                  Riceverai la ricevuta di sottoscrizione via email.
                </div>
                {error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-800" data-testid="firma-error">
                    {error}
                  </div>
                )}
                <button
                  onClick={submit}
                  disabled={!canSign}
                  data-testid="firma-submit-btn"
                  className="w-full px-6 py-3.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-bold rounded-full text-sm inline-flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
                >
                  {signing
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Firma in corso…</>
                    : <><ShieldCheck className="w-4 h-4" /> Firma e conferma</>
                  }
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
