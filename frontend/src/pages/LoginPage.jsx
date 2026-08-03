import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(form.email, form.password);
      if (user.role === "admin") navigate("/admin");
      else if (user.role === "terapeuta") navigate("/terapeuta");
      else navigate("/paziente");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Credenziali non valide");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0A0A0A] flex-col justify-between p-12">
        <div>
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 rounded-full bg-[#E9D628] flex items-center justify-center">
              <span className="text-[#0A0A0A] font-bold text-sm font-[Outfit]">FB</span>
            </div>
            <span className="text-white text-xl font-semibold font-[Outfit]">FunzionaBene</span>
          </div>
          <div className="space-y-4">
            <h1 className="text-4xl font-bold text-white font-[Outfit] leading-tight">
              Benvenuto nel<br />
              <span className="text-[#E9D628]">Gestionale</span>
            </h1>
            <p className="text-[rgba(253,251,247,0.7)] text-lg leading-relaxed">
              Piattaforma integrata di sessuologia online FunzionaBene.
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: "Terapisti", value: "12+" },
            { label: "Pazienti", value: "340+" },
            { label: "Sessioni/mese", value: "480+" },
            { label: "Soddisfazione", value: "98%" }
          ].map((stat) => (
            <div key={stat.label} className="bg-white/5 border border-white/10 rounded-2xl p-4">
              <div className="text-2xl font-bold text-[#E9D628] font-[Outfit]">{stat.value}</div>
              <div className="text-[rgba(253,251,247,0.6)] text-sm mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel - Login form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 rounded-full bg-[#0A0A0A]" />
            <span className="text-[#0A0A0A] text-xl font-semibold font-[Outfit]">FunzionaBene</span>
          </div>

          <div className="mb-8 flex items-center gap-4">
            <Mascotte name="abbraccio" theme="light" size={64} animation="breathe" />
            <div>
              <h2 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Bentornato</h2>
              <p className="text-[#0A0A0A]/65 mt-1">Bello rivederti.</p>
            </div>
          </div>

          {error && (
            <div data-testid="login-error" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
                <input
                  data-testid="login-email"
                  type="email"
                  value={form.email}
                  onChange={e => setForm({ ...form, email: e.target.value })}
                  placeholder="nome@funzionabene.it"
                  required
                  className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] placeholder-[rgba(28,28,28,0.4)] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
                <input
                  data-testid="login-password"
                  type={showPass ? "text" : "password"}
                  value={form.password}
                  onChange={e => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-12 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] placeholder-[rgba(28,28,28,0.4)] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] transition-all"
                />
                <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50">
                  {showPass ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              <div className="mt-2 text-right">
                <Link data-testid="forgot-password-link" to="/forgot-password" className="text-xs text-[#0A0A0A]/60 hover:text-[#0A0A0A] hover:underline">
                  Password dimenticata?
                </Link>
              </div>
            </div>

            <button
              data-testid="login-submit"
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-colors disabled:opacity-50 font-[Outfit]"
            >
              {loading ? "Accesso in corso..." : "Accedi"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-[#0A0A0A]/65">
            Non hai un account?{" "}
            <Link data-testid="register-link" to="/registrati" className="text-[#0A0A0A] font-medium hover:text-[#0A0A0A]/70">
              Registrati
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
