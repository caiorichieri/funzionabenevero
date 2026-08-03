import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import axios from "axios";
import { API, useAuth } from "@/contexts/AuthContext";
import { X, Check, Mail, Lock, User as UserIcon, CreditCard, ShieldCheck, ArrowRight, Smartphone } from "lucide-react";
import DatiFiscaliStep from "@/components/public/DatiFiscaliStep";

const GIORNI_IT = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"];

function formatSlot(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const giorno = GIORNI_IT[(d.getDay() + 6) % 7];
    const dateStr = d.toLocaleDateString("it-IT", { day: "2-digit", month: "long", year: "numeric" });
    const timeStr = d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
    return `${giorno} ${dateStr} · ${timeStr}`;
  } catch { return iso; }
}

// Steps: review → auth (login or register) → otp → dati-fiscali → payment → sms-otp → success
export default function BookingSheet({ open, onClose, terapista, slot, currentUser }) {
  const { login, refreshUser } = useAuth();
  const [step, setStep] = useState("review");
  const [mode, setMode] = useState("register"); // register | login
  const [form, setForm] = useState({ nome: "", cognome: "", email: "", password: "", otp: "", privacy: false });
  const [otpDev, setOtpDev] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pazienteProfile, setPazienteProfile] = useState(null);
  // SMS OTP state (phone verification after payment)
  const [smsPhone, setSmsPhone] = useState("");
  const [smsOtp, setSmsOtp] = useState("");
  const [smsOtpDev, setSmsOtpDev] = useState("");
  const [smsPrivacy, setSmsPrivacy] = useState(false);
  const [smsPhoneLocked, setSmsPhoneLocked] = useState(false);
  // Fattura sanitaria: patient opts out of Sistema TS transmission (art.3 DM 31/07/2015)
  const [opposizioneTS, setOpposizioneTS] = useState(false);

  // Check if current user already has dati fiscali completi (skip step if yes)
  const gotoAfterAuth = async () => {
    try {
      const res = await axios.get(`${API}/pazienti/profilo/me`, { withCredentials: true });
      setPazienteProfile(res.data);
      if (res.data.dati_fiscali_completi) {
        setStep("payment");
      } else {
        setStep("dati-fiscali");
      }
    } catch {
      setStep("dati-fiscali");
    }
  };

  useEffect(() => {
    if (open) {
      setError("");
      if (currentUser && currentUser.role === "paziente") {
        gotoAfterAuth();
      } else {
        setStep("review");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, currentUser]);

  if (!open || !terapista || !slot) return null;

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.privacy) { setError("Devi accettare la Privacy Policy"); return; }
    if (form.password.length < 8) { setError("La password deve avere almeno 8 caratteri"); return; }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/auth/register`, {
        email: form.email, password: form.password,
        nome: form.nome, cognome: form.cognome,
        role: "paziente", consenso_privacy: true,
      });
      setOtpDev(res.data.otp_dev || "");
      setStep("otp");
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore nella registrazione");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const u = await login(form.email, form.password);
      if (u.role !== "paziente") {
        setError("Solo gli utenti pazienti possono prenotare");
        return;
      }
      await gotoAfterAuth();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Credenziali non valide");
    } finally {
      setLoading(false);
    }
  };

  const handleOTP = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await axios.post(`${API}/auth/verify-otp`, { email: form.email, otp_code: form.otp }, { withCredentials: true });
      await refreshUser();
      await gotoAfterAuth();
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Codice OTP non valido");
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      // MOCKED PAYMENT — simulate success, then trigger SMS OTP before final confirmation
      const pazienteRes = await axios.get(`${API}/pazienti/profilo/me`, { withCredentials: true });
      const telefono = pazienteRes.data.telefono || "";
      if (!telefono) {
        setError("Numero di telefono mancante. Torna ai dati fiscali per aggiungerlo.");
        return;
      }
      setSmsPhone(telefono);
      setSmsPhoneLocked(true);
      // Send OTP via SMS
      const r = await axios.post(`${API}/sms/send-otp`, { phone: telefono, context: "prenotazione" }, { withCredentials: true });
      setSmsOtpDev(r.data?.otp_dev || "");
      setSmsOtp("");
      setSmsPrivacy(false);
      setStep("sms-otp");
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore nell'invio del codice SMS");
    } finally {
      setLoading(false);
    }
  };

  const handleResendSms = async () => {
    setError("");
    setLoading(true);
    try {
      const r = await axios.post(`${API}/sms/send-otp`, { phone: smsPhone, context: "prenotazione" }, { withCredentials: true });
      setSmsOtpDev(r.data?.otp_dev || "");
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore reinvio SMS");
    } finally {
      setLoading(false);
    }
  };

  const handleSmsVerifyAndBook = async (e) => {
    e.preventDefault();
    setError("");
    if (!smsPrivacy) { setError("Devi accettare il trattamento dei dati per procedere"); return; }
    if (!smsOtp || smsOtp.length < 4) { setError("Inserisci il codice OTP ricevuto via SMS"); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/sms/verify-otp`, { phone: smsPhone, otp_code: smsOtp }, { withCredentials: true });
      const pazienteRes = await axios.get(`${API}/pazienti/profilo/me`, { withCredentials: true });
      const paziente_id = pazienteRes.data._id;
      // Create pending appointment + Stripe checkout session, then redirect
      const checkoutRes = await axios.post(`${API}/payments/checkout/booking`, {
        terapeuta_id: terapista._id,
        paziente_id,
        data_ora: slot.data_ora,
        durata_minuti: 50,
        tipologia: "individuale",
        modalita: "classica",
        opposizione_ts: opposizioneTS,
        origin_url: window.location.origin,
      }, { withCredentials: true });
      // Full-page redirect to Stripe Checkout
      window.location.href = checkoutRes.data.checkout_url;
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore durante la creazione del pagamento");
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-[#0A0A0A]/80 backdrop-blur-sm flex items-stretch justify-end"
        onClick={onClose}
        data-testid="booking-sheet"
      >
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "tween", duration: 0.4, ease: "easeOut" }}
          className="w-full max-w-xl bg-white border-l border-[#0A0A0A]/15 overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sticky top-0 bg-white/85 backdrop-blur-xl border-b border-[#0A0A0A]/10 px-6 lg:px-10 py-5 flex items-center justify-between">
            <div>
              <div className="text-xs tracking-[0.2em] uppercase text-[#0A0A0A]">Prenotazione</div>
              <div className="text-sm text-[#0A0A0A] mt-1">Dr. {terapista.nome} {terapista.cognome}</div>
            </div>
            <button onClick={onClose} data-testid="booking-close" aria-label="Chiudi" className="p-2 text-[#0A0A0A]/70 hover:text-[#0A0A0A]">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="px-6 lg:px-10 py-8">
            {/* Progress */}
            <div className="flex items-center gap-2 mb-10">
              {["review","auth","otp","dati-fiscali","payment","sms-otp","success"]
                .filter((s) => s !== "otp" || mode === "register")
                .map((s) => {
                  const order = ["review","auth","otp","dati-fiscali","payment","sms-otp","success"];
                  const cur = order.indexOf(step);
                  const idx = order.indexOf(s);
                  return (
                    <div
                      key={s}
                      className={`h-1 flex-1 rounded-full ${idx <= cur ? "bg-[#0A0A0A]" : "bg-white/10"}`}
                    />
                  );
                })}
            </div>

            {error && (
              <div data-testid="booking-error" className="mb-6 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm">
                {error}
              </div>
            )}

            {/* REVIEW */}
            {step === "review" && (
              <div data-testid="step-review">
                <h2 className="font-serif text-3xl text-[#0A0A0A] leading-tight">Riepilogo</h2>
                <div className="mt-6 p-5 brand-card space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Terapeuta</span>
                    <span className="text-[#0A0A0A]">Dr. {terapista.nome} {terapista.cognome}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Data &amp; Ora</span>
                    <span className="text-[#0A0A0A] text-right">{formatSlot(slot.data_ora)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Durata</span>
                    <span className="text-[#0A0A0A]">50 minuti</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Modalità</span>
                    <span className="text-[#0A0A0A]">Online</span>
                  </div>
                  <div className="flex justify-between pt-3 border-t border-[#0A0A0A]/15">
                    <span className="text-[#0A0A0A]/60">Totale</span>
                    <span className="font-serif text-2xl text-[#0A0A0A]">€{terapista.prezzo_sessione || 90}</span>
                  </div>
                </div>

                <button
                  data-testid="booking-continue"
                  onClick={() => setStep("auth")}
                  className="mt-8 w-full inline-flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-all"
                >
                  Continua <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* AUTH */}
            {step === "auth" && (
              <div data-testid="step-auth">
                <h2 className="font-serif text-3xl text-[#0A0A0A] leading-tight">
                  {mode === "register" ? "Crea il tuo account" : "Accedi"}
                </h2>
                <p className="mt-2 text-sm text-[#0A0A0A]/70">
                  {mode === "register"
                    ? "Ci servono pochi dati per completare la prenotazione."
                    : "Hai già un account?"}
                </p>

                <div className="mt-6 flex gap-2 p-1 bg-white border border-[#0A0A0A]/15 rounded-full w-fit">
                  <button
                    onClick={() => setMode("register")}
                    data-testid="mode-register"
                    className={`px-5 py-2 rounded-full text-sm transition-all ${mode === "register" ? "bg-[#0A0A0A] text-white" : "text-[#0A0A0A]/70"}`}
                  >
                    Registrati
                  </button>
                  <button
                    onClick={() => setMode("login")}
                    data-testid="mode-login"
                    className={`px-5 py-2 rounded-full text-sm transition-all ${mode === "login" ? "bg-[#0A0A0A] text-white" : "text-[#0A0A0A]/70"}`}
                  >
                    Accedi
                  </button>
                </div>

                <form onSubmit={mode === "register" ? handleRegister : handleLogin} className="mt-8 space-y-4">
                  {mode === "register" && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/60 mb-2">Nome</label>
                        <input
                          data-testid="booking-nome"
                          required type="text" value={form.nome}
                          onChange={(e) => setForm({ ...form, nome: e.target.value })}
                          className="w-full px-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                        />
                      </div>
                      <div>
                        <label className="block text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/60 mb-2">Cognome</label>
                        <input
                          data-testid="booking-cognome"
                          required type="text" value={form.cognome}
                          onChange={(e) => setForm({ ...form, cognome: e.target.value })}
                          className="w-full px-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                        />
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/60 mb-2">Email</label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                      <input
                        data-testid="booking-email"
                        required type="email" value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/60 mb-2">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                      <input
                        data-testid="booking-password"
                        required type="password" value={form.password}
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                        placeholder={mode === "register" ? "Min. 8 caratteri" : ""}
                        className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                      />
                    </div>
                  </div>

                  {mode === "register" && (
                    <label className="flex items-start gap-3 text-sm text-[#0A0A0A]/80 cursor-pointer">
                      <input
                        data-testid="booking-privacy"
                        type="checkbox" checked={form.privacy}
                        onChange={(e) => setForm({ ...form, privacy: e.target.checked })}
                        className="mt-1 accent-[#0A0A0A]"
                      />
                      <span>
                        Accetto la <span className="text-[#0A0A0A] underline">Privacy Policy</span> e il trattamento dei dati ai sensi del GDPR.
                      </span>
                    </label>
                  )}

                  <button
                    data-testid="booking-auth-submit"
                    type="submit" disabled={loading}
                    className="w-full mt-4 inline-flex items-center justify-center gap-3 px-6 py-4 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-all"
                  >
                    {loading ? "Attendere..." : mode === "register" ? "Crea account e continua" : "Accedi e continua"}
                  </button>
                </form>
              </div>
            )}

            {/* OTP */}
            {step === "otp" && (
              <div data-testid="step-otp">
                <div className="w-14 h-14 rounded-full bg-white/30 flex items-center justify-center mb-6">
                  <ShieldCheck className="w-6 h-6 text-[#0A0A0A]" />
                </div>
                <h2 className="font-serif text-3xl text-[#0A0A0A] leading-tight">Verifica l&apos;email</h2>
                <p className="mt-3 text-sm text-[#0A0A0A]/70">
                  Abbiamo inviato un codice a 6 cifre a <strong className="text-[#0A0A0A]">{form.email}</strong>.
                </p>

                {otpDev && (
                  <div className="mt-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm" data-testid="otp-dev">
                    <strong>Dev:</strong> codice OTP {otpDev}
                  </div>
                )}

                <form onSubmit={handleOTP} className="mt-8">
                  <input
                    data-testid="booking-otp"
                    type="text" maxLength={6}
                    value={form.otp}
                    onChange={(e) => setForm({ ...form, otp: e.target.value.replace(/\D/g, "").slice(0, 6) })}
                    placeholder="000000"
                    className="w-full text-center text-3xl font-mono tracking-[0.5em] py-4 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] focus:outline-none focus:border-[#0A0A0A]"
                  />
                  <button
                    data-testid="booking-otp-submit"
                    type="submit" disabled={loading || form.otp.length !== 6}
                    className="w-full mt-6 inline-flex items-center justify-center gap-3 px-6 py-4 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg"
                  >
                    {loading ? "Verifica..." : "Verifica e continua"}
                  </button>
                </form>
              </div>
            )}

            {/* DATI FISCALI */}
            {step === "dati-fiscali" && (
              <DatiFiscaliStep
                existingData={pazienteProfile || {}}
                onComplete={(updatedProfile) => {
                  setPazienteProfile(updatedProfile);
                  setStep("payment");
                }}
              />
            )}

            {/* PAYMENT — riepilogo + opposizione TS + redirect a Stripe */}
            {step === "payment" && (
              <div data-testid="step-payment">
                <h2 className="font-serif text-3xl text-[#0A0A0A] leading-tight">Riepilogo e pagamento</h2>
                <p className="mt-2 text-sm text-[#0A0A0A]/70">
                  Il pagamento avviene su <strong>Stripe</strong> con cifratura bancaria. Nessun dato di carta transita sui nostri server.
                </p>

                <div className="mt-6 p-5 brand-card space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Sessione con</span>
                    <span className="text-[#0A0A0A]">Dr. {terapista.nome} {terapista.cognome}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#0A0A0A]/60">Quando</span>
                    <span className="text-[#0A0A0A] text-right">{formatSlot(slot.data_ora)}</span>
                  </div>
                  <div className="flex justify-between pt-3 border-t border-[#0A0A0A]/15">
                    <span className="text-[#0A0A0A]/60">Totale da pagare</span>
                    <span className="font-serif text-2xl text-[#0A0A0A]">€{terapista.prezzo_sessione || 90}</span>
                  </div>
                </div>

                {/* Mandato all'incasso disclosure */}
                <div className="mt-5 p-4 rounded-2xl bg-[#F4CB78]/25 border border-[#F58A1F]/25 text-xs text-[#0A0A0A]/85 leading-relaxed">
                  Il servizio è <strong>erogato direttamente dal professionista</strong> (Dr. {terapista.nome} {terapista.cognome}) — iscritto all&apos;Ordine e titolare della prestazione sanitaria.
                  BIDOC SRL gestisce l&apos;incasso per suo conto in mandato all&apos;incasso con rappresentanza.
                  La <strong>fattura sanitaria</strong> ti verrà emessa a nome del professionista, esente IVA ex art. 10 DPR 633/72.
                </div>

                {/* Opposizione al Sistema TS */}
                <label className="mt-4 flex items-start gap-3 text-xs text-[#0A0A0A]/80 leading-relaxed cursor-pointer p-3 rounded-2xl hover:bg-[#0A0A0A]/[0.03]">
                  <input
                    data-testid="opposizione-ts-check"
                    type="checkbox" checked={opposizioneTS}
                    onChange={(e) => setOpposizioneTS(e.target.checked)}
                    className="mt-0.5 accent-[#0A0A0A]"
                  />
                  <span>
                    <strong>Mi oppongo</strong> alla trasmissione dei dati di questa fattura al <em>Sistema Tessera Sanitaria</em> (art. 3 D.M. 31/07/2015).
                    <br />
                    <span className="text-[#0A0A0A]/55">In caso di opposizione, non potrai detrarre la spesa nel 730 precompilato — potrai comunque farlo tramite il modello 730 ordinario allegando la fattura.</span>
                  </span>
                </label>

                <button
                  data-testid="booking-pay-submit"
                  type="button"
                  onClick={handlePayment}
                  disabled={loading}
                  className="mt-6 w-full inline-flex items-center justify-center gap-3 px-6 py-4 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg"
                >
                  {loading ? "Elaborazione..." : `Continua · €${terapista.prezzo_sessione || 90}`}
                </button>
                <p className="mt-3 text-center text-[10px] text-[#0A0A0A]/50">
                  Per sicurezza ti chiederemo un codice SMS prima del pagamento.
                </p>
              </div>
            )}

            {/* SMS OTP (post-payment, pre-confirmation) */}
            {step === "sms-otp" && (
              <div data-testid="step-sms-otp">
                <h2 className="font-serif text-3xl text-[#0A0A0A] leading-tight">Verifica il tuo numero</h2>
                <p className="mt-2 text-sm text-[#0A0A0A]/70">
                  Abbiamo inviato un codice SMS a <strong className="text-[#0A0A0A]">{smsPhone}</strong>.
                  Serve a confermare la tua identità prima di finalizzare la prenotazione.
                </p>

                {smsOtpDev && (
                  <div className="mt-4 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl text-amber-300/80 text-xs">
                    <strong>Modalità dev:</strong> codice SMS fallback: <code className="font-mono text-amber-200">{smsOtpDev}</code>
                  </div>
                )}

                <form onSubmit={handleSmsVerifyAndBook} className="mt-6 space-y-4">
                  <div>
                    <label className="block text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/60 mb-2">Codice SMS</label>
                    <div className="relative">
                      <Smartphone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#0A0A0A]/40" />
                      <input
                        data-testid="sms-otp-input"
                        required inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                        value={smsOtp}
                        onChange={(e) => setSmsOtp(e.target.value.replace(/\D/g, ""))}
                        placeholder="123456"
                        className="w-full pl-10 pr-4 py-3 bg-white border border-[#0A0A0A]/15 rounded-xl text-[#0A0A0A] text-center text-xl tracking-[0.5em] focus:outline-none focus:border-[#0A0A0A]"
                      />
                    </div>
                  </div>

                  <label className="flex items-start gap-3 text-xs text-[#0A0A0A]/80 leading-relaxed cursor-pointer">
                    <input
                      data-testid="sms-privacy-check"
                      type="checkbox" checked={smsPrivacy}
                      onChange={(e) => setSmsPrivacy(e.target.checked)}
                      className="mt-0.5 accent-[#0A0A0A]"
                    />
                    <span>
                      Acconsento al trattamento dei miei dati personali (inclusi dati sanitari — categoria speciale, art. 9 GDPR)
                      per la finalità di erogazione della prestazione psicologica e dichiaro di aver letto la
                      <a href="/privacy" target="_blank" rel="noreferrer" className="text-[#0A0A0A] hover:underline"> Privacy Policy</a>.
                    </span>
                  </label>

                  <button
                    data-testid="sms-verify-submit"
                    type="submit" disabled={loading}
                    className="w-full inline-flex items-center justify-center gap-3 px-6 py-4 disabled:opacity-40 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg"
                  >
                    {loading ? "Verifica in corso..." : "Verifica e conferma prenotazione"}
                  </button>

                  <button
                    type="button"
                    data-testid="sms-resend"
                    onClick={handleResendSms}
                    disabled={loading}
                    className="w-full text-center text-xs text-[#0A0A0A]/60 hover:text-[#0A0A0A] py-2"
                  >
                    Non hai ricevuto il codice? Invialo di nuovo
                  </button>
                </form>
              </div>
            )}

            {/* SUCCESS */}
            {step === "success" && (
              <div data-testid="step-success" className="text-center py-8">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", duration: 0.6 }}
                  className="w-20 h-20 mx-auto rounded-full bg-white/30 flex items-center justify-center mb-8"
                >
                  <Check className="w-10 h-10 text-[#0A0A0A]" strokeWidth={2.5} />
                </motion.div>
                <h2 className="font-serif text-4xl text-[#0A0A0A]">Prenotazione confermata</h2>
                <p className="mt-4 text-[#0A0A0A]/70 max-w-sm mx-auto leading-relaxed">
                  Ti abbiamo inviato un&apos;email di conferma con tutti i dettagli.
                  Il Dr. {terapista.cognome} ti aspetta il <strong className="text-[#0A0A0A]">{formatSlot(slot.data_ora)}</strong>.
                </p>
                <p className="mt-3 text-xs text-[#0A0A0A]/40">
                  Puoi chiudere questa finestra.
                </p>
                <button
                  data-testid="booking-close-success"
                  onClick={onClose}
                  className="mt-10 inline-flex items-center gap-3 px-8 py-3 border border-[#0A0A0A]/20 text-[#0A0A0A] hover:bg-white/5 rounded-full text-sm tracking-wide"
                >
                  Chiudi
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
