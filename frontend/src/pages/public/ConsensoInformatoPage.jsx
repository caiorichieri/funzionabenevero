import { useEffect, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ShieldCheck, AlertCircle, CheckCircle2 } from "lucide-react";

export default function ConsensoInformatoPage() {
  const { consentId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [accepted, setAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [checkbox, setCheckbox] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await axios.get(`${API}/consenso-informato/${consentId}`, {
          params: { token },
        });
        if (!cancelled) setData(res.data);
        if (res.data?.status === "granted") setAccepted(true);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail || "Impossibile caricare il consenso.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [consentId, token]);

  const submit = async () => {
    setSubmitting(true);
    setError("");
    try {
      await axios.post(`${API}/consenso-informato/${consentId}/accept`, { token });
      setAccepted(true);
    } catch (e) {
      setError(e?.response?.data?.detail || "Errore durante l'invio del consenso.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-[#F4F1ED] flex items-center justify-center px-6">
        <p className="text-[#0A0A0A]/60 text-sm">Caricamento…</p>
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="min-h-screen bg-[#F4F1ED] flex items-center justify-center px-6">
        <div className="max-w-md text-center" data-testid="consent-error">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h1 className="font-serif text-2xl text-[#0A0A0A] mb-2">Consenso non disponibile</h1>
          <p className="text-[#0A0A0A]/65 text-sm">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="mt-6 px-6 py-3 rounded-full bg-[#0A0A0A] text-white text-sm"
            data-testid="consent-back-home"
          >
            Torna alla home
          </button>
        </div>
      </main>
    );
  }

  if (accepted) {
    return (
      <main className="min-h-screen bg-[#F4F1ED] flex items-center justify-center px-6" data-testid="consent-granted">
        <div className="max-w-lg text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-600 mx-auto mb-6" />
          <h1 className="font-serif text-3xl lg:text-4xl text-[#0A0A0A] mb-4">
            Grazie, {data?.paziente?.nome || ""}
          </h1>
          <p className="text-[#0A0A0A]/75 leading-relaxed">
            Il tuo consenso informato è stato registrato con successo. Da questo momento puoi partecipare alle sedute con Dr./Dr.ssa {data?.terapista?.nome} {data?.terapista?.cognome}.
          </p>
          <p className="text-[#0A0A0A]/50 text-xs mt-6">
            Riceverai il link della videochiamata via email 15 minuti prima dell&apos;inizio della seduta. Puoi revocare il tuo consenso in qualsiasi momento contattando direttamente il/la professionista o dalla tua area personale.
          </p>
          <button
            onClick={() => navigate("/paziente")}
            className="mt-8 px-8 py-3 rounded-full bg-[#0A0A0A] text-white text-sm"
            data-testid="consent-goto-dashboard"
          >
            Vai alla mia area
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F4F1ED] py-12 px-6">
      <div className="max-w-3xl mx-auto" data-testid="consent-page">
        <div className="text-center mb-10">
          <ShieldCheck className="w-14 h-14 text-[#6B8FA3] mx-auto mb-4" />
          <p className="text-xs tracking-[0.3em] uppercase text-[#0A0A0A]/50 mb-3">
            Consenso Informato al Trattamento
          </p>
          <h1 className="font-serif text-3xl lg:text-4xl text-[#0A0A0A]">
            Un passo prima della prima seduta
          </h1>
          <p className="text-[#0A0A0A]/65 mt-4 max-w-xl mx-auto text-sm leading-relaxed">
            Il documento seguente è emesso direttamente da Dr./Dr.ssa <strong className="text-[#0A0A0A]">{data?.terapista?.nome} {data?.terapista?.cognome}</strong>. Bidoc SRL / FunzionaBene opera solo come intermediario tecnologico.
          </p>
        </div>

        <article
          className="bg-white/70 border border-[#0A0A0A]/10 rounded-2xl p-8 lg:p-10 whitespace-pre-line text-[15px] text-[#0A0A0A]/85 leading-relaxed"
          data-testid="consent-text"
        >
          {data?.consent_text}
        </article>

        <div className="mt-8 bg-white/50 border border-[#0A0A0A]/10 rounded-2xl p-6">
          <label className="flex items-start gap-3 cursor-pointer" data-testid="consent-checkbox-label">
            <input
              type="checkbox"
              checked={checkbox}
              onChange={(e) => setCheckbox(e.target.checked)}
              className="mt-1 w-5 h-5 accent-[#D4A017]"
              data-testid="consent-checkbox"
            />
            <span className="text-sm text-[#0A0A0A]/85 leading-relaxed">
              Io, <strong>{data?.paziente?.nome} {data?.paziente?.cognome}</strong> ({data?.paziente?.email}), dichiaro di aver letto e compreso quanto sopra e presto il mio libero consenso informato al trattamento psicologico erogato da Dr./Dr.ssa {data?.terapista?.nome} {data?.terapista?.cognome}.
            </span>
          </label>

          {error && (
            <p className="mt-4 text-sm text-red-600" data-testid="consent-inline-error">{error}</p>
          )}

          <button
            onClick={submit}
            disabled={!checkbox || submitting}
            className="mt-6 w-full inline-flex items-center justify-center gap-3 px-8 py-4 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg tracking-wide transition-all"
            data-testid="consent-submit"
          >
            {submitting ? "Registrazione in corso…" : "Presto il mio consenso"}
          </button>
        </div>

        <p className="text-center text-[#0A0A0A]/50 text-xs mt-8 leading-relaxed max-w-xl mx-auto">
          Questo consenso è prestato al singolo/la singola professionista, non a Bidoc SRL. Il/la professionista è Titolare autonomo del Trattamento dei dati clinici emersi nelle sedute, con obbligo di segreto professionale (art. 622 c.p.).
        </p>
      </div>
    </main>
  );
}
