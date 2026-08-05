import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Smartphone, Share, Plus, Download, MonitorSmartphone,
  BookHeart, Calendar, MessageCircle, ShieldCheck, ArrowRight,
  Chrome, Apple
} from "lucide-react";

// Zero-dependency QR: use qrserver.com public API. Cheap, cacheable, no npm dep.
const APP_URL = "https://www.funzionabene.it";
const QR_URL = `https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(APP_URL)}&size=280x280&bgcolor=F4F1ED&color=0A0A0A&margin=10&qzone=2`;

export default function ScaricaAppPage() {
  const [platform, setPlatform] = useState("desktop");

  useEffect(() => {
    const ua = navigator.userAgent || "";
    if (/iPhone|iPad|iPod/i.test(ua)) setPlatform("ios");
    else if (/Android/i.test(ua)) setPlatform("android");
    else setPlatform("desktop");
  }, []);

  const install = () => {
    // Try to trigger PWA install if event was captured earlier
    const evt = window.__deferredPWAPrompt;
    if (evt && evt.prompt) {
      evt.prompt();
    } else {
      alert("Apri Funzionabene sul tuo smartphone o cerca l'opzione 'Installa app' nel menu del browser.");
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F1ED]" data-testid="scarica-app-page">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[#F58A1F] via-[#F5A419] to-[#F5D419] px-6 py-16 sm:py-24">
        <div className="absolute -right-16 -top-16 w-72 h-72 bg-white/10 rounded-full blur-3xl" />
        <div className="max-w-4xl mx-auto relative">
          <div className="flex items-center gap-2 text-[#0A0A0A]/70 text-xs uppercase tracking-widest font-medium">
            <Smartphone className="w-3.5 h-3.5" /> App Funzionabene
          </div>
          <h1 className="text-4xl sm:text-6xl font-bold text-[#0A0A0A] font-[Outfit] mt-3 leading-[1.05]">
            Porta il tuo terapeuta<br />in tasca.
          </h1>
          <p className="text-lg text-[#0A0A0A]/70 mt-4 max-w-xl leading-relaxed">
            Funzionabene è una web app: <strong>nessuno store, nessun download da 100&nbsp;MB</strong>. La installi in 3 secondi e la usi come un&apos;app vera.
          </p>
          <div className="flex flex-wrap gap-3 mt-8">
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-[#0A0A0A]/90 text-white rounded-full text-xs font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-[#F5D419]" /> Sicura · Criptata · GDPR
            </span>
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 text-[#0A0A0A] rounded-full text-xs font-medium">
              <Apple className="w-3.5 h-3.5" /> iOS
            </span>
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 text-[#0A0A0A] rounded-full text-xs font-medium">
              <Smartphone className="w-3.5 h-3.5" /> Android
            </span>
            <span className="inline-flex items-center gap-2 px-4 py-2 bg-white/60 text-[#0A0A0A] rounded-full text-xs font-medium">
              <MonitorSmartphone className="w-3.5 h-3.5" /> Desktop
            </span>
          </div>
        </div>
      </section>

      {/* Two-column install area */}
      <section className="px-6 -mt-8 relative z-10 pb-16">
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-6">
          {/* Mobile install (dynamic per platform) */}
          <div className="bg-white rounded-3xl p-6 shadow-xl">
            <div className="flex items-center gap-2 text-xs font-medium text-[#0A0A0A]/55 uppercase tracking-widest mb-1">
              <Smartphone className="w-3.5 h-3.5" /> Su smartphone
            </div>
            <h2 className="text-2xl font-bold text-[#0A0A0A] font-[Outfit] mb-4">Installa in un tap</h2>

            {platform === "ios" && (
              <div className="space-y-3" data-testid="install-instructions-ios">
                <Step n={1} icon={<Share className="w-4 h-4 text-[#007AFF]" />} title="Tap sull'icona Condividi" body="In basso al centro della barra di Safari." />
                <Step n={2} icon={<Plus className="w-4 h-4" />} title="Aggiungi a Home" body="Scorri e scegli questa opzione." />
                <Step n={3} icon={<Download className="w-4 h-4 text-[#F58A1F]" />} title="Tocca Aggiungi" body="In alto a destra. L'icona apparirà sulla schermata Home." />
              </div>
            )}
            {platform === "android" && (
              <div className="space-y-3" data-testid="install-instructions-android">
                <Step n={1} icon={<Chrome className="w-4 h-4" />} title="Tocca il menù ⋮ di Chrome" body="In alto a destra del browser." />
                <Step n={2} icon={<Download className="w-4 h-4 text-[#F58A1F]" />} title="Installa app" body="Scegli 'Installa app' oppure 'Aggiungi a schermata Home'." />
                <Step n={3} icon={<Smartphone className="w-4 h-4 text-emerald-600" />} title="Fatto!" body="Funzionabene apparirà come una vera app." />
                <button
                  onClick={install}
                  data-testid="install-app-btn"
                  className="mt-4 w-full py-3 rounded-full bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] font-semibold inline-flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" /> Installa ora
                </button>
              </div>
            )}
            {platform === "desktop" && (
              <div className="space-y-3" data-testid="install-instructions-desktop">
                <p className="text-sm text-[#0A0A0A]/70 leading-relaxed">
                  Sei su computer? Scansiona il QR con il tuo smartphone per aprire l&apos;app e installarla.
                </p>
                <div className="mt-3 flex flex-col items-center gap-3 py-6 bg-[#F4F1ED] rounded-2xl">
                  <img
                    src={QR_URL}
                    alt="QR code per installare Funzionabene"
                    className="w-56 h-56 rounded-2xl"
                    data-testid="install-qr"
                  />
                  <div className="text-xs text-[#0A0A0A]/60 font-mono">funzionabene.it</div>
                </div>
              </div>
            )}
          </div>

          {/* What you get */}
          <div className="bg-[#0A0A0A] text-white rounded-3xl p-6 shadow-xl">
            <div className="text-xs font-medium text-[#F5D419] uppercase tracking-widest mb-2">Cosa avrai</div>
            <h2 className="text-2xl font-bold font-[Outfit] mb-5">Il tuo compagno di percorso</h2>
            <ul className="space-y-4">
              <Feature icon={<Calendar className="w-4 h-4" />} title="I tuoi appuntamenti, ovunque" body="Promemoria, riprogrammazione, accesso video — in tre tap." />
              <Feature icon={<BookHeart className="w-4 h-4" />} title="Diario emozionale" body="Note brevi che il tuo terapeuta legge prima della sessione, se vuoi." />
              <Feature icon={<MessageCircle className="w-4 h-4" />} title="Chat con il terapeuta" body="Messaggi diretti tra una sessione e l'altra." />
              <Feature icon={<ShieldCheck className="w-4 h-4" />} title="Riservatezza assoluta" body="Cifratura end-to-end, GDPR, dati in Europa." />
            </ul>
            <Link
              to="/registrati"
              data-testid="signup-cta"
              className="mt-6 inline-flex items-center gap-2 px-5 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] rounded-full font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              Crea il tuo account gratis <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* FAQ */}
        <div className="max-w-3xl mx-auto mt-16">
          <h3 className="text-2xl font-bold text-[#0A0A0A] font-[Outfit] mb-6">Domande frequenti</h3>
          <div className="space-y-3">
            <FAQ q="Perché non è nello store Apple o Google?"
                 a="Funzionabene è una progressive web app: nessuna installazione da 100 MB, nessun aggiornamento manuale, nessun tracciamento. Ti aggiorni in automatico quando apri l'app." />
            <FAQ q="Serve internet per usarla?"
                 a="Sì per prenotare, videoconsulto e chat. Il diario emozionale funziona anche offline: sincronizza appena torni online." />
            <FAQ q="I miei dati sono al sicuro?"
                 a="Tutto è cifrato in transito e a riposo, ospitato in Europa. Rispettiamo il GDPR e usiamo il framework legale della sanità italiana." />
            <FAQ q="Come rimuovo l'app?"
                 a="Come una qualunque app: tieni premuto sull'icona → Rimuovi. I tuoi dati restano sul tuo account, li ritrovi al prossimo accesso." />
          </div>
        </div>
      </section>
    </div>
  );
}

function Step({ n, icon, title, body }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-7 h-7 rounded-full bg-[#0A0A0A] text-white flex items-center justify-center text-xs font-bold flex-shrink-0">{n}</div>
      <div className="flex-1">
        <div className="text-sm font-medium text-[#0A0A0A] flex items-center gap-2">
          {icon}<span>{title}</span>
        </div>
        <p className="text-xs text-[#0A0A0A]/60 mt-0.5">{body}</p>
      </div>
    </div>
  );
}

function Feature({ icon, title, body }) {
  return (
    <li className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-xl bg-white/10 flex items-center justify-center text-[#F5D419] flex-shrink-0">{icon}</div>
      <div>
        <div className="text-sm font-semibold">{title}</div>
        <p className="text-xs text-white/60 mt-0.5 leading-relaxed">{body}</p>
      </div>
    </li>
  );
}

function FAQ({ q, a }) {
  return (
    <details className="bg-white rounded-2xl p-4 group cursor-pointer">
      <summary className="text-sm font-medium text-[#0A0A0A] flex items-center justify-between gap-2 list-none">
        <span>{q}</span>
        <span className="text-[#0A0A0A]/40 group-open:rotate-180 transition-transform">▾</span>
      </summary>
      <p className="text-sm text-[#0A0A0A]/70 mt-3 leading-relaxed">{a}</p>
    </details>
  );
}
