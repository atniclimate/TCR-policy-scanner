/* Tribal Climate Resilience - Program Priorities Widget */
(function(){"use strict";
var TRIBES_URL="data/tribes.json";
var $=document.getElementById.bind(document);
var searchInput=$("tribe-search"),loadingEl=$("loading"),errorEl=$("error");
var cardEl=$("tribe-card"),tribeName=$("tribe-name"),tribeStates=$("tribe-states");
var tribeEcoregion=$("tribe-ecoregion"),tribeActions=$("tribe-actions"),packetStatus=$("packet-status");
var regionsSection=$("regions-section"),regionsList=$("regions-list");
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
    if(data.regions&&data.regions.length>0)renderRegions(data.regions);
  }).catch(function(err){
    loadingEl.hidden=true;errorEl.hidden=false;
    errorEl.textContent="Failed to load Tribe data. Please try again later.";
    if(typeof console!=="undefined")console.error("Failed to load tribes.json:",err);
  });
}
function escapeText(s){
  var d=document.createElement("div");d.textContent=s;return d.textContent;
}
function makeDownloadBtn(href,label,ariaLabel,extraClass){
  var a=document.createElement("a");
  a.href=href;a.setAttribute("download","");
  a.className="btn-download"+(extraClass?" "+extraClass:"");
  a.setAttribute("aria-label",ariaLabel);
  a.textContent=label;
  return a;
}
function showCard(tribe){
  tribeName.textContent=tribe.name;
  tribeStates.textContent=tribe.states.join(", ");
  tribeEcoregion.textContent=tribe.ecoregion||"N/A";
  var docs=tribe.documents||{};
  var hasInternal=!!docs.internal_strategy;
  var hasCongressional=!!docs.congressional_overview;
  /* Clear previous actions */
  while(tribeActions.firstChild)tribeActions.removeChild(tribeActions.firstChild);
  /* Build action buttons using DOM methods */
  if(hasInternal){
    tribeActions.appendChild(makeDownloadBtn("tribes/"+docs.internal_strategy,"Internal Strategy (Confidential)","Download Internal Strategy for "+escapeText(tribe.name),"btn-internal"));
    tribeActions.appendChild(document.createTextNode(" "));
  }
  if(hasCongressional){
    tribeActions.appendChild(makeDownloadBtn("tribes/"+docs.congressional_overview,"Congressional Overview","Download Congressional Overview for "+escapeText(tribe.name),"btn-congressional"));
    tribeActions.appendChild(document.createTextNode(" "));
  }
  if(hasInternal&&hasCongressional){
    var bothBtn=document.createElement("a");
    bothBtn.href="#";bothBtn.className="btn-download btn-both";
    bothBtn.setAttribute("aria-label","Download both documents for "+escapeText(tribe.name));
    bothBtn.textContent="Download Both";
    bothBtn.addEventListener("click",function(e){
      e.preventDefault();
      var a1=document.createElement("a");a1.href="tribes/"+docs.internal_strategy;a1.setAttribute("download","");document.body.appendChild(a1);a1.click();document.body.removeChild(a1);
      setTimeout(function(){
        var a2=document.createElement("a");a2.href="tribes/"+docs.congressional_overview;a2.setAttribute("download","");document.body.appendChild(a2);a2.click();document.body.removeChild(a2);
      },300);
    });
    tribeActions.appendChild(bothBtn);
  }
  if(!hasInternal&&!hasCongressional){
    var span=document.createElement("span");
    span.className="btn-download";span.setAttribute("aria-disabled","true");
    span.textContent="Documents Not Yet Available";
    tribeActions.appendChild(span);
  }
  /* Status line */
  var statusP=document.createElement("p");
  statusP.className="packet-status";statusP.setAttribute("aria-live","polite");
  if(tribe.has_complete_data){
    statusP.textContent="Full data available: Internal Strategy + Congressional Overview";
  }else if(hasCongressional){
    statusP.textContent="Congressional Overview available";
  }else{
    statusP.textContent="Documents have not been generated yet. Check back soon.";
  }
  tribeActions.appendChild(statusP);
  cardEl.hidden=false;
}
function renderRegions(regions){
  if(!regions||regions.length===0)return;
  var hasAny=false;
  regions.forEach(function(r){
    var docs=r.documents||{};
    var hasInternal=!!docs.internal_strategy;
    var hasCongressional=!!docs.congressional_overview;
    if(!hasInternal&&!hasCongressional)return;
    hasAny=true;
    var card=document.createElement("div");card.className="region-card";
    var h3=document.createElement("h3");h3.className="region-name";h3.textContent=r.region_name;
    card.appendChild(h3);
    if(r.states&&r.states.length>0){
      var stP=document.createElement("p");stP.className="region-states";stP.textContent=r.states.join(", ");
      card.appendChild(stP);
    }
    var actDiv=document.createElement("div");actDiv.className="region-actions";
    if(hasInternal){
      actDiv.appendChild(makeDownloadBtn("tribes/"+docs.internal_strategy,"Internal Strategy","Download Internal Strategy for "+escapeText(r.region_name),"btn-internal btn-sm"));
      actDiv.appendChild(document.createTextNode(" "));
    }
    if(hasCongressional){
      actDiv.appendChild(makeDownloadBtn("tribes/"+docs.congressional_overview,"Congressional Overview","Download Congressional Overview for "+escapeText(r.region_name),"btn-congressional btn-sm"));
    }
    card.appendChild(actDiv);
    regionsList.appendChild(card);
  });
  if(hasAny)regionsSection.hidden=false;
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
