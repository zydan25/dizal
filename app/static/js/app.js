(function(){
const sidebar=document.getElementById("sidebar");
const scrim=document.querySelector(".scrim");
const navSections=[...document.querySelectorAll("[data-nav-section]")];
const navScroll=document.getElementById("sidebarScroll");
const sectionKey="dizal.nav.openSection";
const scrollKey="dizal.nav.scrollTop";

function setSidebar(open){
  if(!sidebar)return;
  sidebar.classList.toggle("open",open);
  sidebar.setAttribute("aria-hidden",open?"false":"true");
  document.body.classList.toggle("sidebar-open",open);
  document.querySelectorAll("[data-sidebar-open]").forEach(btn=>btn.setAttribute("aria-expanded",open?"true":"false"));
  if(scrim){
    scrim.classList.toggle("d-none",!open);
    scrim.setAttribute("aria-hidden",open?"false":"true");
  }
  if(open && navScroll){
    requestAnimationFrame(()=>{navScroll.scrollTop=Number(localStorage.getItem(scrollKey)||0);});
  }
}
document.addEventListener("click",event=>{
  const opener=event.target.closest?.("[data-sidebar-open]");
  if(opener){event.preventDefault();setSidebar(true);return;}
  const closer=event.target.closest?.("[data-sidebar-close]");
  if(closer){event.preventDefault();setSidebar(false);}
});
document.addEventListener("keydown",event=>{if(event.key==="Escape" && sidebar?.classList.contains("open"))setSidebar(false);});
setSidebar(false);

const storedSection=localStorage.getItem(sectionKey) || "";
function applySection(section,open,persist){
  navSections.forEach(other=>{
    const body=other.querySelector(".nav-children");
    const toggle=other.querySelector("[data-tree-toggle]");
    const isOpen=open && other===section;
    other.classList.toggle("closed",!isOpen);
    if(body) body.style.display=isOpen?"":"none";
    toggle?.setAttribute("aria-expanded",isOpen?"true":"false");
  });
  if(persist){
    if(open && section) localStorage.setItem(sectionKey,section.dataset.navSection || "");
    else localStorage.removeItem(sectionKey);
  }
}
const savedTarget=navSections.find(section=>section.dataset.navSection===storedSection);
applySection(savedTarget || null,!!savedTarget,false);

navSections.forEach(section=>{
  const toggle=section.querySelector("[data-tree-toggle]");
  toggle?.addEventListener("click",()=>{
    const isCurrentlyOpen=!section.classList.contains("closed");
    applySection(section,!isCurrentlyOpen,true);
  });
});

navScroll?.addEventListener("scroll",()=>{
  clearTimeout(navScroll._dizalScrollTimer);
  navScroll._dizalScrollTimer=setTimeout(()=>localStorage.setItem(scrollKey,String(navScroll.scrollTop)),120);
},{passive:true});


const AR_ONES=["صفر","واحد","اثنان","ثلاثة","أربعة","خمسة","ستة","سبعة","ثمانية","تسعة"];
const AR_TEENS=["عشرة","أحد عشر","اثنا عشر","ثلاثة عشر","أربعة عشر","خمسة عشر","ستة عشر","سبعة عشر","ثمانية عشر","تسعة عشر"];
const AR_TENS=["","","عشرون","ثلاثون","أربعون","خمسون","ستون","سبعون","ثمانون","تسعون"];
const AR_HUNDREDS=["","مائة","مائتان","ثلاثمائة","أربعمائة","خمسمائة","ستمائة","سبعمائة","ثمانمائة","تسعمائة"];
function arBelow100(n){if(n<10)return AR_ONES[n];if(n<20)return AR_TEENS[n-10];const t=Math.floor(n/10),o=n%10;return o?AR_ONES[o]+" و"+AR_TENS[t]:AR_TENS[t];}
function arUnder1000(n){if(n<100)return arBelow100(n);const h=Math.floor(n/100),r=n%100;return r?AR_HUNDREDS[h]+" و"+arBelow100(r):AR_HUNDREDS[h];}
function arIntWords(n){
 n=Math.floor(Math.abs(n));
 if(n===0)return "صفر";
 const parts=[];
 const millions=Math.floor(n/1000000);n%=1000000;
 const thousands=Math.floor(n/1000);n%=1000;
 if(millions){if(millions===1)parts.push("مليون");else if(millions===2)parts.push("مليونان");else if(millions<10)parts.push(AR_ONES[millions]+" ملايين");else parts.push(arUnder1000(millions)+" مليون");}
 if(thousands){if(thousands===1)parts.push("ألف");else if(thousands===2)parts.push("ألفان");else if(thousands<10)parts.push(AR_ONES[thousands]+" آلاف");else if(thousands<100)parts.push(arBelow100(thousands)+" ألف");else parts.push(arUnder1000(thousands)+" ألف");}
 if(n)parts.push(arUnder1000(n));
 return parts.join(" و");
}
function arNumberWords(value){
 const n=Number(String(value).replace(/,/g,""));
 if(!Number.isFinite(n))return "";
 const sign=n<0?"سالب ":"",a=Math.abs(n),i=Math.floor(a),f=Math.round((a-i)*1000);
 let out=sign+arIntWords(i);
 if(f){const fs=String(f).padStart(3,"0").replace(/0+$/,"");out+=" فاصلة "+fs.split("").map(function(d){return AR_ONES[Number(d)];}).join(" ");}
 return out;
}
function unitWords(value,unit){
 const n=Number(value);
 if(!Number.isFinite(n))return "";
 if(unit==="drum"){
   if(Number.isInteger(n)&&n===1)return "دبة واحدة";
   if(Number.isInteger(n)&&n===2)return "دبتان";
   if(Number.isInteger(n)&&n>=3&&n<=10){const f=["","واحدة","اثنتان","ثلاث","أربع","خمس","ست","سبع","ثمان","تسع","عشر"];return f[n]+" دباب";}
   return arNumberWords(n)+" دبة";
 }
 if(unit==="liter")return arNumberWords(n)+" لتر";
 return arNumberWords(n);
}
function guessUnit(input){
 if(input.dataset.unit)return input.dataset.unit;
 const name=(input.name||"").toLowerCase();
 if(name.indexOf("drum")>=0)return "drum";
 if(name.indexOf("liter")>=0||name.indexOf("capacity")>=0)return "liter";
 return "currency";
}
function installNumberWords(){
 const currency=document.body.dataset.currency||"ريال";
 const drumLiters=Number(document.body.dataset.drumLiters||20);
 document.querySelectorAll('.mobile-form input[type="number"]:not([data-number-words-ignore])').forEach(function(input){
   if(input.dataset.wordsInstalled)return;
   input.dataset.wordsInstalled="1";
   const hint=document.createElement("div");
   hint.className="number-words-hint";
   hint.setAttribute("aria-live","polite");
   const parent=input.parentElement;
   if(!parent)return;
   parent.appendChild(hint);
   function update(){
     if(!input.value){hint.textContent="";hint.classList.remove("show");return;}
     const unit=guessUnit(input);
     let text=unit==="currency"?arNumberWords(input.value)+" "+currency:unitWords(input.value,unit);
     if(unit==="drum"){
       const liters=Number(input.value)*drumLiters;
       if(Number.isFinite(liters))text+=" · "+String(liters).replace(/\.0+$/,"")+" لتر";
     }
     hint.textContent=text;
     hint.classList.add("show");
   }
   input.addEventListener("input",update);
   input.addEventListener("change",update);
   update();
 });
}
window.DizalNumberWords={installNumberWords,arNumberWords,unitWords};
installNumberWords();

function dizalToast(message,type){
  const old=document.querySelector(".dizal-toast"); old?.remove();
  const toast=document.createElement("div");
  toast.className="dizal-toast "+(type||"info");
  toast.innerHTML='<i class="bi '+(type==="success"?"bi-check-circle":"bi-wifi-off")+'"></i><span></span>';
  toast.querySelector("span").textContent=message;
  document.body.appendChild(toast);
  requestAnimationFrame(()=>toast.classList.add("show"));
  setTimeout(()=>{toast.classList.remove("show");setTimeout(()=>toast.remove(),220);},4200);
}
const offlineBanner=document.getElementById("offline-banner");
function updateNetworkState(){
  const offline=!navigator.onLine;
  if(offlineBanner)offlineBanner.hidden=!offline;
  document.documentElement.classList.toggle("is-offline",offline);
}
window.addEventListener("online",()=>{updateNetworkState();dizalToast("عاد الاتصال بالإنترنت ويمكن تنفيذ العمليات الآن.","success");});
window.addEventListener("offline",()=>{updateNetworkState();dizalToast("انقطع الاتصال بالإنترنت. لن يتم إرسال أي عملية حتى يعود الاتصال.","info");});
updateNetworkState();

let deferredInstallPrompt=null;
let appInstalledSignal=false;
const installButton=document.querySelector("[data-install-app]");
const installText=document.getElementById("global-install-text");
const installState=document.getElementById("global-install-state");
const isStandalone=()=>window.matchMedia?.("(display-mode: standalone)").matches || window.navigator.standalone===true;
const isIos=()=>/iphone|ipad|ipod/i.test(navigator.userAgent);
const isAndroid=()=>/android/i.test(navigator.userAgent);

function pwaState(){
  return {
    secureContext:window.isSecureContext===true,
    standalone:isStandalone(),
    serviceWorkerSupported:"serviceWorker" in navigator,
    controlled:!!navigator.serviceWorker?.controller,
    installPromptReady:!!deferredInstallPrompt,
    installedSignal:appInstalledSignal,
  };
}
window.DizalPWA={state:pwaState};

function setInstallState(text){
  if(installState)installState.textContent=text;
}
function refreshInstallButton(){
  if(!installButton)return;
  if(isStandalone()){
    installButton.hidden=true;
    return;
  }
  installButton.hidden=false;
  installButton.disabled=false;
  installButton.classList.toggle("is-ready",!!deferredInstallPrompt);
  if(deferredInstallPrompt){
    if(installText)installText.textContent="تثبيت Dizal الآن";
    setInstallState("المتصفح جهّز التثبيت الرسمي لهذا الجهاز.");
  }else if(isIos()){
    if(installText)installText.textContent="إضافة Dizal للشاشة";
    setInstallState("في iPhone/iPad استخدم مشاركة Safari ثم «إضافة إلى الشاشة الرئيسية».");
  }else if(isAndroid()){
    if(installText)installText.textContent="تثبيت Dizal كتطبيق";
    setInstallState("يمكنك أيضًا استخدام قائمة المتصفح ⋮ ثم «تثبيت التطبيق».");
  }else{
    if(installText)installText.textContent="تثبيت Dizal كتطبيق";
    setInstallState("افتح قائمة المتصفح واختر «تثبيت التطبيق» عند توفرها.");
  }
}

async function triggerInstall(){
  if(isStandalone()){
    refreshInstallButton();
    dizalToast("Dizal مثبت كتطبيق بالفعل.","success");
    return;
  }
  if(!deferredInstallPrompt){
    refreshInstallButton();
    if(isIos()){
      dizalToast("افتح مشاركة Safari ثم اختر «إضافة إلى الشاشة الرئيسية».","info");
    }else{
      dizalToast("لم يرسل المتصفح نافذة التثبيت المباشر. استخدم قائمة المتصفح ثم اختر «تثبيت التطبيق».","info");
    }
    return;
  }
  const event=deferredInstallPrompt;
  deferredInstallPrompt=null;
  refreshInstallButton();
  try{
    const choice=await event.prompt();
    if(choice?.outcome==="accepted"){
      setInstallState("تم قبول التثبيت. ننتظر تأكيد النظام…");
      dizalToast("تم قبول طلب التثبيت. سيكمل المتصفح تثبيت التطبيق.","success");
    }else{
      setInstallState("يمكنك إعادة المحاولة من الزر أو قائمة المتصفح.");
      dizalToast("تم إلغاء التثبيت.");
    }
  }catch(error){
    setInstallState("تعذر فتح نافذة التثبيت المباشر؛ استخدم قائمة المتصفح.");
    console.error("Dizal install prompt error",error);
  }
}

window.addEventListener("beforeinstallprompt",event=>{
  event.preventDefault();
  deferredInstallPrompt=event;
  refreshInstallButton();
});
window.addEventListener("appinstalled",()=>{
  appInstalledSignal=true;
  deferredInstallPrompt=null;
  if(installButton)installButton.hidden=true;
  setInstallState("تم تثبيت Dizal بنجاح.");
  dizalToast("تم تثبيت Dizal كتطبيق على الشاشة.","success");
});

installButton?.addEventListener("click",triggerInstall);
refreshInstallButton();

async function registerDizalServiceWorker(){
  if(!("serviceWorker" in navigator))return;
  try{
    const registration=await navigator.serviceWorker.register("/sw.js?v=20260930-4",{
      scope:"/",
      updateViaCache:"none"
    });
    registration.update().catch(()=>{});
    window.DizalPWA.registration=registration;
    window.DizalPWA.state=pwaState;
  }catch(error){
    window.DizalPWA.error=String(error);
    window.DizalPWA.state=pwaState;
    console.error("Dizal service worker registration failed",error);
  }
}
if(document.readyState==="loading"){
  document.addEventListener("DOMContentLoaded",registerDizalServiceWorker,{once:true});
}else{
  registerDizalServiceWorker();
}

document.addEventListener("submit",event=>{
  if(navigator.onLine!==false)return;
  const form=event.target;
  if(form.matches('form[action*="/auth/logout"]'))return;
  event.preventDefault();
  dizalToast("لا يوجد اتصال بالإنترنت. أعد المحاولة بعد عودة الاتصال.");
});

})();