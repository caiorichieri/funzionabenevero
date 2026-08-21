import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { useAuth } from "@/contexts/AuthContext";
import { Star, CheckCircle2, AlertCircle } from "lucide-react";

export default function ReviewPage() {
  const { appuntamentoId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) navigate(`/login?redirect=/recensione/${appuntamentoId}`);
  }, [user, appuntamentoId, navigate]);

  const submit = async () => {
    if (rating < 1) return setError("Seleziona un voto da 1 a 5 stelle");
    setSubmitting(true);
    setError("");
    try {
      await axios.post(`${API}/reviews`, {
        appuntamento_id: appuntamentoId,
        voto: rating,
        testo: text,
      }, { withCredentials: true });
      setDone(true);
    } catch (e) {
      setError(e?.response?.data?.detail || "Errore invio recensione");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <main className="min-h-screen bg-[#F4F1ED] flex items-center justify-center px-6" data-testid="review-done">
        <div className="max-w-md text-center">
          <CheckCircle2 className="w-16 h-16 text-emerald-600 mx-auto mb-6" />
          <h1 className="font-serif text-3xl text-[#0A0A0A] mb-4">Grazie!</h1>
          <p className="text-[#0A0A0A]/75">
            La tua recensione è stata inviata e sarà pubblicata dopo una breve verifica.
          </p>
          <button
            onClick={() => navigate("/paziente")}
            className="mt-8 px-8 py-3 rounded-full bg-[#0A0A0A] text-white text-sm"
            data-testid="review-goto-dash"
          >
            Vai alla mia area
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F4F1ED] py-16 px-6">
      <div className="max-w-xl mx-auto" data-testid="review-page">
        <div className="text-center mb-10">
          <p className="text-xs tracking-[0.3em] uppercase text-[#0A0A0A]/50 mb-3">La tua opinione</p>
          <h1 className="font-serif text-3xl lg:text-4xl text-[#0A0A0A]">Com&apos;è andata la sessione?</h1>
          <p className="text-[#0A0A0A]/65 mt-3 text-sm">Il tuo parere aiuta altri pazienti. Rimarrà anonimo (solo il tuo nome).</p>
        </div>

        <div className="bg-white/70 border border-[#0A0A0A]/10 rounded-2xl p-8 space-y-6">
          <div>
            <label className="block text-sm text-[#0A0A0A]/70 mb-3">Voto</label>
            <div className="flex gap-2 justify-center" onMouseLeave={() => setHover(0)}>
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  onClick={() => setRating(n)}
                  onMouseEnter={() => setHover(n)}
                  data-testid={`star-${n}`}
                  className="p-2 transition-transform hover:scale-110"
                >
                  <Star
                    className={`w-10 h-10 ${(hover || rating) >= n ? "fill-[#D4A017] text-[#D4A017]" : "text-[#0A0A0A]/25"}`}
                  />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-[#0A0A0A]/70 mb-2">Commento (facoltativo)</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
              rows={6}
              placeholder="Cosa hai apprezzato? Cosa migliorare? Sii sincero/a — la tua recensione sarà utile ad altri pazienti."
              className="w-full px-4 py-3 rounded-xl border border-[#0A0A0A]/15 bg-white/50 text-sm text-[#0A0A0A] focus:outline-none focus:border-[#6B8FA3]"
              data-testid="review-text"
            />
            <div className="text-right text-xs text-[#0A0A0A]/40 mt-1">{text.length}/2000</div>
          </div>

          {error && (
            <div className="flex items-start gap-2 text-sm text-red-600" data-testid="review-error">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            onClick={submit}
            disabled={submitting || rating < 1}
            className="w-full inline-flex items-center justify-center gap-2 px-8 py-4 disabled:opacity-40 disabled:cursor-not-allowed bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md tracking-wide transition-all"
            data-testid="review-submit"
          >
            {submitting ? "Invio in corso…" : "Invia recensione"}
          </button>
        </div>

        <p className="text-center text-[#0A0A0A]/50 text-xs mt-6">
          Le recensioni sono soggette a moderazione. Contenuti offensivi o falsi vengono rifiutati.
        </p>
      </div>
    </main>
  );
}
