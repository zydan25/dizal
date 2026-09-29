// Dizal PWA diagnostic mode.
// No fetch handler and no caching: the browser/network serves all requests.
// Kept as a self-cleaning worker so any older registrations are removed.
self.addEventListener("install",event=>{
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.map(key=>caches.delete(key))))
      .then(()=>self.clients.claim())
      .then(()=>self.registration.unregister())
  );
});
