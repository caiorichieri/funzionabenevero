import { useState, useEffect } from "react";
import { Cookie, ShieldCheck, BarChart3, Megaphone, Settings2, X } from "lucide-react";
import { applyConsent, initGoogleConsentDefaults } from "@/utils/cookieLoader";
import axios from "axios";
import { API } from "@/contexts/AuthContext";

const STORAGE_KEY = "funzionabene_cookie_consent_v1";
const COOKIE_POLICY_URL = "/cookie-policy";

const DEFAULT_PREFS = {
  necessari: true,       // always on
  statistica: false,
  esperienza: false,
  marketing: false,
};

const CATEGORIES = [
  {
    key: "necessari", label: "Necessari",
    desc: "Cookie strettamente indispensabili per il funzionamento del sito (autenticazione, sicurezza, pagamenti Stripe, prevenzione frodi Cloudflare). Non richiedono consenso ex art. 122 Codice Privacy.",
    icon: ShieldCheck, disabled: true, alwaysOn: true,
  },
  {
    key: "statistica", label: "Statistica",
    desc: "Google Analytics 4 con IP anonimizzato + Microsoft Clarity. Ci aiutano a capire come migliorare il sito.",
    icon: BarChart3,
  },
  {
    key: "esperienza", label: "Esperienza",
    desc: "Video YouTube incorporati e Google Fonts per migliorare la fruibilità del sito.",
    icon: Cookie,
  },
  {
    key: "marketing", label: "Marketing",
    desc: "Meta Pixel, TikTok Pixel, LinkedIn Insight e Google Ads per misurare l'efficacia della pubblicità e proporti contenuti in linea con i tuoi interessi.",
    icon: Megaphone,
  },
];

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
}

function savePrefs(prefs) {
  const payload = {
    ...prefs,
    necessari: true,
    timestamp: new Date().toISOString(),
    version: "1.0",
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  return payload;
}

async function pushBackend(prefs) {
  // Best-effort audit log — matches existing POST /api/audit/consent schema
  try {
    await axios.post(`${API}/audit/consent`, {
      prefs: {
        essential: true,
        analytics: !!prefs.statistica,
        marketing: !!prefs.marketing,
      },
      policy_version: "1.0",
      language: navigator.language || "it-IT",
      page_url: window.location.href.slice(0, 300),
    });
  } catch (_) {
    // silent — banner UX must not fail if API is down
  }
}

export default function CookieBanner() {
  const [visible, setVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);

  useEffect(() => {
    initGoogleConsentDefaults(); // must run once regardless
    const stored = loadStored();
    if (stored && stored.version) {
      setPrefs({ ...DEFAULT_PREFS, ...stored });
      applyConsent(stored);
      setVisible(false);
    } else {
      setVisible(true);
    }
  }, []);

  const acceptAll = () => {
    const p = { necessari: true, statistica: true, esperienza: true, marketing: true };
    setPrefs(p);
    const saved = savePrefs(p);
    applyConsent(saved);
    pushBackend(saved);
    setVisible(false);
  };

  const rejectAll = () => {
    const p = { necessari: true, statistica: false, esperienza: false, marketing: false };
    setPrefs(p);
    const saved = savePrefs(p);
    applyConsent(saved);
    pushBackend(saved);
    setVisible(false);
  };

  const saveCustom = () => {
    const saved = savePrefs(prefs);
    applyConsent(saved);
    pushBackend(saved);
    setVisible(false);
  };

  const togglePref = (key) => {
    if (key === "necessari") return;
    setPrefs(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Expose a manual reopen (called from footer link)
  useEffect(() => {
    window.__openCookiePreferences = () => {
      const stored = loadStored();
      if (stored) setPrefs({ ...DEFAULT_PREFS, ...stored });
      setShowDetails(true);
      setVisible(true);
    };
    return () => { delete window.__openCookiePreferences; };
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-[9999] p-3 sm:p-4" data-testid="cookie-banner">
      <div className="mx-auto max-w-4xl bg-[#0A0A0A] text-[#F4F1ED] rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
        {!showDetails ? (
          // Compact banner
          <div className="p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#F58A1F]/20 flex items-center justify-center">
                <Cookie className="w-5 h-5 text-[#F58A1F]" />
              </div>
              <div className="flex-1">
                <h3 className="text-base sm:text-lg font-semibold mb-1">Rispettiamo la tua privacy</h3>
                <p className="text-xs sm:text-sm text-white/70 leading-relaxed">
                  Usiamo cookie tecnici per far funzionare il sito e — con il tuo consenso — cookie di statistica, esperienza e marketing per migliorare i nostri servizi e proporti contenuti in linea con i tuoi interessi.{" "}
                  <a href={COOKIE_POLICY_URL} className="underline text-white/85 hover:text-[#F58A1F]">
                    Cookie Policy
                  </a>
                  .
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-5">
              <button
                onClick={rejectAll}
                data-testid="cookie-reject-all-btn"
                className="px-4 py-3 rounded-full text-sm font-medium border border-white/25 hover:bg-white/10 transition-colors"
              >
                Rifiuta tutti
              </button>
              <button
                onClick={() => setShowDetails(true)}
                data-testid="cookie-customize-btn"
                className="px-4 py-3 rounded-full text-sm font-medium border border-white/25 hover:bg-white/10 transition-colors inline-flex items-center justify-center gap-2"
              >
                <Settings2 className="w-4 h-4" /> Personalizza
              </button>
              <button
                onClick={acceptAll}
                data-testid="cookie-accept-all-btn"
                className="px-4 py-3 rounded-full text-sm font-bold bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] hover:opacity-90 transition-opacity"
              >
                Accetta tutti
              </button>
            </div>
          </div>
        ) : (
          // Detailed preferences
          <div>
            <div className="flex items-center justify-between p-5 border-b border-white/10">
              <div>
                <h3 className="font-semibold text-base sm:text-lg">Preferenze cookie</h3>
                <p className="text-xs text-white/60 mt-0.5">Scegli per categoria. Puoi cambiare in qualsiasi momento.</p>
              </div>
              <button onClick={() => setShowDetails(false)} className="p-1.5 hover:bg-white/10 rounded-lg" aria-label="Chiudi">
                <X className="w-4 h-4 text-white/70" />
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-4 sm:p-5 space-y-3">
              {CATEGORIES.map(cat => {
                const Icon = cat.icon;
                const value = prefs[cat.key];
                return (
                  <div key={cat.key} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.05] transition-colors" data-testid={`cookie-cat-${cat.key}`}>
                    <div className="w-8 h-8 rounded-lg bg-[#F58A1F]/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Icon className="w-4 h-4 text-[#F58A1F]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-3">
                        <div className="font-medium text-sm">{cat.label}</div>
                        <button
                          onClick={() => togglePref(cat.key)}
                          disabled={cat.disabled}
                          data-testid={`cookie-toggle-${cat.key}`}
                          className={`relative inline-flex w-10 h-5 rounded-full flex-shrink-0 transition-colors ${
                            value ? "bg-green-500" : "bg-white/15"
                          } ${cat.disabled ? "opacity-70 cursor-not-allowed" : ""}`}
                          aria-label={`Toggle ${cat.label}`}
                        >
                          <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${value ? "translate-x-5" : ""}`} />
                        </button>
                      </div>
                      <div className="text-xs text-white/60 mt-1 leading-relaxed">{cat.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="p-4 sm:p-5 border-t border-white/10 grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                onClick={rejectAll}
                data-testid="cookie-reject-all-btn-details"
                className="px-4 py-2.5 rounded-full text-sm font-medium border border-white/25 hover:bg-white/10"
              >
                Rifiuta tutti
              </button>
              <button
                onClick={saveCustom}
                data-testid="cookie-save-custom-btn"
                className="px-4 py-2.5 rounded-full text-sm font-medium border border-white/25 hover:bg-white/10"
              >
                Salva selezione
              </button>
              <button
                onClick={acceptAll}
                data-testid="cookie-accept-all-btn-details"
                className="px-4 py-2.5 rounded-full text-sm font-bold bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] hover:opacity-90"
              >
                Accetta tutti
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
