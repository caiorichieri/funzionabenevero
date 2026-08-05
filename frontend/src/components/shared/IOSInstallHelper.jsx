import { useEffect, useState } from "react";
import { Share, Plus, X, Smartphone } from "lucide-react";

/**
 * Detects iOS Safari (which does NOT support beforeinstallprompt) and shows
 * a friendly visual guide to add the app to the Home Screen.
 */
function isIOS() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  const isIPhone = /iPhone|iPad|iPod/i.test(ua);
  const isSafari = /Safari/i.test(ua) && !/CriOS|FxiOS|EdgiOS/i.test(ua);
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches ||
                        window.navigator.standalone === true;
  return isIPhone && isSafari && !isStandalone;
}

export default function IOSInstallHelper() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!isIOS()) return;
    if (localStorage.getItem("ios-install-dismissed")) return;
    // Delay so it doesn't overlap with the initial page load
    const t = setTimeout(() => setVisible(true), 2500);
    return () => clearTimeout(t);
  }, []);

  const dismiss = () => {
    localStorage.setItem("ios-install-dismissed", "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      data-testid="ios-install-helper"
      onClick={dismiss}
    >
      <div
        className="bg-white w-full sm:max-w-md rounded-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 bg-gradient-to-br from-[#F58A1F] to-[#F5D419] relative">
          <button onClick={dismiss} className="absolute top-3 right-3 p-1.5 hover:bg-black/10 rounded-full text-[#0A0A0A]/60" aria-label="Chiudi">
            <X className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/90 flex items-center justify-center">
              <Smartphone className="w-6 h-6 text-[#0A0A0A]" />
            </div>
            <div>
              <div className="text-[10px] font-medium tracking-widest uppercase text-[#0A0A0A]/70">Funzionabene</div>
              <h2 className="text-lg font-bold text-[#0A0A0A] leading-tight">Installa l&apos;app in 2 passi</h2>
            </div>
          </div>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-start gap-4 p-3 rounded-2xl bg-[#0A0A0A]/[0.03]">
            <div className="w-8 h-8 rounded-full bg-[#0A0A0A] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">1</div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#0A0A0A] flex items-center gap-2 flex-wrap">
                Tap sull&apos;icona <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-lg border border-[#0A0A0A]/10"><Share className="w-3.5 h-3.5 text-[#007AFF]" /> <span className="text-xs">Condividi</span></span>
              </div>
              <p className="text-xs text-[#0A0A0A]/60 mt-1">In basso nella barra di Safari.</p>
            </div>
          </div>
          <div className="flex items-start gap-4 p-3 rounded-2xl bg-[#0A0A0A]/[0.03]">
            <div className="w-8 h-8 rounded-full bg-[#0A0A0A] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">2</div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#0A0A0A] flex items-center gap-2 flex-wrap">
                Scegli <span className="inline-flex items-center gap-1 px-2 py-1 bg-white rounded-lg border border-[#0A0A0A]/10"><Plus className="w-3.5 h-3.5" /> <span className="text-xs">Aggiungi a Home</span></span>
              </div>
              <p className="text-xs text-[#0A0A0A]/60 mt-1">Poi tocca &quot;Aggiungi&quot; in alto a destra.</p>
            </div>
          </div>
          <div className="text-center pt-2">
            <p className="text-xs text-[#0A0A0A]/60 leading-relaxed">
              L&apos;icona <span className="inline-block w-4 h-4 rounded bg-gradient-to-br from-[#F58A1F] to-[#F5D419] align-middle" /> comparirà sulla schermata Home come una vera app.
            </p>
          </div>
          <button
            onClick={dismiss}
            data-testid="ios-install-dismiss"
            className="w-full py-3 rounded-full border border-[#0A0A0A]/15 text-sm font-medium text-[#0A0A0A]/70"
          >
            Ho capito, chiudi
          </button>
        </div>
      </div>
    </div>
  );
}
