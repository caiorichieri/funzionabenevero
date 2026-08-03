import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ArrowLeft, Mail } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | sent
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setStatus("sending");
    try {
      await axios.post(`${API}/auth/forgot-password`, { email: email.trim().toLowerCase() });
      setStatus("sent");
    } catch (err) {
      setError("Non siamo riusciti a processare la richiesta. Riprova tra qualche minuto.");
      setStatus("idle");
    }
  };

  return (
    <main className="min-h-screen bg-[#F4EAA8] flex items-center justify-center px-6 py-16" data-testid="forgot-password-page">
      <div className="max-w-md w-full">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-6">
          <ArrowLeft className="w-4 h-4" /> Torna al login
        </Link>

        <div className="bg-white rounded-3xl p-8 shadow-lg">
          <div className="flex justify-center mb-5">
            <Mascotte name="sereno" theme="light" size={90} animation="breathe" />
          </div>
          <h1 className="font-serif text-3xl text-[#0A0A0A] text-center leading-tight">
            Password dimenticata?
          </h1>
          <p className="text-sm text-[#0A0A0A]/65 text-center mt-2">
            Inserisci la tua email e ti invieremo un link per crearne una nuova.
          </p>

          {status === "sent" ? (
            <div className="mt-6 p-5 rounded-2xl bg-green-50 border border-green-200 text-sm text-green-900 leading-relaxed" data-testid="forgot-sent-message">
              <strong>Controlla la tua casella email.</strong><br />
              Se un account esiste con l&apos;indirizzo indicato, riceverai il link per il reset entro pochi minuti. Il link è valido per 30 minuti e utilizzabile una sola volta.
              <div className="mt-4 pt-3 border-t border-green-200 text-xs text-green-800/80">
                Non arriva? Controlla la cartella spam. Puoi anche <button onClick={() => setStatus("idle")} className="underline">rimandare il link</button>.
              </div>
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-4">
              <div>
                <label htmlFor="fp-email" className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                  <input
                    id="fp-email"
                    data-testid="forgot-email-input"
                    type="email" required autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="tu@email.it"
                    className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                  />
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800" role="alert">
                  {error}
                </div>
              )}

              <button
                data-testid="forgot-submit-btn"
                type="submit" disabled={status === "sending"}
                className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-semibold rounded-full shadow-md hover:shadow-lg"
              >
                {status === "sending" ? "Invio in corso..." : "Invia il link"}
              </button>
            </form>
          )}
        </div>

        <p className="text-xs text-center text-[#0A0A0A]/50 mt-6">
          Hai bisogno di aiuto? Scrivi a <a href="mailto:info@funzionabene.it" className="text-[#0A0A0A] hover:underline">info@funzionabene.it</a>
        </p>
      </div>
    </main>
  );
}
