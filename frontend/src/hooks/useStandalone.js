import { useEffect, useState } from "react";

/**
 * Returns true when the page is running as an installed PWA (standalone mode)
 * on Android/Chrome/Edge OR iOS Safari added-to-home-screen.
 */
export default function useStandalone() {
  const [isStandalone, setIsStandalone] = useState(() => detect());

  useEffect(() => {
    const mql = window.matchMedia("(display-mode: standalone)");
    const on = () => setIsStandalone(detect());
    mql.addEventListener?.("change", on);
    return () => mql.removeEventListener?.("change", on);
  }, []);

  return isStandalone;
}

function detect() {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(display-mode: standalone)").matches) return true;
  if (window.navigator.standalone === true) return true; // iOS Safari
  // Manual preview mode: add ?app=1 to any URL to see the standalone experience
  // without installing. Persists in the same tab via sessionStorage.
  try {
    const url = new URL(window.location.href);
    if (url.searchParams.get("app") === "1") {
      sessionStorage.setItem("__preview-app-mode", "1");
    }
    if (sessionStorage.getItem("__preview-app-mode") === "1") return true;
  } catch (err) {
    if (typeof console !== "undefined") console.warn("[useStandalone] URL/sessionStorage access failed:", err?.message || err);
  }
  return false;
}
