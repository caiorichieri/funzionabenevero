import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Lock, Eye, EyeOff, Check } from "lucide-react";
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

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("idle"); // idle | submitting | done

  useEffect(() => {
    if (!token) setError("Il link di reset è mancante o non valido.");
  }, [token]);

  const score = scorePassword(password);
  const strengthLabel = ["Molto debole", "Debole", "Discreta", "Buona", "Forte", "Ottima"][score];
  const strengthColor = ["bg-red-500", "bg-red-400", "bg-orange-400", "bg-yellow-400", "bg-green-500", "bg-green-600"][score];

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!token) { setError("Il link di reset è mancante o non valido."); return; }
    if (password.length < MIN_LENGTH) { setError(`La password deve avere almeno ${MIN_LENGTH} caratteri.`); return; }
    if (password !== confirm) { setError("Le due password non corrispondono."); return; }
    setStatus("submitting");
    try {
      await axios.post(`${API}/auth/reset-password`, { token, new_password: password });
      setStatus("done");
      // Do NOT auto-login. Force user to sign in with the new password.
      window.history.replaceState({}, "", "/reset-password");
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) {
      setError(err.response?.data?.detail || "Il link di reset non è valido o è scaduto.");
      setStatus("idle");
    }
  };

  return (
    <main className="min-h-screen bg-[#F4EAA8] flex items-center justify-center px-6 py-16" data-testid="reset-password-page">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-3xl p-8 shadow-lg">
          <div className="flex justify-center mb-5">
            <Mascotte name="abbraccio" theme="light" size={90} animation="breathe" />
          </div>
          <h1 className="font-serif text-3xl text-[#0A0A0A] text-center leading-tight">
            Crea una nuova password
          </h1>
          <p className="text-sm text-[#0A0A0A]/65 text-center mt-2">
            Scegli una password sicura. La userai per accedere alla tua area.
          </p>

          {status === "done" ? (
            <div className="mt-8 p-5 rounded-2xl bg-green-50 border border-green-200 text-center" data-testid="reset-done-message">
              <Check className="w-8 h-8 text-green-600 mx-auto" />
              <p className="text-sm text-green-900 mt-3 font-medium">Password aggiornata!</p>
              <p className="text-xs text-green-800/70 mt-1">Ti reindirizzeremo al login tra un attimo...</p>
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-4">
              <div>
                <label htmlFor="rp-password" className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2">Nuova password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                  <input
                    id="rp-password"
                    data-testid="reset-password-input"
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
                <label htmlFor="rp-confirm" className="block text-xs uppercase tracking-widest text-[#0A0A0A]/55 mb-2">Conferma password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                  <input
                    id="rp-confirm"
                    data-testid="reset-confirm-input"
                    type={show ? "text" : "password"}
                    required minLength={MIN_LENGTH} maxLength={128} autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                  />
                </div>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800" role="alert" data-testid="reset-error">
                  {error}
                </div>
              )}

              <button
                data-testid="reset-submit-btn"
                type="submit" disabled={status === "submitting" || !token}
                className="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-semibold rounded-full shadow-md hover:shadow-lg"
              >
                {status === "submitting" ? "Aggiornamento..." : "Salva nuova password"}
              </button>

              <p className="text-center text-xs text-[#0A0A0A]/50 pt-2">
                <Link to="/login" className="hover:underline">Torna al login</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
