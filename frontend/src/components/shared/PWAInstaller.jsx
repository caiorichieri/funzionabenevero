import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

/**
 * PWA Service Worker registration + "Add to Home Screen" prompt.
 * Renders a discreet install banner when installable and dismisses on demand.
 */
export default function PWAInstaller() {
  const [deferred, setDeferred] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("/sw.js").catch(() => {});
      });
    }

    // Hide when already installed / running as PWA
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true;
    if (isStandalone) return;

    const dismissed = localStorage.getItem("pwa-install-dismissed");
    if (dismissed) return;

    const justRegistered = sessionStorage.getItem("just-registered");
    if (justRegistered) {
      sessionStorage.removeItem("just-registered");
      setTimeout(() => setVisible(true), 1500);
    }

    const handler = (e) => {
      e.preventDefault();
      setDeferred(e);
      window.__deferredPWAPrompt = e;
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const install = async () => {
    if (deferred) {
      deferred.prompt();
      await deferred.userChoice;
      setDeferred(null);
      setVisible(false);
    } else {
      // No native prompt available (e.g. just-registered flow, iOS, already installed).
      // Send the user to the install-instructions page.
      window.location.href = "/scarica-app";
    }
  };
  const dismiss = () => {
    localStorage.setItem("pwa-install-dismissed", "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:max-w-sm bg-[#0A0A0A] text-white rounded-2xl shadow-2xl p-4 z-50 flex items-start gap-3 animate-slide-up"
      data-testid="pwa-install-banner"
    >
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#F58A1F] to-[#F5D419] flex items-center justify-center flex-shrink-0">
        <Download className="w-5 h-5 text-[#0A0A0A]" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm">Installa Funzionabene</div>
        <p className="text-xs text-white/70 mt-0.5 leading-snug">
          Aggiungi alla schermata Home per accesso rapido e notifiche.
        </p>
        <div className="flex gap-2 mt-2">
          <button
            onClick={install}
            data-testid="pwa-install-btn"
            className="px-3 py-1.5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] text-[#0A0A0A] rounded-full text-xs font-semibold"
          >
            Installa
          </button>
          <button
            onClick={dismiss}
            data-testid="pwa-install-dismiss"
            className="px-3 py-1.5 text-white/60 text-xs hover:text-white/90"
          >
            Non ora
          </button>
        </div>
      </div>
      <button onClick={dismiss} className="text-white/40 hover:text-white/80 flex-shrink-0" aria-label="Chiudi">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
