import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API } from "@/contexts/AuthContext";
import { ShieldCheck, Check, AlertCircle } from "lucide-react";
import DocumentsStep, { DOC_TYPES } from "@/components/therapist/onboarding/DocumentsStep";
import PhoneVerifyStep from "@/components/therapist/onboarding/PhoneVerifyStep";
import DprStep from "@/components/therapist/onboarding/DprStep";

/**
 * OnboardingSection — orchestrates the 3-step therapist onboarding wizard:
 *  1) Upload professional documents
 *  2) Verify phone via SMS OTP
 *  3) Sign DPR 445/2000 self-certification
 * Owns all state; delegates rendering to focused step components.
 */
export default function OnboardingSection({ profilo, currentUser, onRefresh }) {
  const [docs, setDocs] = useState({});
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [uploading, setUploading] = useState({});
  const [error, setError] = useState("");

  // SMS OTP
  const [smsPhone, setSmsPhone] = useState(currentUser?.telefono || "");
  const [smsOtp, setSmsOtp] = useState("");
  const [smsOtpDev, setSmsOtpDev] = useState("");
  const [smsSending, setSmsSending] = useState(false);
  const [smsStep, setSmsStep] = useState("phone");
  const phoneVerified = Boolean(currentUser?.telefono_verificato);

  // DPR 445
  const [dprChecked, setDprChecked] = useState(false);
  const [dprSigning, setDprSigning] = useState(false);

  const fetchDocs = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const r = await axios.get(`${API}/terapisti/me/documenti`, { withCredentials: true });
      setDocs(r.data?.documenti || {});
    } catch (e) {
      if (process.env.NODE_ENV !== "production") {
        console.error("[OnboardingSection] fetchDocs failed:", e);
      }
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);
  useEffect(() => {
    setSmsPhone(currentUser?.telefono || "");
    if (currentUser?.telefono_verificato) setSmsStep("done");
  }, [currentUser?.telefono, currentUser?.telefono_verificato]);

  const readErr = (err, fallback) => {
    const d = err.response?.data?.detail;
    return typeof d === "string" ? d : fallback;
  };

  const handleUpload = async (tipo, file) => {
    if (!file) return;
    setError("");
    setUploading((u) => ({ ...u, [tipo]: true }));
    try {
      const fd = new FormData();
      fd.append("file", file);
      await axios.post(`${API}/terapisti/me/documenti/${tipo}`, fd, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      await fetchDocs();
    } catch (err) {
      setError(readErr(err, "Errore caricamento documento"));
    } finally {
      setUploading((u) => ({ ...u, [tipo]: false }));
    }
  };

  const handleSmsSend = async () => {
    setError("");
    if (!smsPhone || smsPhone.length < 8) { setError("Numero non valido"); return; }
    setSmsSending(true);
    try {
      const r = await axios.post(
        `${API}/sms/send-otp`,
        { phone: smsPhone, context: "verifica-terapeuta" },
        { withCredentials: true }
      );
      setSmsOtpDev(r.data?.otp_dev || "");
      setSmsStep("code");
    } catch (err) {
      setError(readErr(err, "Errore invio SMS"));
    } finally {
      setSmsSending(false);
    }
  };

  const handleSmsVerify = async () => {
    setError("");
    setSmsSending(true);
    try {
      await axios.post(
        `${API}/sms/verify-otp`,
        { phone: smsPhone, otp_code: smsOtp },
        { withCredentials: true }
      );
      setSmsStep("done");
      onRefresh && onRefresh();
    } catch (err) {
      setError(readErr(err, "Codice SMS non valido"));
    } finally {
      setSmsSending(false);
    }
  };

  const allDocsUploaded = DOC_TYPES.every((d) => docs[d.key]);
  const alreadySigned = Boolean(profilo?.autocertificazione_dpr445 || profilo?.autocertificazione_firmata);
  const canSignDpr = allDocsUploaded && phoneVerified && dprChecked && !alreadySigned;

  const handleSignDpr = async () => {
    setError("");
    setDprSigning(true);
    try {
      await axios.post(`${API}/terapisti/me/autocertificazione-dpr445`, {}, { withCredentials: true });
      // After the final signature, tell the backend that onboarding is complete so the admin
      // gets notified via email. Best-effort — if this fails the therapist is still signed.
      try {
        await axios.post(`${API}/terapisti/me/onboarding-completato`, {}, { withCredentials: true });
      } catch (e) {
        // Backend enforces the same guards; silently ignore validation errors here.
      }
      onRefresh && onRefresh();
    } catch (err) {
      setError(readErr(err, "Errore firma autocertificazione"));
    } finally {
      setDprSigning(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="therapist-onboarding">
      {/* Intro card */}
      <div className="rounded-2xl border border-[#0A0A0A]/10 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <ShieldCheck
            className={`w-7 h-7 flex-shrink-0 mt-0.5 ${alreadySigned ? "text-green-600" : "text-[#0A0A0A]"}`}
          />
          <div className="flex-1">
            <h3 className="font-semibold text-[#0A0A0A] font-[Outfit] text-lg">
              {alreadySigned ? "Profilo verificato" : "Verifica profilo professionista"}
            </h3>
            <p className="text-sm text-[#0A0A0A]/65 mt-1">
              {alreadySigned
                ? "Hai completato tutti i passi richiesti. In attesa di verifica documenti da parte dell'amministratore per diventare pubblicamente visibile."
                : "Per essere visibile ai pazienti, carica i documenti, verifica il numero e firma l'autocertificazione (DPR 445/2000)."}
            </p>
            {profilo?.documenti_verificati && (
              <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-50 border border-green-200 text-green-700 text-xs font-medium">
                <Check className="w-3.5 h-3.5" /> Documenti verificati dall&apos;amministratore ·
                Profilo pubblico attivo
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div
          data-testid="onboarding-error"
          className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-start gap-2"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" /> <span>{error}</span>
        </div>
      )}

      <DocumentsStep
        docs={docs}
        uploading={uploading}
        loading={loadingDocs}
        onUpload={handleUpload}
        allDocsUploaded={allDocsUploaded}
      />

      <PhoneVerifyStep
        phoneVerified={phoneVerified}
        smsStep={smsStep}
        smsPhone={smsPhone}
        smsOtp={smsOtp}
        smsOtpDev={smsOtpDev}
        smsSending={smsSending}
        currentUser={currentUser}
        onPhoneChange={setSmsPhone}
        onOtpChange={setSmsOtp}
        onSend={handleSmsSend}
        onVerify={handleSmsVerify}
        onChangeNumber={() => { setSmsStep("phone"); setSmsOtp(""); }}
      />

      <DprStep
        alreadySigned={alreadySigned}
        dprChecked={dprChecked}
        onDprCheck={setDprChecked}
        canSignDpr={canSignDpr}
        dprSigning={dprSigning}
        onSign={handleSignDpr}
        allDocsUploaded={allDocsUploaded}
        phoneVerified={phoneVerified}
        profilo={profilo}
      />
    </div>
  );
}
