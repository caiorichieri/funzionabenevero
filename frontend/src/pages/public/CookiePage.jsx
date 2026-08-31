import LegalLayout from "@/components/public/LegalLayout";
import SEO from "@/components/shared/SEO";
import { useState, useEffect } from "react";
import { getCookiePreferences, setCookiePreferences, clearCookieConsent } from "@/utils/cookieConsent";

function Toggle({ name, label, desc, disabled, prefs, setPrefs }) {
  return (
    <div className="flex items-start justify-between gap-6 py-5 border-b border-[#0A0A0A]/10">
      <div>
        <div className="text-[#0A0A0A] font-medium mb-1">{label}</div>
        <div className="text-sm text-[#0A0A0A]/65 leading-relaxed">{desc}</div>
      </div>
      <label className="relative inline-block w-11 h-6 flex-shrink-0 mt-1 cursor-pointer">
        <input
          type="checkbox" disabled={disabled}
          data-testid={`cookie-toggle-${name}`}
          checked={prefs[name]}
          onChange={(e) => setPrefs({ ...prefs, [name]: e.target.checked })}
          className="sr-only peer"
        />
        <span className={`block w-11 h-6 rounded-full transition-colors ${prefs[name] ? "bg-[#0A0A0A]" : "bg-white/15"} ${disabled ? "opacity-60" : ""}`}></span>
        <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${prefs[name] ? "translate-x-5" : ""}`}></span>
      </label>
    </div>
  );
}

export default function CookiePage() {
  const [prefs, setPrefs] = useState({ essential: true, analytics: false, marketing: false });

  useEffect(() => {
    const saved = getCookiePreferences();
    if (saved) setPrefs(saved);
  }, []);

  const save = () => {
    setCookiePreferences(prefs);
    alert("Preferenze salvate. Ricarica la pagina per applicare i cambiamenti.");
  };

  const revoke = () => {
    clearCookieConsent();
    setPrefs({ essential: true, analytics: false, marketing: false });
    alert("Consenso revocato. Ricarica la pagina per rimostrare il banner.");
  };

  return (
    <>
      <SEO title="Cookie Policy" description="Informativa sui cookie utilizzati da FunzionaBene: essenziali, di analisi e di marketing." path="/cookie" />
      <LegalLayout title="Cookie Policy" lastUpdate="19 aprile 2026" testId="cookie-page">
      <p>
        Il sito <strong>funzionabene.it</strong> utilizza cookie e tecnologie simili per garantire il funzionamento
        del sito, migliorare l&apos;esperienza utente e (solo con il tuo consenso) analizzare il traffico.
      </p>

      <h2>Tipologie di cookie</h2>

      <h3>Cookie essenziali (sempre attivi)</h3>
      <p>
        Necessari per il funzionamento del sito: login, sessione utente, prenotazioni, carrello, preferenze cookie.
        Non richiedono consenso ai sensi dell&apos;art. 122 del Codice Privacy.
      </p>
      <ul>
        <li><strong>access_token</strong>, <strong>refresh_token</strong>: autenticazione (durata: 7 giorni).</li>
        <li><strong>fb_cookie_consent</strong>: memorizza le tue preferenze cookie (durata: 12 mesi).</li>
      </ul>

      <h3>Cookie di analisi (opzionali)</h3>
      <p>
        Ci aiutano a capire come gli utenti utilizzano il sito in forma anonima e aggregata, per migliorare i contenuti.
        Attivati solo con il tuo consenso.
      </p>

      <h3>Cookie di marketing (opzionali)</h3>
      <p>
        Utilizzati per mostrare annunci pertinenti e misurare l&apos;efficacia delle campagne.
        <strong> Attualmente non utilizziamo cookie di marketing.</strong>
      </p>

      <h2 style={{ marginTop: "2.5rem" }}>Gestisci le tue preferenze</h2>

      <div style={{ background: "rgba(212,160,23,0.04)", border: "1px solid rgba(212,160,23,0.2)", borderRadius: 16, padding: "4px 24px", marginTop: 16 }}>
        <Toggle
          name="essential"
          label="Cookie essenziali"
          desc="Necessari per il funzionamento del sito. Sempre attivi."
          disabled={true}
          prefs={prefs}
          setPrefs={setPrefs}
        />
        <Toggle
          name="analytics"
          label="Cookie di analisi"
          desc="Ci permettono di misurare l'utilizzo del sito in forma anonima."
          prefs={prefs}
          setPrefs={setPrefs}
        />
        <Toggle
          name="marketing"
          label="Cookie di marketing"
          desc="Per campagne pubblicitarie personalizzate (attualmente non utilizzati)."
          prefs={prefs}
          setPrefs={setPrefs}
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mt-8">
        <button
          data-testid="cookie-save-btn"
          onClick={save}
          className="px-6 py-3 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] hover:from-[#E07A0F] hover:to-[#E5C419] text-[#0A0A0A] font-bold rounded-2xl shadow-md hover:shadow-lg text-sm font-medium tracking-wide transition-all"
        >
          Salva preferenze
        </button>
        <button
          data-testid="cookie-revoke-btn"
          onClick={revoke}
          className="px-6 py-3 border border-[rgba(28,28,28,0.12)] text-[#0A0A0A] hover:bg-[rgba(28,28,28,0.04)] rounded-full text-sm tracking-wide transition-all"
        >
          Revoca tutto il consenso
        </button>
      </div>

      <h2 style={{ marginTop: "3rem" }}>Durata dei cookie</h2>
      <ul>
        <li><strong>Di sessione:</strong> eliminati alla chiusura del browser.</li>
        <li><strong>Persistenti:</strong> durano al massimo 12 mesi dalla prima installazione.</li>
      </ul>

      <h2>Cookie di terze parti</h2>
      <p>
        Alcune pagine potrebbero integrare contenuti di terze parti (ad esempio video delle sessioni via Daily.co).
        Queste piattaforme possono installare propri cookie. Per maggiori informazioni consulta le loro privacy policy.
      </p>

      <h2>Base giuridica</h2>
      <p>
        I cookie essenziali si basano sul legittimo interesse (art. 6.1.f GDPR) e sull&apos;art. 122 Codice Privacy.
        I cookie non essenziali richiedono consenso (art. 7 GDPR), revocabile in qualsiasi momento tramite questa pagina.
      </p>
    </LegalLayout>
    </>
  );
}
