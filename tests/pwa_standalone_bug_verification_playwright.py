"""
Focused Playwright verification plan/script for bug: installed PWA on Android should
open only the patient app area, hide the install prompt, hide marketing chrome, and
keep normal browser mode unchanged.

This file documents the exact selectors and flows exercised by the testing agent
using the mcp_browser_automation tool in this verification run.
"""

BASE_URL = "https://portugues-writer-2.preview.emergentagent.com"
PATIENT_EMAIL = "demo.paziente@funzionabene.it"
PATIENT_PASSWORD = "paziente2026"

STANDALONE_MATCH_MEDIA_PATCH = r'''
(() => {
  const originalMatchMedia = window.matchMedia ? window.matchMedia.bind(window) : null;
  Object.defineProperty(window, 'matchMedia', {
    value: (query) => {
      if (String(query).includes('display-mode') && String(query).includes('standalone')) {
        return {
          matches: true,
          media: query,
          onchange: null,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
        };
      }
      return originalMatchMedia
        ? originalMatchMedia(query)
        : { matches: false, media: query, addEventListener: () => {}, removeEventListener: () => {} };
    },
    writable: true,
  });
  try {
    Object.defineProperty(window.navigator, 'standalone', { get: () => true, configurable: true });
  } catch (e) {}
  sessionStorage.setItem('just-registered', '1');
  localStorage.removeItem('pwa-install-dismissed');
})();
'''

NORMAL_BROWSER_MATCH_MEDIA_PATCH = r'''
(() => {
  const originalMatchMedia = window.matchMedia ? window.matchMedia.bind(window) : null;
  Object.defineProperty(window, 'matchMedia', {
    value: (query) => {
      if (String(query).includes('display-mode') && String(query).includes('standalone')) {
        return {
          matches: false,
          media: query,
          onchange: null,
          addEventListener: () => {},
          removeEventListener: () => {},
          addListener: () => {},
          removeListener: () => {},
          dispatchEvent: () => false,
        };
      }
      return originalMatchMedia
        ? originalMatchMedia(query)
        : { matches: false, media: query, addEventListener: () => {}, removeEventListener: () => {} };
    },
    writable: true,
  });
  try {
    Object.defineProperty(window.navigator, 'standalone', { get: () => false, configurable: true });
  } catch (e) {}
  sessionStorage.setItem('just-registered', '1');
  localStorage.removeItem('pwa-install-dismissed');
})();
'''
