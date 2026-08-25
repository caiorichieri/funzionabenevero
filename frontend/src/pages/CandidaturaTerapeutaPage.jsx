import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { Mail, User, Phone, MessageSquare, CheckCircle2 } from "lucide-react";
import Mascotte from "@/components/shared/Mascotte";

/**
 * Public therapist application form (no auth, no password).
 * Captures name, surname, email, phone + optional message.
 * Backend saves as `approval_status: "lead"` and emails admin.
 * The applicant is contacted manually by the team.
 */
export default function CandidaturaTerapeutaPage() {
  const [form, setForm] = useState({ nome: "", cognome: "", email: "", telefono: "", messaggio: "" });
  const [privacyOk, setPrivacyOk] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!privacyOk) { setError("Devi accettare l'informativa Privacy per proseguire."); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/terapeuti/candidatura`, {
        nome: form.nome.trim(),
        cognome: form.cognome.trim(),
        email: form.email.trim(),
        telefono: form.telefono.trim(),
        messaggio: form.messaggio.trim() || null,
      });
      setSuccess(true);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === "string" ? d : "Errore durante l'invio della candidatura");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-transparent flex items-center justify-center p-6">
        <div
          data-testid="candidatura-success"
          className="w-full max-w-md text-center bg-white/40 backdrop-blur-sm border border-[#0A0A0A]/10 rounded-3xl p-10"
        >
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2 className="w-9 h-9 text-green-600" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit] mb-3">
            Candidatura ricevuta
          </h1>
          <p className="text-[#0A0A0A]/70 leading-relaxed">
            Grazie <strong className="text-[#0A0A0A]">{form.nome}</strong>. Il nostro team esaminerà
            la tua candidatura e ti contatterà entro <strong>2 giorni lavorativi</strong> al numero{" "}
            <strong>{form.telefono}</strong>.
          </p>
          <p className="text-sm text-[#0A0A0A]/50 mt-4">
            Nel frattempo, se hai domande, scrivi a{" "}
            <a href="mailto:hr@funzionabene.it" className="underline">hr@funzionabene.it</a>.
          </p>
          <Link
            to="/"
            data-testid="back-to-home"
            className="inline-block mt-8 px-6 py-3 rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white font-medium transition-colors"
          >
            Torna alla home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-transparent flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Mascotte name="saltitante" theme="light" size={90} animation="wiggle" />
          </div>
          <h1 className="text-3xl font-bold text-[#0A0A0A] font-[Outfit]">Unisciti al team</h1>
          <p className="text-[#0A0A0A]/65 mt-2 text-sm leading-relaxed">
            Lascia i tuoi dati e il nostro team ti contatterà per verificare i requisiti,
            i documenti e completare l&apos;attivazione del tuo profilo.
          </p>
        </div>

        {error && (
          <div
            data-testid="candidatura-error"
            className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Nome</label>
              <input
                data-testid="candidatura-nome"
                type="text" required value={form.nome} onChange={update("nome")}
                placeholder="Mario"
                className="w-full px-3 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Cognome</label>
              <input
                data-testid="candidatura-cognome"
                type="text" required value={form.cognome} onChange={update("cognome")}
                placeholder="Rossi"
                className="w-full px-3 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Email professionale</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
              <input
                data-testid="candidatura-email"
                type="email" required value={form.email} onChange={update("email")}
                placeholder="dott.rossi@studio.it"
                className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">Telefono</label>
            <div className="relative">
              <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-[#0A0A0A]/50 w-5 h-5" />
              <input
                data-testid="candidatura-telefono"
                type="tel" required value={form.telefono} onChange={update("telefono")}
                placeholder="+39 351 1234567"
                className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#0A0A0A] mb-1">
              Messaggio <span className="text-[#0A0A0A]/45 font-normal">(facoltativo)</span>
            </label>
            <div className="relative">
              <MessageSquare className="absolute left-3 top-3 text-[#0A0A0A]/50 w-5 h-5" />
              <textarea
                data-testid="candidatura-messaggio"
                value={form.messaggio} onChange={update("messaggio")}
                rows={3}
                maxLength={800}
                placeholder="Specializzazione, anni di esperienza, disponibilità..."
                className="w-full pl-10 pr-4 py-3 border border-[#0A0A0A]/15 rounded-xl bg-white text-[#0A0A0A] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A] resize-none"
              />
            </div>
            <div className="text-xs text-[#0A0A0A]/45 text-right mt-1">
              {form.messaggio.length}/800
            </div>
          </div>

          <label
            className="flex items-start gap-2.5 cursor-pointer text-sm text-[#0A0A0A]/80"
            data-testid="candidatura-privacy-wrapper"
          >
            <input
              data-testid="candidatura-privacy"
              type="checkbox"
              checked={privacyOk}
              onChange={() => setPrivacyOk((v) => !v)}
              className="mt-1 accent-[#0A0A0A]"
              required
            />
            <span>
              <span className="text-red-600">*</span> Ho letto l&apos;
              <Link to="/privacy-visitatori" target="_blank" className="underline hover:text-[#0A0A0A]">
                Informativa Privacy
              </Link>{" "}
              e autorizzo il trattamento dei dati per finalità di selezione (art. 6.1.b GDPR).
            </span>
          </label>

          <button
            data-testid="candidatura-submit"
            type="submit" disabled={loading}
            className="w-full py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg transition-colors disabled:opacity-50 font-[Outfit]"
          >
            {loading ? "Invio in corso..." : "Invia candidatura"}
          </button>
        </form>

        <div className="mt-6 space-y-2 text-center text-sm text-[#0A0A0A]/65">
          <p>
            Sei un paziente?{" "}
            <Link data-testid="candidatura-to-register" to="/registrati" className="text-[#0A0A0A] font-medium hover:text-[#0A0A0A]/70">
              Registrati qui
            </Link>
          </p>
          <p>
            Hai già un account?{" "}
            <Link data-testid="candidatura-to-login" to="/login" className="text-[#0A0A0A] font-medium hover:text-[#0A0A0A]/70">
              Accedi
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
