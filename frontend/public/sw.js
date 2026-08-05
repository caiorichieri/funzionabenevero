/* Funzionabene PWA — Service Worker
 * Strategies:
 *  - Static assets (js/css/img): stale-while-revalidate, cache-first fallback
 *  - HTML navigation: network-first, offline fallback to cached shell
 *  - /api/*: NEVER cache — always network (dynamic user data)
 */
const CACHE_NAME = "funzionabene-v1";
const OFFLINE_URL = "/";
const STATIC_ASSETS = [
  "/",
  "/manifest.json",
  "/favicon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never intercept API calls (dynamic + auth)
  if (url.pathname.startsWith("/api/")) return;
  // Only GET
  if (request.method !== "GET") return;
  // Only same-origin
  if (url.origin !== self.location.origin) return;

  // HTML navigation → network-first, fallback to cached shell
  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, copy));
          return res;
        })
        .catch(() => caches.match(request).then((r) => r || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Static assets → stale-while-revalidate
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((c) => c.put(request, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || fetchPromise;
    })
  );
});

// Web Push (VAPID) — placeholder for Fase A parte 2
self.addEventListener("push", (event) => {
  if (!event.data) return;
  let payload = {};
  try { payload = event.data.json(); } catch { payload = { title: "Funzionabene", body: event.data.text() }; }
  const options = {
    body: payload.body || "",
    icon: "/favicon.png",
    badge: "/favicon.png",
    data: { url: payload.url || "/paziente" },
    vibrate: [100, 50, 100],
  };
  event.waitUntil(self.registration.showNotification(payload.title || "Funzionabene", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(url));
});
