import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { Lock, Eye, EyeOff, Check, ShieldCheck } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

const MIN_LENGTH = 8;

function scorePassword(pwd) {
  let score = 0;
  if (pwd.length >= MIN_LENGTH) score += 1;
  if (pwd.length >= 12) score += 1;
  if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) score += 1;
  if (/[0-9]/.test(pwd)) score += 1;
  if (/[^A-Za-z0-9]/.test(pwd)) score += 1;
  return score; // 0-5
}

export default function AttivaAccountPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const token = params.get("token") || "";

  const [tokenState, setTokenState] = useState("checking"); // checking | valid | invalid
  const [candidato, setCandidato] = useState(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle"); // idle | submitting | done

  // Validate the token before showing the form
  useEffect(() => {
    if (!token) {
      setTokenState("invalid");
      setError("Il link di attivazione è mancante o non valido.");
      return;
    }
    axios.get(`${API}/auth/attivazione-terapeuta/verifica`, { params: { token } })
      .then(r => {
        setCandidato(r.data);
        setTokenState("valid");
      })
      .catch(err => {
        setTokenState("invalid");
        setError(err.response?.data?.detail || "Il link di attivazione non è valido o è scaduto.");
      });
  }, [token]);

  const score = scorePassword(password);
  const strengthLabel = ["Molto debole", "Debole", "Discreta", "Buona", "Forte", "Ottima"][score];
  const strengthColor = ["bg-red-500", "bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-green-500", "bg-green-600"][score];

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < MIN_LENGTH) { setError(`La password deve avere almeno ${MIN_LENGTH} caratteri.`); return; }
    if (password !== confirm) { setError("Le due password non corrispondono."); return; }
    setStatus("submitting");
    try {
      await axios.post(
        `${API}/auth/attivazione-terapeuta/completa`,
        { token, new_password: password },
        { withCredentials: true }
      );
      setStatus("done");
      // Refresh the auth context (cookies are now set) and redirect to the therapist onboarding.
      if (typeof refreshUser === "function") { try { await refreshUser(); } catch { /* ignore */ } }
      window.history.replaceState({}, "", "/attiva-account");
      setTimeout(() => navigate("/terapeuta"), 1500);
    } catch (err) {
      setError(err.response?.data?.detail || "Impossibile completare l'attivazione.");
      setStatus("idle");
    }
  };

  return (
    <main className="min-h-screen bg-[#F4EAA8] flex items-center justify-center px-6 py-16" data-testid="attiva-account-page">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-3xl p-8 shadow-lg">
          <div className="flex justify-center mb-5">
            <Mascotte name="saltitante" theme="light" size={90} animation="breathe" />
          </div>

          {tokenState === "checking" && (
            <p className="text-center text-sm text-[#0A0A0A]/55">Verifica del link in corso...</p>
          )}

          {tokenState === "invalid" && (
            <div className="text-center" data-testid="attiva-error-state">
              <h1 className="font-serif text-2xl text-[#0A0A0A] leading-tight">Link non valido</h1>
              <p className="text-sm text-[#0A0A0A]/65 mt-3">{error}</p>
              <p className="text-xs text-[#0A0A0A]/50 mt-4">
                Contatta l'amministrazione a <a href="mailto:hr@funzionabene.it" className="underline">hr@funzionabene.it</a> per ricevere un nuovo link.
              </p>
            </div>
          )}

          {tokenState === "valid" && (
            <>
              <h1 className="font-serif text-3xl text-[#0A0A0A] text-center leading-tight">
                Benvenuto/a{candidato?.nome ? `, ${candidato.nome}` : ""}!
              </h1>
              <p className="text-sm text-[#0A0A0A]/65 text-center mt-2">
                Crea la tua password per attivare l'account e iniziare l'onboarding.
              </p>

              {status === "done" ? (
                <div className="mt-8 p-5 rounded-2xl bg-green-50 border border-green-200 text-center" data-testid="attiva-done-message">
                  <ShieldCheck className="w-8 h-8 text-green-600 mx-auto" />
                  <p className="text-sm text-green-900 mt-3 font-medium">Account attivato!</p>
                  <p className="text-xs text-green-800/70 mt-1">Ti portiamo alla tua area riservata...</p>
                </div>
              ) : (
                <form onSubmit={submit} className="mt-6 space-y-4">
                  <div>
                    <label htmlFor="aa-password" className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                      <input
                        id="aa-password"
                        data-testid="attiva-password-input"
                        type={show ? "text" : "password"}
                        required minLength={MIN_LENGTH} maxLength={128} autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full pl-10 pr-10 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                      />
                      <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/40 hover:text-[#0A0A0A]">
                        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    {password && (
                      <div className="mt-2">
                        <div className="flex gap-1">
                          {[0, 1, 2, 3, 4].map(i => (
                            <div key={i} className={`h-1 flex-1 rounded-full ${i < score ? strengthColor : "bg-[#0A0A0A]/10"}`} />
                          ))}
                        </div>
                        <p className="text-[10px] text-[#0A0A0A]/55 mt-1">{strengthLabel}</p>
                      </div>
                    )}
                  </div>

                  <div>
                    <label htmlFor="aa-confirm" className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2">Conferma password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                      <input
                        id="aa-confirm"
                        data-testid="attiva-confirm-input"
                        type={show ? "text" : "password"}
                        required minLength={MIN_LENGTH} maxLength={128} autoComplete="new-password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                      />
                    </div>
                  </div>

                  {error && (
                    <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800" role="alert" data-testid="attiva-error">
                      {error}
                    </div>
                  )}

                  <button
                    data-testid="attiva-submit-btn"
                    type="submit" disabled={status === "submitting"}
                    className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-semibold rounded-full shadow-md hover:shadow-lg"
                  >
                    {status === "submitting" ? "Attivazione..." : "Attiva account e inizia l'onboarding"}
                  </button>

                  <p className="text-center text-xs text-[#0A0A0A]/55 pt-2">
                    Prossimo passo: caricherai i documenti, verificherai il telefono e firmerai l'autocertificazione.
                  </p>
                  <p className="text-center text-xs text-[#0A0A0A]/50 pt-1">
                    <Link to="/login" className="hover:underline">Già attivato? Accedi</Link>
                  </p>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  );
}
