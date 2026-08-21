import { Smartphone } from "lucide-react";
import StepHeader from "@/components/therapist/onboarding/StepHeader";

/**
 * PhoneVerifyStep — Step 2: verify therapist's phone number via SMS OTP.
 * Presentational; parent controls `smsStep` ('phone' | 'code' | 'done') and handlers.
 */
export default function PhoneVerifyStep({
  phoneVerified,
  smsStep,
  smsPhone,
  smsOtp,
  smsOtpDev,
  smsSending,
  currentUser,
  onPhoneChange,
  onOtpChange,
  onSend,
  onVerify,
  onChangeNumber,
}) {
  return (
    <div className="rounded-2xl border border-[#0A0A0A]/10 bg-white p-6 shadow-sm">
      <StepHeader number="2" title="Verifica il tuo numero di telefono" done={phoneVerified} />

      {phoneVerified ? (
        <div className="text-sm text-[#0A0A0A]/75 flex items-center gap-2">
          <Smartphone className="w-4 h-4 text-green-600" />
          Numero verificato:{" "}
          <strong className="text-[#0A0A0A]">{currentUser?.telefono || smsPhone}</strong>
        </div>
      ) : smsStep === "phone" ? (
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            data-testid="onb-sms-phone"
            type="tel"
            value={smsPhone}
            onChange={(e) => onPhoneChange(e.target.value)}
            placeholder="+39 351 1234567"
            className="flex-1 px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
          />
          <button
            data-testid="onb-sms-send"
            type="button"
            disabled={smsSending}
            onClick={onSend}
            className="px-5 py-2.5 text-sm font-medium rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white transition-colors disabled:opacity-50"
          >
            {smsSending ? "Invio..." : "Invia codice SMS"}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="text-sm text-[#0A0A0A]/75">
            Codice inviato a <strong className="text-[#0A0A0A]">{smsPhone}</strong>.
            {smsOtpDev && (
              <span className="block mt-1 text-amber-700 text-xs bg-amber-50 border border-amber-200 rounded-lg px-2 py-1 inline-block">
                Dev fallback: <code className="font-mono">{smsOtpDev}</code>
              </span>
            )}
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              data-testid="onb-sms-code"
              inputMode="numeric"
              maxLength={6}
              value={smsOtp}
              onChange={(e) => onOtpChange(e.target.value.replace(/\D/g, ""))}
              placeholder="123456"
              className="flex-1 px-3 py-2.5 border border-[#0A0A0A]/15 rounded-xl text-sm text-center tracking-[0.4em] focus:outline-none focus:ring-2 focus:ring-[#0A0A0A]"
            />
            <button
              data-testid="onb-sms-verify"
              type="button"
              disabled={smsSending}
              onClick={onVerify}
              className="px-5 py-2.5 text-sm font-medium rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white transition-colors disabled:opacity-50"
            >
              {smsSending ? "Verifica..." : "Verifica"}
            </button>
            <button
              type="button"
              onClick={onChangeNumber}
              className="px-3 py-2.5 text-xs text-[#0A0A0A]/55 hover:text-[#0A0A0A]"
            >
              Cambia numero
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
