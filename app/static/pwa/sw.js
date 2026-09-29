// Dizal PWA service worker is intentionally disabled.
// Previous versions cached HTML/assets and could leave stale pages.
// Keep this file as a self-cleaning worker so old registrations remove themselves safely.
self.addEventListener("install", event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(key => caches.delete(key))))
      .then(() => self.clients.claim())
      .then(() => self.registration.unregister())
  );
});

// No fetch handler: requests always go directly to the network.
