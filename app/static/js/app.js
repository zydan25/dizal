(function(){
const sidebar=document.getElementById("sidebar");
const scrim=document.querySelector(".scrim");
function setSidebar(open){sidebar?.classList.toggle("open",open);scrim?.classList.toggle("d-none",!open);}
document.querySelectorAll("[data-sidebar-open]").forEach(x=>x.addEventListener("click",()=>setSidebar(true)));
document.querySelectorAll("[data-sidebar-close]").forEach(x=>x.addEventListener("click",()=>setSidebar(false)));
document.querySelectorAll("[data-tree-toggle]").forEach((button,index)=>{
const section=button.closest(".nav-section"),body=button.nextElementSibling,key="dizal.nav."+index;
if(localStorage.getItem(key)==="closed"){section.classList.add("closed");body.style.display="none";}
button.addEventListener("click",()=>{const closed=section.classList.toggle("closed");body.style.display=closed?"none":"";localStorage.setItem(key,closed?"closed":"open");});
});
document.querySelectorAll(".nav-item.active").forEach(link=>{const section=link.closest(".nav-section"),body=section?.querySelector(".nav-children");if(body){section.classList.remove("closed");body.style.display="";}});
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("/static/sw.js"));}
})();