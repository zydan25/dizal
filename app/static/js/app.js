(function(){
const sidebar=document.getElementById("sidebar");
const scrim=document.querySelector(".scrim");
function setSidebar(open){sidebar?.classList.toggle("open",open);scrim?.classList.toggle("d-none",!open);}
document.querySelectorAll("[data-sidebar-open]").forEach(x=>x.addEventListener("click",()=>setSidebar(true)));
document.querySelectorAll("[data-sidebar-close]").forEach(x=>x.addEventListener("click",()=>setSidebar(false)));

document.querySelectorAll("[data-tree-toggle]").forEach((button,index)=>{
const section=button.closest(".nav-section"),body=button.nextElementSibling,key="dizal.nav."+index;
const active=section?.querySelector(".nav-item.active");
const stored=localStorage.getItem(key);
const shouldOpen=stored ? stored==="open" : !!active;
section?.classList.toggle("closed",!shouldOpen);
if(body) body.style.display=shouldOpen?"":"none";
button.addEventListener("click",()=>{
const closed=section.classList.toggle("closed");
body.style.display=closed?"none":"";
localStorage.setItem(key,closed?"closed":"open");
});
});

if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js?v=20260928-6",{updateViaCache:"none"}));}
})();