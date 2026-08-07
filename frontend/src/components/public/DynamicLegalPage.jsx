import { sanitizeHtml } from "@/utils/safeHtml";
import { useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import LegalLayout from "@/components/public/LegalLayout";

/**
 * Renders a legal document fetched from the backend by "kind".
 * The admin panel edits the same document, so any change goes live instantly.
 *
 * Props:
 *  - kind: string (e.g. "privacy_pazienti")
 *  - fallbackTitle: string shown while loading or if fetch fails
 *  - testId: string data-testid for the outer layout
 */
export default function DynamicLegalPage({ kind, fallbackTitle, testId }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    axios.get(`${API}/contracts/current/${kind}`)
      .then(r => { if (!cancelled) setDoc(r.data); })
      .catch(e => { if (!cancelled) setError(e); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [kind]);

  const lastUpdate = doc?.effective_date
    ? new Date(doc.effective_date).toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <LegalLayout
      title={doc?.title || fallbackTitle}
      lastUpdate={lastUpdate}
      testId={testId}
    >
      {loading && (
        <div className="py-16 text-center text-[#0A0A0A]/55" data-testid={`${testId}-loading`}>
          Caricamento del documento…
        </div>
      )}

      {!loading && error && (
        <div className="p-6 bg-red-50 border border-red-200 rounded-2xl text-red-800 text-sm" data-testid={`${testId}-error`}>
          Il documento non è momentaneamente disponibile. Riprova più tardi o scrivici a{" "}
          <a href="mailto:privacy@bidoc.it">privacy@bidoc.it</a>.
        </div>
      )}

      {!loading && doc && (
        <>
          <div className="text-[10px] text-[#0A0A0A]/45 mb-6 flex flex-wrap gap-x-4 gap-y-1" data-testid={`${testId}-meta`}>
            <span>Versione: <strong>#{doc.version}</strong></span>
            {doc.content_hash && (
              <span>Hash SHA-256: <span className="font-mono">{doc.content_hash.slice(0, 32)}…</span></span>
            )}
          </div>
          <div
            className="text-[#0A0A0A]/85"
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(doc.content_html) }}
            data-testid={`${testId}-content`}
          />
        </>
      )}
    </LegalLayout>
  );
}
