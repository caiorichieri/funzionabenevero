import StepHeader from "@/components/therapist/onboarding/StepHeader";

/**
 * DprStep — Step 3: sign the DPR 445/2000 self-certification.
 * Enabled only when documents uploaded + phone verified.
 */
export default function DprStep({
  alreadySigned,
  dprChecked,
  onDprCheck,
  canSignDpr,
  dprSigning,
  onSign,
  allDocsUploaded,
  phoneVerified,
  profilo,
}) {
  return (
    <div className="rounded-2xl border border-[#0A0A0A]/10 bg-white p-6 shadow-sm">
      <StepHeader
        number="3"
        title="Autocertificazione (DPR 445/2000)"
        done={alreadySigned}
      />

      {alreadySigned ? (
        <div className="text-sm text-[#0A0A0A]/75">
          Hai firmato l&apos;autocertificazione il{" "}
          <strong className="text-[#0A0A0A]">
            {profilo?.autocertificazione_data
              ? new Date(profilo.autocertificazione_data).toLocaleDateString("it-IT")
              : "—"}
          </strong>
          .
        </div>
      ) : (
        <>
          <label className="flex items-start gap-3 text-sm text-[rgba(28,28,28,0.75)] leading-relaxed cursor-pointer">
            <input
              data-testid="dpr445-checkbox"
              type="checkbox"
              checked={dprChecked}
              onChange={(e) => onDprCheck(e.target.checked)}
              disabled={!allDocsUploaded || !phoneVerified}
              className="mt-0.5 accent-[#0A0A0A]"
            />
            <span>
              Il sottoscritto, consapevole delle sanzioni penali previste dall&apos;
              <strong>art. 76 del DPR 28 dicembre 2000, n. 445</strong>, per le ipotesi di falsità in
              atti e dichiarazioni mendaci, dichiara sotto la propria responsabilità che i dati e i
              documenti caricati (CV, assicurazione professionale, laurea/abilitazione) sono{" "}
              <strong>veritieri, completi e corrispondenti al vero</strong>. Autorizzo FunzionaBene
              alla verifica dei dati ai sensi della normativa vigente.
            </span>
          </label>

          {(!allDocsUploaded || !phoneVerified) && (
            <div className="mt-3 text-xs text-[#0A0A0A]/55">
              {!allDocsUploaded && <div>• Prima carica tutti i documenti richiesti</div>}
              {!phoneVerified && <div>• Prima verifica il tuo numero di telefono via SMS</div>}
            </div>
          )}

          <button
            data-testid="dpr445-sign"
            type="button"
            disabled={!canSignDpr || dprSigning}
            onClick={onSign}
            className="mt-4 px-5 py-2.5 text-sm font-medium rounded-full bg-[#0A0A0A] hover:bg-[#1C1C1C] text-white transition-colors disabled:opacity-50"
          >
            {dprSigning ? "Firma in corso..." : "Firma autocertificazione"}
          </button>
        </>
      )}
    </div>
  );
}
