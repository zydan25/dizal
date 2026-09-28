const VERSION="20260928-9";
const CACHE="dizal-shell-"+VERSION;
const SHELL=["/static/css/app.css?v=20260928-9","/static/js/app.js?v=20260928-9","/static/manifest.webmanifest?v=20260928-9","/static/icons/dizal.svg?v=20260928-9"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith("dizal-shell-")&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",e=>{if(e.request.method!=="GET")return;e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return response;}).catch(()=>cached)));});
