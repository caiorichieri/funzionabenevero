/**
 * Utility: conditionally load 3rd-party marketing/analytics scripts based on
 * the user's cookie consent choices. Every loader is idempotent — safe to call
 * multiple times. IDs are placeholders — replace with real ones when known.
 *
 * The scripts are only injected in the browser; they never run server-side.
 */

const PLACEHOLDER_IDS = {
  GA4: process.env.REACT_APP_GA4_ID || "",           // e.g. "G-XXXXXXX"
  META_PIXEL: process.env.REACT_APP_META_PIXEL_ID || "",  // e.g. "1234567890"
  TIKTOK_PIXEL: process.env.REACT_APP_TIKTOK_PIXEL_ID || "",  // e.g. "CXXXXXXXXX"
  LINKEDIN: process.env.REACT_APP_LINKEDIN_PARTNER_ID || "",
  GOOGLE_ADS: process.env.REACT_APP_GOOGLE_ADS_ID || "",  // e.g. "AW-XXXXXXX"
  CLARITY: process.env.REACT_APP_MS_CLARITY_ID || "",
};

const injectScript = (id, src, async = true) => {
  if (document.getElementById(id)) return;
  const s = document.createElement("script");
  s.id = id;
  s.async = async;
  s.src = src;
  document.head.appendChild(s);
};

const injectInline = (id, code) => {
  if (document.getElementById(id)) return;
  const s = document.createElement("script");
  s.id = id;
  // Use textContent (not innerHTML): the content is our own inline JS,
  // never user input. textContent is the safer API for <script> injection.
  s.textContent = code;
  document.head.appendChild(s);
};

// ─── Statistica ──────────────────────────────────────────────────────────────

export const loadGoogleAnalytics = () => {
  const gaId = PLACEHOLDER_IDS.GA4;
  if (!gaId) return;
  injectScript("ga4-loader", `https://www.googletagmanager.com/gtag/js?id=${gaId}`);
  injectInline("ga4-init", `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '${gaId}', { anonymize_ip: true });
  `);
};

export const loadMicrosoftClarity = () => {
  const cid = PLACEHOLDER_IDS.CLARITY;
  if (!cid) return;
  injectInline("clarity-init", `
    (function(c,l,a,r,i,t,y){
      c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
      t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
      y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", "${cid}");
  `);
};

// ─── Marketing ───────────────────────────────────────────────────────────────

export const loadMetaPixel = () => {
  const pid = PLACEHOLDER_IDS.META_PIXEL;
  if (!pid) return;
  injectInline("meta-pixel", `
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
    document,'script','https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', '${pid}');
    fbq('track', 'PageView');
  `);
};

export const loadTikTokPixel = () => {
  const pid = PLACEHOLDER_IDS.TIKTOK_PIXEL;
  if (!pid) return;
  injectInline("tiktok-pixel", `
    !function (w, d, t) {
      w.TiktokAnalyticsObject=t;var ttq=w[t]=w[t]||[];
      ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie"];
      ttq.setAndDefer=function(t,e){t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}};
      for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);
      ttq.instance=function(t){for(var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e};
      ttq.load=function(e,n){var i="https://analytics.tiktok.com/i18n/pixel/events.js";
        ttq._i=ttq._i||{},ttq._i[e]=[],ttq._i[e]._u=i,ttq._t=ttq._t||{},ttq._t[e]=+new Date,ttq._o=ttq._o||{},ttq._o[e]=n||{};
        var o=document.createElement("script");o.type="text/javascript",o.async=!0,o.src=i+"?sdkid="+e+"&lib="+t;
        var a=document.getElementsByTagName("script")[0];a.parentNode.insertBefore(o,a)};
      ttq.load('${pid}');
      ttq.page();
    }(window, document, 'ttq');
  `);
};

export const loadLinkedInInsight = () => {
  const pid = PLACEHOLDER_IDS.LINKEDIN;
  if (!pid) return;
  injectInline("linkedin-init", `_linkedin_partner_id = "${pid}"; window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || []; window._linkedin_data_partner_ids.push(_linkedin_partner_id);`);
  injectScript("linkedin-loader", "https://snap.licdn.com/li.lms-analytics/insight.min.js");
};

export const loadGoogleAds = () => {
  const aid = PLACEHOLDER_IDS.GOOGLE_ADS;
  if (!aid) return;
  // gtag is often already loaded by GA4; if not, load it.
  if (!document.getElementById("ga4-loader") && !document.getElementById("gads-loader")) {
    injectScript("gads-loader", `https://www.googletagmanager.com/gtag/js?id=${aid}`);
  }
  injectInline("gads-init", `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', '${aid}');
  `);
};

// ─── Google Consent Mode v2 ──────────────────────────────────────────────────
/**
 * Apply Google Consent Mode v2 signals BEFORE any tag loads.
 * This runs on every page load with default 'denied' values.
 */
export const initGoogleConsentDefaults = () => {
  injectInline("gcm-defaults", `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('consent', 'default', {
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied',
      'analytics_storage': 'denied',
      'functionality_storage': 'granted',
      'security_storage': 'granted',
      'wait_for_update': 500
    });
  `);
};

export const updateGoogleConsent = ({ statistica, marketing }) => {
  if (!window.dataLayer) window.dataLayer = [];
  function gtag(){ window.dataLayer.push(arguments); }
  gtag('consent', 'update', {
    'ad_storage': marketing ? 'granted' : 'denied',
    'ad_user_data': marketing ? 'granted' : 'denied',
    'ad_personalization': marketing ? 'granted' : 'denied',
    'analytics_storage': statistica ? 'granted' : 'denied',
  });
};

// ─── Apply consent (single entry point) ──────────────────────────────────────

export const applyConsent = (prefs) => {
  updateGoogleConsent({ statistica: prefs.statistica, marketing: prefs.marketing });
  if (prefs.statistica) {
    loadGoogleAnalytics();
    loadMicrosoftClarity();
  }
  if (prefs.marketing) {
    loadMetaPixel();
    loadTikTokPixel();
    loadLinkedInInsight();
    loadGoogleAds();
  }
};
