from decimal import Decimal,InvalidOperation
import math
from flask import Flask,render_template,redirect,request,url_for,send_from_directory,Response
from flask_login import current_user
from .config import Config
from .extensions import db,migrate,csrf,security

def create_app(config_object=None):
    app=Flask(__name__)
    app.config.from_object(Config)
    if isinstance(config_object,dict):
        app.config.from_mapping(config_object)
    elif config_object is not None:
        app.config.from_object(config_object)
    def clean_number(value):
        if value is None or value == "":
            return ""
        try:
            number=Decimal(str(value).replace(",",""))
            if not number.is_finite():
                return value
            text=format(number,"f")
            if "." in text:
                text=text.rstrip("0").rstrip(".")
            return text or "0"
        except (InvalidOperation,ValueError,TypeError):
            return value

    def display_finalize(value):
        if isinstance(value,(Decimal,float)) and not isinstance(value,bool):
            if isinstance(value,float) and not math.isfinite(value):
                return value
            return clean_number(value)
        return value

    app.jinja_env.filters["clean_number"]=clean_number
    app.jinja_env.finalize=display_finalize

    db.init_app(app)
    migrate.init_app(app,db)
    csrf.init_app(app)

    from flask_security import SQLAlchemyUserDatastore
    from .models import User,Role
    security.init_app(app,SQLAlchemyUserDatastore(db,User,Role))

    from .context import register_context
    register_context(app)

    from .blueprints.auth import auth_bp
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.settings import settings_bp
    from .blueprints.employees import employees_bp
    from .blueprints.cashbox import cashbox_bp
    from .blueprints.capital import capital_bp
    from .blueprints.assets import assets_bp
    from .blueprints.fuel import fuel_bp
    from .blueprints.farmers import farmers_bp
    from .blueprints.sales import sales_bp
    from .blueprints.expenses import expenses_bp
    from .blueprints.settlements import settlements_bp
    from .blueprints.reports import reports_bp
    from .blueprints.documents import documents_bp
    from .blueprints.notifications import notifications_bp
    from .blueprints.audit import audit_bp
    from .blueprints.roles import roles_bp
    from .blueprints.whatsapp import whatsapp_bp
    from .blueprints.media import media_bp

    for blueprint in (
        auth_bp,dashboard_bp,settings_bp,employees_bp,cashbox_bp,capital_bp,
        assets_bp,fuel_bp,farmers_bp,sales_bp,expenses_bp,settlements_bp,
        reports_bp,documents_bp,notifications_bp,audit_bp,roles_bp,whatsapp_bp,media_bp
    ):
        app.register_blueprint(blueprint)

    @app.get("/")
    def root():
        return redirect(url_for("dashboard.index" if current_user.is_authenticated else "auth.login"))

    @app.get("/pwa/launch")
    def pwa_launch():
        # Session-independent so it can be safely precached as the PWA start URL.
        # /dashboard/ handles authentication/redirects after launch.
        html="""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1877F2">
<link rel="manifest" href="/manifest.webmanifest">
<title>Dizal</title>
<style>html,body{height:100%;margin:0}body{display:grid;place-items:center;background:#f6f8fc;color:#172033;font-family:Arial,sans-serif}.box{text-align:center;padding:32px}.logo{width:76px;height:76px;border-radius:22px;background:#1877F2;color:#fff;display:grid;place-items:center;margin:0 auto 18px;font-size:34px;font-weight:800}.spinner{width:24px;height:24px;border:3px solid #d9e0ec;border-top-color:#1877F2;border-radius:50%;animation:spin .8s linear infinite;margin:18px auto}@keyframes spin{to{transform:rotate(360deg)}}p{margin:0;color:#68758b;font-size:14px}</style>
</head>
<body><main class="box" aria-live="polite"><div class="logo">D</div><h1>Dizal</h1><div class="spinner" aria-hidden="true"></div><p>جاري فتح النظام…</p></main>
<script>window.setTimeout(function(){window.location.replace("/dashboard/");},150);</script>
</body></html>"""
        response=Response(html,mimetype="text/html")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/pwa/debug")
    def pwa_debug():
        html="""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1877F2">
<link rel="manifest" href="/manifest.webmanifest?v=20260930-5">
<title>Dizal · تشخيص PWA</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",Tahoma,Arial,sans-serif;color:#172033;background:#f4f7fb}
*{box-sizing:border-box}
body{margin:0;padding:16px}
main{max-width:760px;margin:0 auto}
.card{background:#fff;border:1px solid #e0e7f0;border-radius:18px;padding:16px;margin-bottom:12px;box-shadow:0 5px 18px rgba(20,35,65,.05)}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:17px;margin:0 0 12px}
p{color:#67748a;margin:0 0 12px;line-height:1.7}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.item{border:1px solid #e5ebf3;border-radius:12px;padding:10px;background:#fbfcfe;min-width:0}
.item b{display:block;font-size:12px;color:#657287;margin-bottom:5px}
.item span{display:block;font-size:14px;word-break:break-word}
.ok{color:#187a45;font-weight:800}.bad{color:#b42318;font-weight:800}.warn{color:#9a6700;font-weight:800}
button{border:0;border-radius:12px;background:#1877F2;color:#fff;font:inherit;font-weight:800;padding:11px 14px;margin:4px;cursor:pointer}
button.secondary{background:#eef3fb;color:#24334d}
pre{white-space:pre-wrap;word-break:break-word;background:#111827;color:#e5eefc;border-radius:12px;padding:12px;font-size:12px;direction:ltr;text-align:left;overflow:auto}
small{color:#77849a}
.icon-test{display:flex;align-items:center;gap:12px;padding:10px;border:1px solid #e5ebf3;border-radius:12px;margin:7px 0}
.icon-test img{width:56px;height:56px;object-fit:contain;border-radius:12px;background:#f2f5fa}
@media(max-width:560px){.grid{grid-template-columns:1fr}body{padding:10px}}
</style>
</head>
<body>
<main>
<section class="card">
<h1>تشخيص Dizal PWA</h1>
<p>هذه الصفحة تجمع حالة التثبيت والـManifest والـService Worker من <b>هذا الجهاز نفسه</b> دون الحاجة إلى كمبيوتر.</p>
<div>
<button id="refresh">إعادة الفحص</button>
<button class="secondary" id="install">تجربة التثبيت</button>
</div>
</section>
<section class="card"><h2>الحالة الأساسية</h2><div class="grid" id="state"></div></section>
<section class="card"><h2>فحص الملفات</h2><div id="resources"></div></section>
<section class="card"><h2>Service Worker</h2><div id="sw"></div></section>
<section class="card"><h2>الأيقونات</h2><div id="icons"></div></section>
<section class="card"><h2>تفاصيل المتصفح والخطأ</h2><pre id="details">جاري الفحص…</pre></section>
</main>
<script>
let deferredPrompt=null;
window.addEventListener("beforeinstallprompt",(event)=>{
  event.preventDefault();
  deferredPrompt=event;
  render();
  console.info("Dizal debug: beforeinstallprompt fired",event.platforms||[]);
});
window.addEventListener("appinstalled",()=>{deferredPrompt=null;render();});
const $=(id)=>document.getElementById(id);
const esc=(v)=>String(v??"").replace(/[&<>"]/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function valueCell(label,value,cls=""){return '<div class="item"><b>'+esc(label)+'</b><span class="'+cls+'">'+esc(value)+'</span></div>';}
function bool(v){return v?'<span class="ok">✅ نعم</span>':'<span class="bad">❌ لا</span>'}
async function fetchInfo(url){
  try{
    const started=performance.now();
    const response=await fetch(url,{cache:"no-store",credentials:"same-origin"});
    const ms=Math.round(performance.now()-started);
    const text=await response.text();
    return {ok:response.ok,status:response.status,statusText:response.statusText,contentType:response.headers.get("content-type")||"",serviceWorkerAllowed:response.headers.get("service-worker-allowed")||"",bytes:text.length,timeMs:ms,text};
  }catch(error){return {ok:false,error:String(error)}}
}
async function checkImage(url,expected){
  return new Promise(resolve=>{
    const img=new Image();
    const started=performance.now();
    img.onload=()=>resolve({ok:true,naturalWidth:img.naturalWidth,naturalHeight:img.naturalHeight,timeMs:Math.round(performance.now()-started),expected,url});
    img.onerror=()=>resolve({ok:false,expected,url,error:"تعذر تحميل الصورة"});
    img.src=url+(url.includes("?")?"&":"?")+"debug="+Date.now();
  });
}
async function run(){
  const nav=navigator;
  const modes={
    standalone:window.matchMedia("(display-mode: standalone)").matches,
    fullscreen:window.matchMedia("(display-mode: fullscreen)").matches,
    minimalUi:window.matchMedia("(display-mode: minimal-ui)").matches
  };
  const manifestInfo=await fetchInfo("/manifest.webmanifest?v=20260930-5");
  let manifest=null;
  let manifestRaw=null;
  if(manifestInfo.ok){
    try{manifest=JSON.parse(manifestInfo.text);manifestRaw=JSON.stringify(manifest,null,2)}catch(error){manifestRaw="JSON parse error: "+error}
  }
  const swInfo=await fetchInfo("/sw.js?v=20260930-5");
  let regList=[];
  let registrationError="";
  if("serviceWorker" in nav){
    try{
      const regs=await nav.serviceWorker.getRegistrations();
      regList=regs.map(r=>({scope:r.scope,scriptURL:r.active?.scriptURL||r.installing?.scriptURL||r.waiting?.scriptURL||"",state:r.active?.state||r.installing?.state||r.waiting?.state||"none"}));
    }catch(error){registrationError=String(error)}
  }
  let registration=null;
  try{
    if("serviceWorker" in nav){
      registration=await nav.serviceWorker.register("/sw.js?v=20260930-5",{scope:"/",updateViaCache:"none"});
      await registration.update().catch(()=>{});
    }
  }catch(error){registrationError=registrationError||String(error)}
  const icons=[];
  if(manifest?.icons){
    for(const icon of manifest.icons.slice(0,4)) icons.push(await checkImage(icon.src,icon.sizes||"unknown"));
  }
  const promptState=deferredPrompt?"جاهز":(modes.standalone?"مثبت/وضع مستقل":"غير جاهز حتى الآن");
  $("state").innerHTML=[
    valueCell("HTTPS / secureContext",window.isSecureContext?"✅ نعم":"❌ لا",window.isSecureContext?"ok":"bad"),
    valueCell("Service Worker API","serviceWorker" in nav?"✅ نعم":"❌ لا","serviceWorker" in nav?"ok":"bad"),
    valueCell("SW Controller",nav.serviceWorker?.controller?.scriptURL||"❌ لا يوجد",nav.serviceWorker?.controller?"ok":"warn"),
    valueCell("beforeinstallprompt",promptState,deferredPrompt?"ok":"warn"),
    valueCell("Standalone",modes.standalone?"✅ نعم":"لا",modes.standalone?"ok":""),
    valueCell("Online",nav.onLine?"✅ نعم":"❌ لا",nav.onLine?"ok":"bad"),
    valueCell("Android",/Android/i.test(nav.userAgent)?"✅ نعم":"لا",/Android/i.test(nav.userAgent)?"ok":""),
    valueCell("Manifest link",document.querySelector('link[rel="manifest"]')?"✅ موجود":"❌ غير موجود",document.querySelector('link[rel="manifest"]')?"ok":"bad")
  ].join("");
  $("resources").innerHTML=[
    valueCell("Manifest HTTP",manifestInfo.ok?"✅ "+manifestInfo.status+" · "+manifestInfo.contentType:"❌ "+(manifestInfo.error||manifestInfo.status),manifestInfo.ok?"ok":"bad"),
    valueCell("SW HTTP",swInfo.ok?"✅ "+swInfo.status+" · "+swInfo.contentType:"❌ "+(swInfo.error||swInfo.status),swInfo.ok?"ok":"bad"),
    valueCell("SW-Allowed",swInfo.serviceWorkerAllowed||"غير موجود",swInfo.serviceWorkerAllowed==="/"?"ok":"warn"),
    valueCell("start_url",manifest?.start_url||"غير موجود",manifest?.start_url?"ok":"bad"),
    valueCell("scope",manifest?.scope||"غير موجود",manifest?.scope==="/"?"ok":"warn"),
    valueCell("display",manifest?.display||"غير موجود",manifest?.display==="standalone"?"ok":"warn")
  ].join("");
  const regsHtml=regList.length
    ? '<div class="grid">'+regList.map(r=>'<div class="item"><b>Registration</b><span>scope: '+esc(r.scope)+'<br>script: '+esc(r.scriptURL)+'<br>state: '+esc(r.state)+'</span></div>').join("")+'</div>'
    : '<div class="item"><span class="warn">لا توجد تسجيلات ظاهرة حاليًا.</span></div>';
  $("sw").innerHTML=regsHtml+'<div class="grid" style="margin-top:8px">'+
    valueCell("Registration الحالي",registration?.active?.state||registration?.installing?.state||registration?.waiting?.state||"غير معروف",registration?"ok":"warn")+
    valueCell("خطأ التسجيل",registrationError||"لا يوجد","")+
    '</div>';
  $("icons").innerHTML=icons.length?icons.map((i,idx)=>
    '<div class="icon-test"><img src="'+esc(i.url)+'" alt=""><div><b>Icon '+(idx+1)+'</b><br><span class="'+(i.ok?"ok":"bad")+'">'+(i.ok?"✅ "+i.naturalWidth+"×"+i.naturalHeight:"❌ "+esc(i.error))+'</span><br><small>المطلوب: '+esc(i.expected)+'</small></div></div>'
  ).join(""):'<div class="item"><span class="warn">لم يمكن استخراج الأيقونات من الـManifest.</span></div>';
  $("details").textContent=JSON.stringify({
    userAgent:nav.userAgent,
    userAgentData:nav.userAgentData?{mobile:nav.userAgentData.mobile,platform:nav.userAgentData.platform,brands:nav.userAgentData.brands}:null,
    platform:nav.platform||"",
    language:nav.language,
    online:nav.onLine,
    secureContext:window.isSecureContext,
    location:location.href,
    manifest:manifest||null,
    manifestRaw:manifestRaw,
    manifestResult:{status:manifestInfo.status,contentType:manifestInfo.contentType,bytes:manifestInfo.bytes,timeMs:manifestInfo.timeMs,error:manifestInfo.error||null},
    swResult:{status:swInfo.status,contentType:swInfo.contentType,serviceWorkerAllowed:swInfo.serviceWorkerAllowed,bytes:swInfo.bytes,timeMs:swInfo.timeMs,error:swInfo.error||null},
    registrations:regList,
    controller:nav.serviceWorker?.controller?.scriptURL||null,
    registrationError:registrationError||null,
    promptReady:!!deferredPrompt,
    displayModes:modes
  },null,2);
}
$("refresh").addEventListener("click",run);
$("install").addEventListener("click",async()=>{
  if(deferredPrompt){
    try{
      await deferredPrompt.prompt();
      const choice=await deferredPrompt.userChoice;
      $("details").textContent+="

Install choice: "+JSON.stringify(choice);
      deferredPrompt=null;
      render();
    }catch(error){$("details").textContent+="

Install error: "+String(error)}
  }else alert("beforeinstallprompt لم يصل بعد. استخدم قائمة Chrome ⋮ ثم «تثبيت التطبيق» إن ظهرت.");
});
function render(){$("install").textContent=deferredPrompt?"تجربة التثبيت الآن":"تجربة التثبيت (الحدث غير جاهز)";}
render();
run();
setTimeout(run,12000);
</script>
</body>
</html>"""
        response=Response(html,mimetype="text/html")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/manifest.webmanifest")
    def web_manifest():
        response=send_from_directory(app.static_folder,"manifest.webmanifest",mimetype="application/manifest+json")
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.get("/sw.js")
    def service_worker():
        response=send_from_directory(app.static_folder,"sw.js",mimetype="application/javascript")
        response.headers["Service-Worker-Allowed"]="/"
        response.headers["Cache-Control"]="no-cache, no-store, must-revalidate"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response

    @app.errorhandler(401)
    def unauthorized(_error):
        return redirect(url_for("auth.login", next=request.full_path))

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"),403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"),404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"),500

    @app.get("/health")
    def health():
        from sqlalchemy import text
        try:
            db.session.execute(text("SELECT 1"))
            status="ok"
        except Exception:
            status="error"
        return {"status":status,"database":status,"version":"integration-2026-09"}

    return app
