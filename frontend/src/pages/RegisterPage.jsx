import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Eye, EyeOff, User, Mail, Lock, UserCheck } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

const ROLES = [
  { id: "paziente", label: "Sono un Paziente", desc: "Cerco supporto psicologico/sessuologico" },
  { id: "terapeuta", label: "Sono un Terapeuta", desc: "Voglio candidarmi per offrire i miei servizi" }
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [role, setRole] = useState("");
  const [form, setForm] = useState({ nome: "", cognome: "", email: "", password: "", conferma_password: "" });
  const [consents, setConsents] = useState({
    privacy: false,
    termini: false,
    dati_sanitari: false,
    marketing: false,
    ricerca: false,
    miglioramento: false,
  });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRoleSelect = (r) => {
    // Terapeuta cannot self-register — always redirect to the application form.
    if (r === "terapeuta") {
      navigate("/candidatura-terapeuta");
      return;
    }
    setRole(r);
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password !== form.conferma_password) { setError("Le password non coincidono"); return; }
    if (form.password.length < 8) { setError("La password deve avere almeno 8 caratteri"); return; }
    if (role === "paziente") {
      if (!consents.privacy || !consents.termini || !consents.dati_sanitari) {
        setError("Devi accettare Privacy, Termini e trattamento dei dati sanitari per proseguire.");
        return;
      }
    } else {
      if (!consents.privacy) {
        setError("Devi accettare l'informativa Privacy per proseguire.");
        return;
      }
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/register`, {
        email: form.email, password: form.password,
        nome: form.nome, cognome: form.cognome,
        role,
        consenso_privacy: consents.privacy,
        consenso_termini: consents.termini,
        consenso_dati_sanitari: consents.dati_sanitari,
        consenso_marketing: consents.marketing,
        consenso_ricerca: consents.ricerca,
        consenso_miglioramento: consents.miglioramento,
        consent_version_privacy: "1.0",
        consent_version_termini: "1.0",
      });
      navigate("/verifica-otp", { state: { email: form.email, otp_dev: res.data.otp_dev } });
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Errore durante la registrazione");
    } finally {
      setLoading(false);
    }
  };

  const toggleConsent = (k) => setConsents(prev => ({ ...prev, [k]: !prev[k] }));

  return (
    <div className="min-h-screen bg-transparent flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Mascotte name="saltitante" theme="light" size={90} animation="wiggle" />
          </div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Crea il tuo account</h1>
          <p className="text-[#0A0A0A]/65 mt-2">Il primo passo è già qui.</p>
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <p className="text-center text-[#0A0A0A] font-medium mb-6">Chi sei?</p>
            {ROLES.map(r => (
              <button
                key={r.id}
                data-testid={`role-${r.id}`}
                onClick={() => handleRoleSelect(r.id)}
                className="w-full p-5 border-2 border-[#0A0A0A]/12 rounded-2xl text-left hover:border-[#0A0A0A] hover:bg-white/20 transition-all group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-white/30 group-hover:bg-white/40 flex items-center justify-center">
                    {r.id === "paziente" ? <User className="w-5 h-5 text-[#0A0A0A]" /> : <UserCheck className="w-5 h-5 text-[#0A0A0A]" />}
                  </div>
                  <div>
                    <div className="font-semibold text-[#0A0A0A] font-[Outfit]">{r.label}</div>
                    <div className="text-sm text-[#0A0A0A]/65">{r.desc}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {step === 2 && (
          <>
            <div className="mb-4">
              <button onClick={() => setStep(1)} className="text-sm text-[#0A0A0A]/65 hover:text-[#0A0A0A] flex items-center gap-1">
                ← Cambia ruolo
              </button>
              <div className="mt-2 inline-flex items-center gap-2 bg-white/30 text-[#0A0A0A] text-sm px-3 py-1 rounded-full">
                {role === "paziente" ? <User className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                {role === "paziente" ? "Paziente" : "Terapeuta"}
              </div>
            </div>

            {error && (
              <div data-testid="register-error" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Nome</label>
                  <input
                    data-testid="register-nome"
                    type="text" value={form.nome}
                    onChange={e => setForm({ ...form, nome: e.target.value })}
                    required placeholder="Mario"
                    className="w-full px-3 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Cognome</label>
                  <input
                    data-testid="register-cognome"
                    type="text" value={form.cognome}
                    onChange={e => setForm({ ...form, cognome: e.target.value })}
                    required placeholder="Rossi"
                    className="w-full px-3 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
                  <input
                    data-testid="register-email"
                    type="email" value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    required placeholder="mario.rossi@email.it"
                    className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
                  <input
                    data-testid="register-password"
                    type={showPass ? "text" : "password"} value={form.password}
                    onChange={e => setForm({ ...form, password: e.target.value })}
                    required placeholder="Minimo 8 caratteri"
                    className="w-full pl-10 pr-12 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                  <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50">
                    {showPass ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Conferma Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
                  <input
                    data-testid="register-conferma-password"
                    type={showPass ? "text" : "password"} value={form.conferma_password}
                    onChange={e => setForm({ ...form, conferma_password: e.target.value })}
                    required placeholder="Ripeti la password"
                    className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
                  />
                </div>
              </div>

              <div className="space-y-2.5 pt-1 border-t border-[#0A0A0A]/10">
                <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/80" data-testid="consent-privacy-wrapper">
                  <input
                    data-testid="consent-privacy"
                    type="checkbox"
                    checked={consents.privacy}
                    onChange={() => toggleConsent("privacy")}
                    className="mt-1 accent-[#0A0A0A]"
                    required
                  />
                  <span>
                    <span className="text-red-600">*</span> Ho letto l&apos;
                    <Link to={role === "paziente" ? "/privacy-pazienti" : "/privacy-visitatori"} target="_blank" className="underline hover:text-[#0A0A0A]">
                      Informativa Privacy
                    </Link>{" "}
                    (art. 13 GDPR).
                  </span>
                </label>

                {role === "paziente" && (
                  <>
                    <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/80" data-testid="consent-termini-wrapper">
                      <input
                        data-testid="consent-termini"
                        type="checkbox"
                        checked={consents.termini}
                        onChange={() => toggleConsent("termini")}
                        className="mt-1 accent-[#0A0A0A]"
                        required
                      />
                      <span>
                        <span className="text-red-600">*</span> Ho letto e accetto i{" "}
                        <Link to="/termini-pazienti" target="_blank" className="underline hover:text-[#0A0A0A]">
                          Termini e Condizioni
                        </Link>
                        .
                      </span>
                    </label>

                    <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/80" data-testid="consent-sanitari-wrapper">
                      <input
                        data-testid="consent-sanitari"
                        type="checkbox"
                        checked={consents.dati_sanitari}
                        onChange={() => toggleConsent("dati_sanitari")}
                        className="mt-1 accent-[#0A0A0A]"
                        required
                      />
                      <span>
                        <span className="text-red-600">*</span> Acconsento al trattamento dei miei dati particolari relativi alla salute per la compilazione del questionario iniziale e la proposta del Terapeuta più adatto (art. 9.2.a GDPR).
                      </span>
                    </label>
                  </>
                )}

                <div className="text-[11px] uppercase tracking-widest text-[#0A0A0A]/45 pt-1">Facoltativi</div>

                <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/75" data-testid="consent-marketing-wrapper">
                  <input
                    data-testid="consent-marketing"
                    type="checkbox"
                    checked={consents.marketing}
                    onChange={() => toggleConsent("marketing")}
                    className="mt-1 accent-[#0A0A0A]"
                  />
                  <span>Voglio ricevere comunicazioni promozionali su nuovi servizi, contenuti e iniziative di Funzionabene (art. 6.1.a GDPR).</span>
                </label>

                <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/75" data-testid="consent-ricerca-wrapper">
                  <input
                    data-testid="consent-ricerca"
                    type="checkbox"
                    checked={consents.ricerca}
                    onChange={() => toggleConsent("ricerca")}
                    className="mt-1 accent-[#0A0A0A]"
                  />
                  <span>Autorizzo l&apos;uso dei miei dati in forma anonimizzata per ricerca scientifica in ambito psicologico (art. 9.2.a GDPR).</span>
                </label>

                <label className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/75" data-testid="consent-miglioramento-wrapper">
                  <input
                    data-testid="consent-miglioramento"
                    type="checkbox"
                    checked={consents.miglioramento}
                    onChange={() => toggleConsent("miglioramento")}
                    className="mt-1 accent-[#0A0A0A]"
                  />
                  <span>Acconsento all&apos;utilizzo dei miei dati aggregati per analisi statistiche di miglioramento del servizio.</span>
                </label>
              </div>

              <button
                data-testid="register-submit"
                type="submit" disabled={loading}
                className="w-full py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-colors disabled:opacity-50 font-[Outfit]"
              >
                {loading ? "Registrazione in corso..." : "Crea Account"}
              </button>
            </form>
          </>
        )}

        <p className="mt-6 text-center text-sm text-[#0A0A0A]/65">
          Hai già un account?{" "}
          <Link data-testid="login-link" to="/login" className="text-[#0A0A0A] font-medium hover:text-[#0A0A0A]/70">
            Accedi
          </Link>
        </p>
      </div>
    </div>
  );
}
