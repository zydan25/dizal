(()=>{let deferredPrompt=null;
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const cell=(label,value,cls)=>'<div class="item"><b>'+esc(label)+'</b><span class="'+(cls||"")+'">'+esc(value)+'</span></div>';
const yn=v=>v?"✅ نعم":"❌ لا";
window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();deferredPrompt=e;renderButton();run();console.info("Dizal PWA debug: beforeinstallprompt",e.platforms||[])});
window.addEventListener("appinstalled",function(){deferredPrompt=null;renderButton();run()});
async function get(url){
  try{
    const t=performance.now(),r=await fetch(url,{cache:"no-store",credentials:"same-origin"}),body=await r.text();
    return {ok:r.ok,status:r.status,type:r.headers.get("content-type")||"",allowed:r.headers.get("service-worker-allowed")||"",body:body,ms:Math.round(performance.now()-t)}
  }catch(e){return {ok:false,error:String(e)}}
}
async function image(url){
  return new Promise(function(resolve){
    const img=new Image();
    img.onload=function(){resolve({ok:true,w:img.naturalWidth,h:img.naturalHeight})};
    img.onerror=function(){resolve({ok:false})};
    img.src=url+(url.includes("?")?"&":"?")+"_debug="+Date.now();
  })
}
async function run(){
  const n=navigator,standalone=window.matchMedia("(display-mode: standalone)").matches||n.standalone===true;
  const m=await get("/manifest.webmanifest?_debug="+Date.now());
  let manifest=null,jsonError="";
  if(m.ok){try{manifest=JSON.parse(m.body)}catch(e){jsonError=String(e)}}
  const sw=await get("/sw.js?_debug="+Date.now());
  let regs=[],regError="",reg=null;
  if("serviceWorker" in n){
    try{regs=await n.serviceWorker.getRegistrations()}catch(e){regError=String(e)}
    try{reg=await n.serviceWorker.register("/sw.js?_debug="+Date.now(),{scope:"/",updateViaCache:"none"});await reg.update().catch(function(){})}catch(e){regError=regError||String(e)}
  }
  const imgs=[];
  for(const icon of (manifest&&manifest.icons||[])) imgs.push({src:icon.src,want:icon.sizes,result:await image(icon.src)});
  $("state").innerHTML=[
    cell("HTTPS / secureContext",yn(window.isSecureContext),window.isSecureContext?"ok":"bad"),
    cell("Service Worker API",yn("serviceWorker"in n),"serviceWorker"in n?"ok":"bad"),
    cell("SW Controller",n.serviceWorker&&n.serviceWorker.controller?n.serviceWorker.controller.scriptURL:"❌ لا يوجد",n.serviceWorker&&n.serviceWorker.controller?"ok":"warn"),
    cell("beforeinstallprompt",deferredPrompt?"✅ وصل وجاهز":"⚠️ لم يصل حتى الآن",deferredPrompt?"ok":"warn"),
    cell("Standalone",standalone?"✅ نعم":"لا",standalone?"ok":""),
    cell("متصل بالإنترنت",yn(n.onLine),n.onLine?"ok":"bad"),
    cell("Android",/Android/i.test(n.userAgent)?"✅ نعم":"لا"),
    cell("Manifest link",document.querySelector('link[rel="manifest"]')?"✅ موجود":"❌ غير موجود")
  ].join("");
  $("resources").innerHTML=[
    cell("Manifest HTTP",m.ok?"✅ "+m.status+" · "+m.type:"❌ "+(m.error||m.status),m.ok?"ok":"bad"),
    cell("SW HTTP",sw.ok?"✅ "+sw.status+" · "+sw.type:"❌ "+(sw.error||sw.status),sw.ok?"ok":"bad"),
    cell("Service-Worker-Allowed",sw.allowed||"غير موجود",sw.allowed==="/"?"ok":"warn"),
    cell("start_url",manifest&&manifest.start_url||"غير موجود",manifest&&manifest.start_url?"ok":"bad"),
    cell("scope",manifest&&manifest.scope||"غير موجود",manifest&&manifest.scope==="/"?"ok":"warn"),
    cell("display",manifest&&manifest.display||"غير موجود",manifest&&manifest.display==="standalone"?"ok":"warn"),
    cell("Manifest JSON",jsonError||"✅ صالح",jsonError?"bad":"ok")
  ].join("");
  $("sw").innerHTML=regs.length?regs.map(function(r){
    return '<div class="item"><b>تسجيل Service Worker</b><span>scope: '+esc(r.scope)+'<br>script: '+esc((r.active&&r.active.scriptURL)||(r.installing&&r.installing.scriptURL)||(r.waiting&&r.waiting.scriptURL)||"")+'<br>state: '+esc((r.active&&r.active.state)||(r.installing&&r.installing.state)||(r.waiting&&r.waiting.state)||"none")+'</span></div>'
  }).join(""):'<div class="item"><span class="warn">لا توجد تسجيلات سابقة.</span></div>';
  $("sw").innerHTML+='<div class="grid" style="margin-top:8px">'+cell("التسجيل الحالي",(reg&&reg.active&&reg.active.state)||(reg&&reg.installing&&reg.installing.state)||(reg&&reg.waiting&&reg.waiting.state)||"غير معروف",reg?"ok":"warn")+cell("خطأ التسجيل",regError||"لا يوجد",regError?"bad":"ok")+'</div>';
  $("icons").innerHTML=imgs.map(function(x,i){
    return '<div class="icon-test"><img src="'+esc(x.src)+'"><div><b>Icon '+(i+1)+'</b><br><span class="'+(x.result.ok?"ok":"bad")+'">'+(x.result.ok?"✅ "+x.result.w+"×"+x.result.h:"❌ تعذر التحميل")+'</span><br><small>المعلن: '+esc(x.want)+'</small></div></div>'
  }).join("")||'<div class="item"><span class="warn">لا توجد أيقونات في Manifest.</span></div>';
  $("details").textContent=JSON.stringify({
    ua:n.userAgent,platform:n.userAgentData&&n.userAgentData.platform||n.platform||"",mobile:n.userAgentData&&n.userAgentData.mobile!==undefined?n.userAgentData.mobile:null,
    secureContext:window.isSecureContext,online:n.onLine,standalone:standalone,location:location.href,manifest:manifest,
    manifestHttp:{status:m.status,type:m.type,error:m.error||null},swHttp:{status:sw.status,type:sw.type,allowed:sw.allowed,error:sw.error||null},
    registrations:regs.map(function(r){return {scope:r.scope,scriptURL:(r.active&&r.active.scriptURL)||(r.installing&&r.installing.scriptURL)||(r.waiting&&r.waiting.scriptURL)||"",state:(r.active&&r.active.state)||(r.installing&&r.installing.state)||(r.waiting&&r.waiting.state)||"none"}}),
    controller:n.serviceWorker&&n.serviceWorker.controller?n.serviceWorker.controller.scriptURL:null,registrationError:regError||null,promptReady:!!deferredPrompt
  },null,2);
}
async function install(){
  if(!deferredPrompt){alert("لم يصل beforeinstallprompt حتى الآن. إذا كان التثبيت متاحًا في Chrome استخدم القائمة ⋮.");return}
  try{
    await deferredPrompt.prompt();
    const choice=await deferredPrompt.userChoice;
    console.info("Dizal install choice",choice);
    $("details").textContent+="\n\nInstall choice: "+JSON.stringify(choice);
    deferredPrompt=null;
    renderButton();
  }catch(e){$("details").textContent+="\n\nInstall error: "+String(e)}
}
function renderButton(){$("install").textContent=deferredPrompt?"تجربة التثبيت الآن":"تجربة التثبيت (الحدث غير جاهز)"}
$("refresh").addEventListener("click",run);
$("install").addEventListener("click",install);
renderButton();
run();
setTimeout(run,10000);
})();