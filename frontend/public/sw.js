// Service worker: keeps the app shell available when the local backend is down (ticket 14).
// Network first for everything; fall back to the cached copy. API data is never cached here.
const CACHE = "sf-shell-v1";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/index.html"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Only the app shell: page navigations and built assets. Data files (replays, crew records,
  // models) and /api/* are left to the browser so the app's own loaders see them unchanged.
  const shell = e.request.mode === "navigate" || url.pathname.startsWith("/assets/");
  if (e.request.method !== "GET" || url.origin !== self.location.origin || !shell) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request).then((m) => m || caches.match("/index.html"))),
  );
});
