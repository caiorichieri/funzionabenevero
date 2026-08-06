"""
Iteration 19 focused bug-verification script notes.

Bug under test: installed Android PWA must behave like a dedicated patient app,
not the full marketing site / install invitation page. Regression checks include
standalone chat send and composer overlap with bottom nav.

The executable Playwright steps were run through mcp_browser_automation using:
- Mobile viewport: 390x844
- Patient credentials: demo.paziente@funzionabene.it / paziente2026
- Standalone override: window.matchMedia('(display-mode: standalone)').matches = true

Direct checks covered:
1. Standalone login lands in /paziente with paziente-app-shell and mockup home.
2. PWA install banner remains hidden in standalone, including just-registered state.
3. /scarica-app and /blog redirect back to /paziente in standalone.
4. Bottom nav renders exactly 4 tabs.
5. /paziente/chat opens conversation; elementFromPoint at chat-send center resolves
   to the send button, not paziente-bottom-nav; POST /api/messaggi returns 200;
   sent text is visible and present in GET /api/messaggi response.
6. Normal browser mode still renders the public marketing home/site and the legacy
   PazienteDashboard after login.
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
        return { matches: true, media: query, onchange: null,
          addEventListener: () => {}, removeEventListener: () => {},
          addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false };
      }
      return originalMatchMedia ? originalMatchMedia(query) :
        { matches: false, media: query, addEventListener: () => {}, removeEventListener: () => {} };
    },
    writable: true,
  });
  try { Object.defineProperty(window.navigator, 'standalone', { get: () => true, configurable: true }); } catch (e) {}
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
        return { matches: false, media: query, onchange: null,
          addEventListener: () => {}, removeEventListener: () => {},
          addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false };
      }
      return originalMatchMedia ? originalMatchMedia(query) :
        { matches: false, media: query, addEventListener: () => {}, removeEventListener: () => {} };
    },
    writable: true,
  });
  try { Object.defineProperty(window.navigator, 'standalone', { get: () => false, configurable: true }); } catch (e) {}
  sessionStorage.setItem('just-registered', '1');
  localStorage.removeItem('pwa-install-dismissed');
})();
'''