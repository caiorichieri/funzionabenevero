import { Link } from "react-router-dom";
import { ArrowLeft, FileText } from "lucide-react";

export default function LegalLayout({ title, lastUpdate, children, testId }) {
  return (
    <main className="min-h-[calc(100vh-80px)] bg-transparent py-16 lg:py-24" data-testid={testId}>
      <article className="max-w-3xl mx-auto px-6 lg:px-10">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-[#0A0A0A]/60 hover:text-[#0A0A0A] mb-10 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Torna alla home
        </Link>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-11 h-11 rounded-full bg-white/30 flex items-center justify-center">
            <FileText className="w-5 h-5 text-[#0A0A0A]" />
          </div>
          <span className="text-[#0A0A0A] text-xs tracking-[0.25em] uppercase">Informativa legale</span>
        </div>

        <h1 className="font-serif text-4xl lg:text-5xl text-[#0A0A0A] leading-tight">{title}</h1>
        {lastUpdate && (
          <p className="mt-3 text-xs tracking-[0.15em] uppercase text-[#0A0A0A]/50">
            Ultimo aggiornamento: {lastUpdate}
          </p>
        )}

        <div className="mt-12 prose prose-invert max-w-none text-[#0A0A0A]/75 leading-relaxed [&_h2]:font-serif [&_h2]:text-2xl [&_h2]:text-[#0A0A0A] [&_h2]:mt-10 [&_h2]:mb-3 [&_h3]:text-[#0A0A0A] [&_h3]:text-xs [&_h3]:tracking-[0.15em] [&_h3]:uppercase [&_h3]:mt-6 [&_h3]:mb-2 [&_p]:mb-4 [&_p]:text-base [&_ul]:mb-4 [&_ul]:pl-6 [&_ul]:list-disc [&_li]:mb-2 [&_strong]:text-[#0A0A0A] [&_a]:text-[#0A0A0A] [&_a]:underline">
          {children}
        </div>

        <div className="mt-16 pt-8 border-t border-[#0A0A0A]/10 text-xs text-[#0A0A0A]/50">
          <p>
            Per domande su questa informativa: <a href="mailto:privacy@bidoc.it" className="text-[#0A0A0A] hover:text-[#0A0A0A]/70">privacy@bidoc.it</a>
          </p>
        </div>
      </article>
    </main>
  );
}
