const VERSION="20260928-4";
const CACHE=`dizal-shell-${VERSION}`;
const SHELL=["/static/css/app.css?v=20260928-4","/static/js/app.js?v=20260928-4","/static/manifest.webmanifest?v=20260928-4","/static/icons/dizal.svg?v=20260928-4"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));
self.addEventListener("fetch",e=>{if(e.request.method!=="GET")return;e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request).then(response=>{const copy=response.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return response;}).catch(()=>cached)));});