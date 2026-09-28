(function(){
const sidebar=document.getElementById("sidebar");
const scrim=document.querySelector(".scrim");
const navSections=[...document.querySelectorAll("[data-nav-section]")];
const navScroll=document.getElementById("sidebarScroll");
const sectionKey="dizal.nav.openSection";
const scrollKey="dizal.nav.scrollTop";

function setSidebar(open){
  sidebar?.classList.toggle("open",open);
  scrim?.classList.toggle("d-none",!open);
  if(open && navScroll){
    requestAnimationFrame(()=>{navScroll.scrollTop=Number(localStorage.getItem(scrollKey)||0);});
  }
}
document.querySelectorAll("[data-sidebar-open]").forEach(x=>x.addEventListener("click",()=>setSidebar(true)));
document.querySelectorAll("[data-sidebar-close]").forEach(x=>x.addEventListener("click",()=>setSidebar(false)));

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

if("serviceWorker" in navigator){
  window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js?v=20260928-7",{updateViaCache:"none"}));
}
})();