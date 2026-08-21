// Cookie consent storage helper
// Uses a real first-party cookie (Secure, SameSite=Strict, path=/) instead of
// localStorage, to harden against XSS exfiltration and align with GDPR best practices.
// Only non-sensitive booleans are persisted here.
const COOKIE_KEY = "fb_cookie_consent";
const COOKIE_VERSION = "1";
const MAX_AGE_SECONDS = 60 * 60 * 24 * 180; // 180 days
const API_BASE = process.env.REACT_APP_BACKEND_URL || "";

function readCookie(name) {
  const target = name + "=";
  const cookies = (document.cookie || "").split(";");
  for (let c of cookies) {
    c = c.trim();
    if (c.indexOf(target) === 0) return decodeURIComponent(c.substring(target.length));
  }
  return null;
}

function writeCookie(name, value, maxAge) {
  const isHttps = typeof window !== "undefined" && window.location.protocol === "https:";
  const secure = isHttps ? "; Secure" : "";
  document.cookie = `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; SameSite=Strict${secure}`;
}

function deleteCookie(name) {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Strict`;
}

export function getCookiePreferences() {
  const raw = readCookie(COOKIE_KEY);
  if (!raw) return null;
  try {
    const data = JSON.parse(raw);
    if (data.version !== COOKIE_VERSION) return null;
    return data.prefs;
  } catch {
    return null;
  }
}

export function hasGivenConsent() {
  return getCookiePreferences() !== null;
}

export function setCookiePreferences(prefs) {
  const fullPrefs = { essential: true, analytics: !!prefs.analytics, marketing: !!prefs.marketing };
  const payload = {
    version: COOKIE_VERSION,
    prefs: fullPrefs,
    timestamp: new Date().toISOString(),
  };
  writeCookie(COOKIE_KEY, JSON.stringify(payload), MAX_AGE_SECONDS);
  window.dispatchEvent(new Event("fb-cookie-consent-changed"));
  // Fire-and-forget GDPR audit log to the backend (immutable proof of consent).
  // We deliberately do not await/await the response: the user's choice is already
  // persisted client-side via the cookie, and the audit call must not block the UI.
  try {
    fetch(`${API_BASE}/api/audit/consent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prefs: fullPrefs,
        policy_version: COOKIE_VERSION,
        language: typeof navigator !== "undefined" ? navigator.language : null,
        page_url: typeof window !== "undefined" ? window.location.pathname : null,
      }),
      keepalive: true,
    }).catch((err) => {
      if (typeof console !== "undefined") console.warn("[consent] fetch failed:", err?.message || err);
    });
  } catch (err) {
    if (typeof console !== "undefined") console.warn("[consent] handler error:", err?.message || err);
  }
}

export function acceptAll() {
  setCookiePreferences({ analytics: true, marketing: true });
}

export function acceptEssentialOnly() {
  setCookiePreferences({ analytics: false, marketing: false });
}

export function clearCookieConsent() {
  deleteCookie(COOKIE_KEY);
  window.dispatchEvent(new Event("fb-cookie-consent-changed"));
}
