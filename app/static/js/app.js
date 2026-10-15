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


// Water POS searchable selects. Employee CSS uses a separate body class and
// never styles the employee home, navigation tree or bottom navigation.
(function(){
  const body=document.body;
  const on=body.classList.contains("admin-theme-water-pos") || body.classList.contains("employee-controls-water-pos");
  const selector=on
    ? "select:not([multiple]):not([data-native-select='true']):not(.smart-select-native)"
    : "select[data-searchable='true']:not([multiple]):not([data-native-select='true']):not(.smart-select-native)";
  document.querySelectorAll(selector).forEach(function(select){
    if(select.dataset.searchEnhanced==="true" || !select.parentElement) return;
    select.dataset.searchEnhanced="true";
    const wrapper=document.createElement("div"); wrapper.className="smart-select"; wrapper.dataset.selectName=select.name||"";
    select.parentElement.insertBefore(wrapper,select); wrapper.appendChild(select);
    select.classList.add("smart-select-native"); select.setAttribute("aria-hidden","true"); select.tabIndex=-1;
    const trigger=document.createElement("button"); trigger.type="button"; trigger.className="smart-select-trigger";
    trigger.setAttribute("aria-expanded","false"); trigger.setAttribute("aria-haspopup","listbox");
    const label=(select.getAttribute("aria-label") || Array.from(select.labels||[]).map(l=>l.textContent.trim()).join(" ") || "اختيار").replace(/\s+/g," ").trim();
    trigger.setAttribute("aria-label",label+"، فتح القائمة");
    const menu=document.createElement("div"); menu.className="smart-select-menu"; menu.hidden=true;
    const search=document.createElement("input"); search.type="search"; search.className="smart-select-search";
    search.placeholder="بحث فوري..."; search.setAttribute("aria-label","بحث في الخيارات"); search.autocomplete="off";
    const options=document.createElement("div"); options.className="smart-select-options"; options.setAttribute("role","listbox");
    menu.append(search,options); wrapper.append(trigger,menu);
    function syncValue(){
      const selected=select.options[select.selectedIndex]; trigger.textContent=selected?selected.textContent.trim():"اختر...";
      trigger.disabled=select.disabled; trigger.setAttribute("aria-required",String(select.required));
      options.querySelectorAll("button").forEach(function(button){
        const selectedNow=button.dataset.value===select.value;
        button.classList.toggle("is-selected",selectedNow); button.setAttribute("aria-selected",String(selectedNow));
        button.disabled=button.dataset.disabled==="true";
      });
    }
    function applySearch(){
      const needle=search.value.trim().toLocaleLowerCase();
      options.querySelectorAll("button").forEach(button=>{button.hidden=!button.textContent.toLocaleLowerCase().includes(needle);});
    }
    function renderOptions(){
      options.replaceChildren();
      Array.from(select.options).forEach(function(option){
        const button=document.createElement("button"); button.type="button"; button.className="smart-select-option";
        button.textContent=option.textContent.trim(); button.dataset.value=option.value; button.dataset.disabled=String(option.disabled);
        button.setAttribute("role","option"); button.setAttribute("aria-selected",String(option.selected)); button.disabled=option.disabled;
        button.addEventListener("click",function(){
          if(option.disabled) return;
          select.value=option.value; select.dispatchEvent(new Event("change",{bubbles:true})); syncValue(); closeMenu(true);
        });
        options.appendChild(button);
      });
      syncValue(); applySearch();
    }
    function closeMenu(returnFocus){
      menu.hidden=true; trigger.setAttribute("aria-expanded","false"); wrapper.classList.remove("is-open");
      if(returnFocus) trigger.focus();
    }
    function openMenu(){
      document.querySelectorAll(".smart-select.is-open").forEach(function(other){
        if(other===wrapper) return;
        other.classList.remove("is-open");
        const m=other.querySelector(".smart-select-menu"),t=other.querySelector(".smart-select-trigger");
        if(m)m.hidden=true; if(t)t.setAttribute("aria-expanded","false");
      });
      renderOptions(); menu.hidden=false; wrapper.classList.add("is-open");
      trigger.setAttribute("aria-expanded","true"); search.value=""; applySearch(); search.focus();
    }
    trigger.addEventListener("click",()=>menu.hidden?openMenu():closeMenu(false));
    trigger.addEventListener("keydown",function(event){
      if(["ArrowDown","Enter"," "].includes(event.key)){event.preventDefault();if(menu.hidden)openMenu();else search.focus();}
    });
    search.addEventListener("input",applySearch);
    search.addEventListener("keydown",function(event){
      if(event.key==="Escape"){event.preventDefault();closeMenu(true);}
      if(event.key==="ArrowDown"){event.preventDefault();options.querySelector("button:not([hidden]):not(:disabled)")?.focus();}
    });
    select.addEventListener("change",renderOptions);
    select.form?.addEventListener("reset",()=>window.setTimeout(renderOptions,0));
    document.addEventListener("click",event=>{if(!wrapper.contains(event.target))closeMenu(false);});
    document.addEventListener("invalid",function(event){if(event.target===select){event.preventDefault();openMenu();trigger.focus();}},true);
    const observer=new MutationObserver(renderOptions);
    observer.observe(select,{childList:true,subtree:true,attributes:true,attributeFilter:["disabled","label","selected"]});
    renderOptions();
  });
})();

(function(){
  document.querySelectorAll("dialog.app-form-dialog").forEach(function(dialog){
    dialog.querySelectorAll("[data-close-dialog]").forEach(button=>button.addEventListener("click",()=>dialog.close()));
    dialog.addEventListener("click",function(event){
      if(event.target!==dialog)return;
      const r=dialog.getBoundingClientRect();
      if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();
    });
    if(dialog.dataset.autoOpen==="true" && typeof dialog.showModal==="function")dialog.showModal();
  });
  document.addEventListener("click",function(event){
    const button=event.target.closest?.("[data-open-dialog]");
    if(!button)return;
    const dialog=document.getElementById(button.dataset.openDialog);
    if(dialog && typeof dialog.showModal==="function")dialog.showModal();
  });
})();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

})();
