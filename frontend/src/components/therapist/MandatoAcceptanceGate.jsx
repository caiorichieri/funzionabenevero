import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ScrollText, Check } from "lucide-react";

/**
 * Blocks the therapist dashboard until they accept the current version of the
 * "Mandato all'incasso con Rappresentanza" contract. Once accepted, the
 * acceptance is recorded on the server (write-once) and this modal disappears
 * for future sessions of the same version.
 */
export default function MandatoAcceptanceGate({ children }) {
  const [ready, setReady] = useState(false);
  const [contract, setContract] = useState(null);
  const [needsAcceptance, setNeedsAcceptance] = useState(false);
  const [scrolledToEnd, setScrolledToEnd] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const bodyRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ data: current }, { data: accepts }] = await Promise.all([
          axios.get(`${API}/contracts/current/mandato_all_incasso`),
          axios.get(`${API}/contracts/my-acceptances`, { withCredentials: true }),
        ]);
        if (cancelled) return;
        setContract(current);
        const items = accepts?.items || [];
        const alreadyAccepted = items.some(
          a => a.contract_kind === "mandato_all_incasso" && a.content_hash === current.content_hash,
        );
        setNeedsAcceptance(!alreadyAccepted);
      } catch {
        // If contract endpoint fails, don't block dashboard.
        setNeedsAcceptance(false);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const onScroll = (e) => {
    const el = e.target;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 24) {
      setScrolledToEnd(true);
    }
  };

  const handleAccept = async () => {
    if (!contract) return;
    setSubmitting(true);
    setError("");
    try {
      await axios.post(`${API}/contracts/accept`, {
        contract_id: contract.id,
        scrolled_to_end: scrolledToEnd,
      }, { withCredentials: true });
      setNeedsAcceptance(false);
    } catch (e) {
      setError(e.response?.data?.detail || "Errore durante l'accettazione");
    } finally {
      setSubmitting(false);
    }
  };

  if (!ready) return null;
  if (!needsAcceptance) return children;

  return (
    <>
      {children}
      <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="mandato-gate">
        <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
          <div className="p-6 border-b border-[#0A0A0A]/10">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-[#F58A1F]/15 flex items-center justify-center flex-shrink-0">
                <ScrollText className="w-6 h-6 text-[#F58A1F]" />
              </div>
              <div>
                <h2 className="text-xl font-serif text-[#0A0A0A]">{contract?.title || "Mandato all'incasso"}</h2>
                <p className="text-xs text-[#0A0A0A]/60 mt-1">
                  Versione #{contract?.version} · Per poter operare sulla piattaforma devi leggere e accettare il presente mandato.
                </p>
              </div>
            </div>
          </div>

          <div
            ref={bodyRef}
            onScroll={onScroll}
            className="p-6 overflow-y-auto flex-1 prose prose-sm max-w-none text-[#0A0A0A]/90"
            dangerouslySetInnerHTML={{ __html: contract?.content_html || "" }}
            data-testid="mandato-content"
          />

          {error && (
            <div className="px-6 py-2 text-sm text-red-600 border-t border-red-100 bg-red-50">
              {error}
            </div>
          )}

          <div className="p-4 border-t border-[#0A0A0A]/10 flex flex-col sm:flex-row items-center gap-3 justify-between bg-[#0A0A0A]/[0.02]">
            <p className="text-xs text-[#0A0A0A]/55">
              {scrolledToEnd
                ? "✓ Hai letto l'intero documento"
                : "Scorri fino in fondo per abilitare l'accettazione"}
            </p>
            <button
              data-testid="mandato-accept-btn"
              onClick={handleAccept}
              disabled={!scrolledToEnd || submitting}
              className="px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold rounded-full inline-flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Check className="w-4 h-4" />
              {submitting ? "Registrazione..." : "Accetto il mandato"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
