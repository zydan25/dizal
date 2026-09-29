const VERSION="20260930-6";
const CACHE="dizal-static-"+VERSION;
const STATIC_SHELL=[
  "/static/css/app.css?v=20260930-4",
  "/static/js/app.js?v=20260930-4",
  "/static/js/pwa-debug.js?v=20260930-6",
  "/static/manifest.webmanifest?v=20260930-4",
  "/static/icons/dizal-192.png?v=20260930-4",
  "/static/icons/dizal-512.png?v=20260930-4"
];

self.addEventListener("install",event=>{
  event.waitUntil(
    caches.open(CACHE)
      .then(cache=>cache.addAll(STATIC_SHELL))
      .then(()=>self.skipWaiting())
  );
});

self.addEventListener("activate",event=>{
  event.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(
        keys.filter(key=>key.startsWith("dizal-")&&key!==CACHE).map(key=>caches.delete(key))
      ))
      .then(()=>self.clients.claim())
  );
});

// Diagnostic mode: no navigation interception and no offline fallback.
// Requests use the normal browser/network path.
