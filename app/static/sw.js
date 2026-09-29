const VERSION="20260930-2";
const CACHE="dizal-static-"+VERSION;
const STATIC_SHELL=[
  "/static/css/app.css?v=20260930-2",
  "/static/js/app.js?v=20260930-2",
  "/static/manifest.webmanifest?v=20260930-2",
  "/static/icons/dizal-192.png?v=20260930-2",
  "/static/icons/dizal-512.png?v=20260930-2",
  "/static/offline.html"
];

self.addEventListener("install",(event)=>{
  event.waitUntil(
    caches.open(CACHE)
      .then((cache)=>cache.addAll(STATIC_SHELL))
      .then(()=>self.skipWaiting())
  );
});

self.addEventListener("activate",(event)=>{
  event.waitUntil(
    caches.keys()
      .then((keys)=>Promise.all(
        keys.filter((key)=>key.startsWith("dizal-") && key!==CACHE)
          .map((key)=>caches.delete(key))
      ))
      .then(()=>self.clients.claim())
  );
});

async function staticResponse(request){
  const cached=await caches.match(request);
  if(cached)return cached;
  const response=await fetch(request);
  if(response.ok){
    const cache=await caches.open(CACHE);
    await cache.put(request,response.clone());
  }
  return response;
}

self.addEventListener("fetch",(event)=>{
  if(event.request.method!=="GET")return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin)return;

  if(event.request.mode==="navigate"){
    event.respondWith(
      fetch(event.request,{cache:"no-store"})
        .catch(()=>caches.match("/static/offline.html"))
    );
    return;
  }

  if(url.pathname.startsWith("/static/")){
    event.respondWith(
      staticResponse(event.request)
        .catch(()=>caches.match("/static/offline.html"))
    );
  }
});
