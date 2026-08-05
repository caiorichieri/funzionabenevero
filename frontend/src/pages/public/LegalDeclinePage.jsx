import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { AlertTriangle, Loader2, CheckCircle } from "lucide-react";

/**
 * Public landing when a therapist clicks "NON ACCETTO" in an update email.
 * The token is single-use and expires in 60 days.
 * On success we show a confirmation that the profile will be deactivated in 48h.
 */
export default function LegalDeclinePage() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/legal/decline/${token}`)
      .then(r => setResult(r.data))
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-[#F5D419]/20 to-white flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-[#F58A1F]" />
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F5D419]/20 via-[#F58A1F]/10 to-white flex items-center justify-center p-6" data-testid="legal-decline-page">
      <div className="bg-white rounded-3xl border border-[#0A0A0A]/10 shadow-xl max-w-lg w-full p-8">
        {error ? (
          <>
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-red-600" />
            </div>
            <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2 text-center">Link non valido</h1>
            <p className="text-[#0A0A0A]/70 text-sm text-center mb-6" data-testid="legal-decline-error">{error}</p>
            <button
              onClick={() => navigate("/")}
              className="w-full px-5 py-2.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-medium rounded-full text-sm"
            >
              Torna alla home
            </button>
          </>
        ) : (
          <>
            <div className="w-16 h-16 rounded-full bg-orange-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-orange-600" />
            </div>
            <h1 className="text-2xl font-bold text-[#0A0A0A] mb-2 text-center" data-testid="legal-decline-success">
              Richiesta registrata
            </h1>
            <p className="text-[#0A0A0A]/75 text-sm text-center mb-4">
              Ciao <strong>{result?.user_nome}</strong>, abbiamo registrato la tua volontà di non accettare la nuova versione del documento.
            </p>
            <div className="bg-[#F5D419]/10 rounded-xl p-4 space-y-2 text-sm">
              <div><strong>Documento:</strong> {result?.contract_kind}</div>
              <div><strong>Versione:</strong> {result?.contract_version}</div>
              <div><strong>Disattivazione prevista:</strong> {new Date(result?.deactivate_at).toLocaleString("it-IT")}</div>
            </div>
            <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-xl text-xs text-orange-900">
              Il tuo profilo verrà disattivato definitivamente entro 48 ore. Gli appuntamenti già confermati saranno onorati;
              le prenotazioni future saranno cancellate con rimborso ai pazienti. Riceverai una email di conferma.
              Se hai cambiato idea, contatta <a href="mailto:privacy@bidoc.it" className="underline">privacy@bidoc.it</a> entro il periodo di grazia.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
