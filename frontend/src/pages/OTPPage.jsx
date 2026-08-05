import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { ShieldCheck, RotateCcw } from "lucide-react";

export default function OTPPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { refreshUser } = useAuth();
  const email = location.state?.email || "";
  const otpDev = location.state?.otp_dev || "";

  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    if (countdown > 0) {
      const t = setTimeout(() => setCountdown(c => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [countdown]);

  const handleVerify = async (e) => {
    e.preventDefault();
    setError("");
    if (otp.length !== 6) { setError("Il codice OTP deve essere di 6 cifre"); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/auth/verify-otp`, { email, otp_code: otp }, { withCredentials: true });
      await refreshUser();
      setSuccess("Account verificato! Reindirizzamento...");
      // Flag so the destination can suggest PWA install
      sessionStorage.setItem("just-registered", "1");
      setTimeout(() => navigate("/paziente"), 1500);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Codice OTP non valido");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      const res = await axios.post(`${API}/auth/resend-otp`, { email });
      setSuccess(`Nuovo codice inviato! ${res.data.otp_dev ? `(Dev: ${res.data.otp_dev})` : ""}`);
      setCountdown(60);
      setTimeout(() => setSuccess(""), 5000);
    } catch {
      setError("Errore nel reinvio del codice");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent flex items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <div className="w-16 h-16 rounded-full bg-white/30 flex items-center justify-center mx-auto mb-6">
          <ShieldCheck className="w-8 h-8 text-[#0A0A0A]" />
        </div>

        <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit] mb-2">Verifica Email</h1>
        <p className="text-[#0A0A0A]/65 mb-2">
          Abbiamo inviato un codice OTP a <strong className="text-[#0A0A0A]">{email}</strong>
        </p>

        {otpDev && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-700 text-sm">
            <strong>Modalità Sviluppo — Codice OTP:</strong>{" "}
            <span className="font-mono text-lg font-bold">{otpDev}</span>
          </div>
        )}

        {error && (
          <div data-testid="otp-error" className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
            {error}
          </div>
        )}
        {success && (
          <div data-testid="otp-success" className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
            {success}
          </div>
        )}

        <form onSubmit={handleVerify} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-[#0A0A0A] mb-2 text-left">Codice OTP (6 cifre)</label>
            <input
              data-testid="otp-input"
              type="text" value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              className="w-full text-center text-3xl font-mono tracking-widest px-4 py-4 border-2 border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] focus:border-transparent"
            />
          </div>

          <button
            data-testid="otp-verify-btn"
            type="submit" disabled={loading || otp.length !== 6}
            className="w-full py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-colors disabled:opacity-50 font-[Outfit]"
          >
            {loading ? "Verifica in corso..." : "Verifica Account"}
          </button>
        </form>

        <div className="mt-4">
          <button
            data-testid="otp-resend-btn"
            onClick={handleResend}
            disabled={resending || countdown > 0}
            className="flex items-center gap-2 text-sm text-[#0A0A0A]/65 hover:text-[#0A0A0A] mx-auto disabled:opacity-50 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            {countdown > 0 ? `Reinvia tra ${countdown}s` : "Reinvia codice"}
          </button>
        </div>
      </div>
    </div>
  );
}
