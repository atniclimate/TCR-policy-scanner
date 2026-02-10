/* TCR Policy Scanner - Advocacy Packet Search Widget */
(function(){"use strict";
var TRIBES_URL="data/tribes.json";
var $=document.getElementById.bind(document);
var searchInput=$("tribe-search"),loadingEl=$("loading"),errorEl=$("error");
var cardEl=$("tribe-card"),tribeName=$("tribe-name"),tribeStates=$("tribe-states");
var tribeEcoregion=$("tribe-ecoregion"),downloadLink=$("download-link"),packetStatus=$("packet-status");
var tribeMap={};
function init(){
  fetch(TRIBES_URL).then(function(r){
    if(!r.ok)throw new Error("HTTP "+r.status);return r.json();
  }).then(function(data){
    var names=[];
    data.tribes.forEach(function(t){tribeMap[t.name]=t;names.push(t.name)});
    if(typeof Awesomplete!=="undefined")
      new Awesomplete(searchInput,{list:names,minChars:2,maxItems:15,autoFirst:true});
    loadingEl.hidden=true;searchInput.disabled=false;searchInput.focus();
  }).catch(function(err){
    loadingEl.hidden=true;errorEl.hidden=false;
    errorEl.textContent="Failed to load Tribe data. Please try again later.";
    if(typeof console!=="undefined")console.error("Failed to load tribes.json:",err);
  });
}
function showCard(tribe){
  tribeName.textContent=tribe.name;
  tribeStates.textContent=tribe.states.join(", ");
  tribeEcoregion.textContent=tribe.ecoregion||"N/A";
  if(tribe.has_packet){
    downloadLink.href="tribes/"+tribe.id+".docx";
    downloadLink.setAttribute("download","");
    downloadLink.removeAttribute("aria-disabled");
    downloadLink.setAttribute("aria-label","Download advocacy packet for "+tribe.name);
    downloadLink.textContent="Download Report";
    packetStatus.textContent="Packet available ("+tribe.file_size_kb+" KB)";
  }else{
    downloadLink.removeAttribute("href");downloadLink.removeAttribute("download");
    downloadLink.setAttribute("aria-disabled","true");
    downloadLink.setAttribute("aria-label","Packet not yet available");
    downloadLink.textContent="Packet Not Yet Available";
    packetStatus.textContent="This packet has not been generated yet. Check back soon.";
  }
  cardEl.hidden=false;
}
searchInput.addEventListener("awesomplete-selectcomplete",function(evt){
  var name=evt.text&&evt.text.value?evt.text.value:evt.text;
  var tribe=tribeMap[name];if(tribe)showCard(tribe);
});
searchInput.addEventListener("keydown",function(evt){
  if(evt.key==="Escape"){cardEl.hidden=true;searchInput.value="";searchInput.setAttribute("aria-expanded","false")}
});
document.addEventListener("DOMContentLoaded",init);
})();
