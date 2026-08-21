import { Check } from "lucide-react";

/**
 * StepHeader — numbered step header used by onboarding wizard steps.
 * When `done` is true, shows a green check instead of the number.
 */
export default function StepHeader({ number, title, done }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
          done ? "bg-green-100 text-green-700" : "bg-white/30 text-[#0A0A0A]"
        }`}
      >
        {done ? <Check className="w-4 h-4" /> : number}
      </div>
      <h3 className="font-semibold text-[#0A0A0A] font-[Outfit]">{title}</h3>
    </div>
  );
}
