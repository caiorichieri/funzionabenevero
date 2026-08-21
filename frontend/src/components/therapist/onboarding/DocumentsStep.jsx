import { useRef } from "react";
import { Upload, FileCheck2 } from "lucide-react";
import StepHeader from "@/components/therapist/onboarding/StepHeader";

export const DOC_TYPES = [
  { key: "cv", label: "Curriculum Vitae", hint: "CV aggiornato (PDF/JPG/PNG — max 10MB)" },
  { key: "assicurazione", label: "Assicurazione Professionale", hint: "Polizza RC o dichiarazione della compagnia" },
  { key: "laurea", label: "Laurea / Abilitazione", hint: "Diploma di laurea o certificato di abilitazione" },
];

/**
 * DocumentsStep — Step 1: upload three required professional documents.
 * Fully controlled; parent owns `docs` state and passes `onUpload(tipo, file)`.
 */
export default function DocumentsStep({ docs, uploading, loading, onUpload, allDocsUploaded }) {
  const fileRefs = useRef({});

  return (
    <div className="rounded-2xl border border-[#0A0A0A]/10 bg-white p-6 shadow-sm">
      <StepHeader number="1" title="Carica i tuoi documenti" done={allDocsUploaded} />
      {loading ? (
        <div className="text-sm text-[#0A0A0A]/55">Caricamento...</div>
      ) : (
        <div className="space-y-3">
          {DOC_TYPES.map((d) => {
            const meta = docs[d.key];
            const isUp = uploading[d.key];
            return (
              <div
                key={d.key}
                className="flex items-center gap-3 p-3 rounded-xl border border-[#0A0A0A]/10 bg-[#E9D628]"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm font-medium text-[#0A0A0A]">
                    {meta ? (
                      <FileCheck2 className="w-4 h-4 text-green-600" />
                    ) : (
                      <Upload className="w-4 h-4 text-[#0A0A0A]/50" />
                    )}
                    {d.label}
                  </div>
                  <div className="text-xs text-[rgba(28,28,28,0.55)] mt-0.5 truncate">
                    {meta ? `${meta.filename} · ${(meta.size / 1024).toFixed(1)} KB` : d.hint}
                  </div>
                </div>
                <input
                  ref={(el) => { fileRefs.current[d.key] = el; }}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  className="hidden"
                  data-testid={`doc-file-${d.key}`}
                  onChange={(e) => onUpload(d.key, e.target.files?.[0])}
                />
                <button
                  type="button"
                  disabled={isUp}
                  data-testid={`doc-upload-${d.key}`}
                  onClick={() => fileRefs.current[d.key]?.click()}
                  className="px-3 py-1.5 text-xs font-medium rounded-full border border-[#0A0A0A] text-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white transition-colors disabled:opacity-50"
                >
                  {isUp ? "Carico..." : meta ? "Sostituisci" : "Carica"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
