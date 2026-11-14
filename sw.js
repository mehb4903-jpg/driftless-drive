/* Driftless Drive service worker: network first (so every push is picked up at once), the cached copy only when offline. */
const CACHE = 'dd-shell-v1';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const r = e.request; if (r.method !== 'GET') return; const u = new URL(r.url); if (u.origin !== location.origin) return;
  e.respondWith(fetch(r).then(res => { if (res && res.ok) { const c = res.clone(); caches.open(CACHE).then(ch => ch.put(r, c)); } return res; }).catch(() => caches.match(r).then(m => m || caches.match('./index.html'))));
});
