/**
 * Tribal Climate Resilience - Program Priorities
 *
 * Main application controller: loads tribes.json, initializes Fuse.js
 * fuzzy search, wires TribeCombobox, handles state filtering, card
 * rendering with freshness badges, descriptive download filenames,
 * and regional document rendering.
 *
 * Dependencies (loaded before this script):
 *   - fuse.min.js  (Fuse.js 7.1.0 UMD)
 *   - combobox.js  (TribeCombobox ARIA component)
 *
 * Data source:
 *   - data/tribes.json (built by scripts/build_web_index.py)
 */
(function() {
  "use strict";

  var TRIBES_URL = "data/tribes.json";

  // --- DOM element references ---
  var searchInput = document.getElementById("tribe-search");
  var listboxEl = document.getElementById("tribe-listbox");
  var statusEl = document.getElementById("search-status");
  var stateFilter = document.getElementById("state-filter");
  var loadingEl = document.getElementById("loading");
  var errorEl = document.getElementById("error");
  var cardEl = document.getElementById("tribe-card");
  var tribeName = document.getElementById("tribe-name");
  var tribeFreshness = document.getElementById("tribe-freshness");
  var tribeStates = document.getElementById("tribe-states");
  var tribeEcoregion = document.getElementById("tribe-ecoregion");
  var tribeActions = document.getElementById("tribe-actions");
  var stateResultsSection = document.getElementById("state-results");
  var stateResultsTitle = document.getElementById("state-results-title");
  var stateResultsList = document.getElementById("state-results-list");
  var regionsSection = document.getElementById("regions-section");
  var regionsList = document.getElementById("regions-list");

  // --- Data storage ---
  var allTribes = [];
  var tribeMap = {};

  // ====================================================================
  // Initialization
  // ====================================================================

  /**
   * Initialize the application: fetch data, build search index, wire UI.
   */
  function init() {
    fetch(TRIBES_URL).then(function(response) {
      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }
      return response.json();
    }).then(function(data) {
      allTribes = data.tribes || [];
      if (allTribes.length === 0) {
        showError("No Tribe data available.");
        return;
      }

      // Build lookup map by name
      for (var i = 0; i < allTribes.length; i++) {
        tribeMap[allTribes[i].name] = allTribes[i];
      }

      // Initialize Fuse.js search index
      var fuse = new Fuse(allTribes, {
        keys: [
          { name: "name", weight: 3 },
          { name: "aliases", weight: 1 },
          { name: "states", weight: 0.5 }
        ],
        threshold: 0.4,
        ignoreLocation: true,
        includeScore: true,
        includeMatches: true,
        minMatchCharLength: 2,
        shouldSort: true
      });

      // Initialize ARIA combobox
      var combobox = new TribeCombobox(searchInput, listboxEl, statusEl, fuse);
      combobox.onTribeSelected = showCard;

      // Enable search input
      searchInput.disabled = false;
      searchInput.focus();

      // Populate state filter
      populateStateFilter();

      // Render regional documents
      var regions = data.regions || [];
      renderRegions(regions);

      // Hide loading message
      loadingEl.hidden = true;

    }).catch(function(err) {
      showError("Failed to load Tribe data. Please try again later.");
      if (typeof console !== "undefined") {
        console.error("Failed to load tribes.json:", err);
      }
    });
  }

  /**
   * Show error message and hide loading indicator.
   * @param {string} message
   */
  function showError(message) {
    loadingEl.hidden = true;
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  // ====================================================================
  // State Filter
  // ====================================================================

  /**
   * Populate the state filter dropdown with sorted unique states.
   */
  function populateStateFilter() {
    var stateSet = {};
    for (var i = 0; i < allTribes.length; i++) {
      var states = allTribes[i].states || [];
      for (var j = 0; j < states.length; j++) {
        stateSet[states[j]] = true;
      }
    }

    // Sort state codes alphabetically
    var sortedStates = Object.keys(stateSet).sort();

    for (var k = 0; k < sortedStates.length; k++) {
      var opt = document.createElement("option");
      opt.value = sortedStates[k];
      opt.textContent = sortedStates[k];
      stateFilter.appendChild(opt);
    }

    // Enable and bind change handler
    stateFilter.disabled = false;
    stateFilter.addEventListener("change", onStateFilterChange);
  }

  /**
   * Handle state filter selection changes.
   */
  function onStateFilterChange() {
    var selectedState = stateFilter.value;

    if (!selectedState) {
      // "All states" selected -- hide state results
      stateResultsSection.hidden = true;
      return;
    }

    // Filter tribes by selected state
    var filtered = [];
    for (var i = 0; i < allTribes.length; i++) {
      var states = allTribes[i].states || [];
      if (states.indexOf(selectedState) !== -1) {
        filtered.push(allTribes[i]);
      }
    }

    // Sort filtered tribes alphabetically by name
    filtered.sort(function(a, b) {
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });

    // Render state results
    renderStateResults(selectedState, filtered);
  }

  /**
   * Render filtered tribes for a selected state.
   * @param {string} stateCode
   * @param {Array} tribes
   */
  function renderStateResults(stateCode, tribes) {
    // Set title
    stateResultsTitle.textContent = "Tribal Nations in " + stateCode + " (" + tribes.length + ")";

    // Clear previous results
    while (stateResultsList.firstChild) {
      stateResultsList.removeChild(stateResultsList.firstChild);
    }

    for (var i = 0; i < tribes.length; i++) {
      var tribe = tribes[i];
      var item = document.createElement("div");
      item.className = "state-tribe-item";
      item.setAttribute("tabindex", "0");
      item.setAttribute("role", "button");
      item.setAttribute("aria-label", "View " + tribe.name);

      var nameSpan = document.createElement("span");
      nameSpan.textContent = tribe.name;
      item.appendChild(nameSpan);

      var stateSpan = document.createElement("span");
      stateSpan.className = "option-state";
      stateSpan.textContent = (tribe.states || []).join(", ");
      item.appendChild(stateSpan);

      // Bind click and keyboard handlers with closure
      (function(t) {
        item.addEventListener("click", function() {
          showCard(t);
        });
        item.addEventListener("keydown", function(e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            showCard(t);
          }
        });
      })(tribe);

      stateResultsList.appendChild(item);
    }

    stateResultsSection.hidden = false;
  }

  // ====================================================================
  // Tribe Card
  // ====================================================================

  /**
   * Show the tribe card with details and download buttons.
   * @param {object} tribe - Tribe data object from tribes.json
   */
  function showCard(tribe) {
    // Set tribe name (text before badge)
    tribeName.textContent = tribe.name + " ";
    tribeName.appendChild(tribeFreshness);

    // Set freshness badge
    var badge = getFreshnessBadge(tribe.generated_at);
    tribeFreshness.className = "badge " + badge.cls;
    tribeFreshness.textContent = badge.text;
    tribeFreshness.setAttribute("aria-label", badge.label);

    // Set detail rows
    tribeStates.textContent = (tribe.states || []).join(", ");
    tribeEcoregion.textContent = tribe.ecoregion || "N/A";

    // Build action buttons
    var docs = tribe.documents || {};
    var hasInternal = !!docs.internal_strategy;
    var hasCongressional = !!docs.congressional_overview;
    var safeName = sanitizeFilename(tribe.name);

    // Clear previous actions
    while (tribeActions.firstChild) {
      tribeActions.removeChild(tribeActions.firstChild);
    }

    if (hasInternal) {
      var internalBtn = document.createElement("a");
      internalBtn.href = "tribes/" + docs.internal_strategy;
      internalBtn.download = safeName + "_Internal_Strategy.docx";
      internalBtn.className = "btn-download btn-internal";
      internalBtn.setAttribute("aria-label", "Download Internal Strategy for " + tribe.name);
      internalBtn.textContent = "Internal Strategy";
      tribeActions.appendChild(internalBtn);
    }

    if (hasCongressional) {
      var congressionalBtn = document.createElement("a");
      congressionalBtn.href = "tribes/" + docs.congressional_overview;
      congressionalBtn.download = safeName + "_Congressional_Overview.docx";
      congressionalBtn.className = "btn-download btn-congressional";
      congressionalBtn.setAttribute("aria-label", "Download Congressional Overview for " + tribe.name);
      congressionalBtn.textContent = "Congressional Overview";
      tribeActions.appendChild(congressionalBtn);
    }

    if (hasInternal && hasCongressional) {
      var bothBtn = document.createElement("button");
      bothBtn.type = "button";
      bothBtn.className = "btn-download btn-both";
      bothBtn.setAttribute("aria-label", "Download both documents for " + tribe.name);
      bothBtn.textContent = "Download Both";
      bothBtn.addEventListener("click", function() {
        downloadBoth(docs.internal_strategy, docs.congressional_overview, tribe.name);
      });
      tribeActions.appendChild(bothBtn);
    }

    if (!hasInternal && !hasCongressional) {
      var disabledSpan = document.createElement("span");
      disabledSpan.className = "btn-download";
      disabledSpan.setAttribute("aria-disabled", "true");
      disabledSpan.textContent = "Documents are being prepared. Check back soon.";
      tribeActions.appendChild(disabledSpan);
    }

    // Status line
    var statusP = document.createElement("p");
    statusP.id = "packet-status";
    statusP.className = "packet-status";
    statusP.setAttribute("aria-live", "polite");

    if (tribe.has_complete_data) {
      statusP.textContent = "Full data available: Internal Strategy + Congressional Overview";
    } else if (hasInternal || hasCongressional) {
      var available = [];
      if (hasInternal) available.push("Internal Strategy");
      if (hasCongressional) available.push("Congressional Overview");
      statusP.textContent = available.join(" + ") + " available";
    } else {
      statusP.textContent = "Documents have not been generated yet. Check back soon.";
    }
    tribeActions.appendChild(statusP);

    // Show card with animation
    cardEl.hidden = false;
    // Force reflow before adding data-visible for transition
    cardEl.offsetHeight; // eslint-disable-line no-unused-expressions
    cardEl.setAttribute("data-visible", "");

    // Scroll card into view smoothly
    cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  /**
   * Compute freshness badge class, text, and aria-label from timestamp.
   * @param {string|null} generatedAt - ISO 8601 timestamp or null
   * @returns {{cls: string, text: string, label: string}}
   */
  function getFreshnessBadge(generatedAt) {
    if (!generatedAt) {
      return {
        cls: "badge-unknown",
        text: "Unknown",
        label: "Data freshness unknown"
      };
    }

    var days = (Date.now() - new Date(generatedAt).getTime()) / 86400000;

    if (days < 7) {
      return {
        cls: "badge-fresh",
        text: "Current",
        label: "Data is current (less than 7 days old)"
      };
    }
    if (days < 30) {
      return {
        cls: "badge-aging",
        text: "Recent",
        label: "Data is recent (less than 30 days old)"
      };
    }
    return {
      cls: "badge-stale",
      text: "Needs Update",
      label: "Data may need updating (more than 30 days old)"
    };
  }

  // ====================================================================
  // Download Helpers
  // ====================================================================

  /**
   * Sanitize a Tribe name for use as a download filename.
   * Removes special characters and replaces spaces with underscores.
   * @param {string} name
   * @returns {string}
   */
  function sanitizeFilename(name) {
    return name.replace(/[^a-zA-Z0-9 _-]/g, "").replace(/\s+/g, "_");
  }

  /**
   * Download both documents sequentially with a 300ms delay.
   * Creates temporary anchor elements for each download.
   * @param {string} docAPath - Relative path to Internal Strategy document
   * @param {string} docBPath - Relative path to Congressional Overview document
   * @param {string} tribeName - Tribe name for descriptive filenames
   */
  function downloadBoth(docAPath, docBPath, tribeName) {
    var safeName = sanitizeFilename(tribeName);

    var a1 = document.createElement("a");
    a1.href = "tribes/" + docAPath;
    a1.download = safeName + "_Internal_Strategy.docx";
    document.body.appendChild(a1);
    a1.click();
    document.body.removeChild(a1);

    setTimeout(function() {
      var a2 = document.createElement("a");
      a2.href = "tribes/" + docBPath;
      a2.download = safeName + "_Congressional_Overview.docx";
      document.body.appendChild(a2);
      a2.click();
      document.body.removeChild(a2);
    }, 300);
  }

  // ====================================================================
  // Regional Documents
  // ====================================================================

  /**
   * Render regional document cards.
   * @param {Array} regions - Regions array from tribes.json
   */
  function renderRegions(regions) {
    if (!regions || regions.length === 0) return;

    var hasAny = false;

    for (var i = 0; i < regions.length; i++) {
      var r = regions[i];
      var docs = r.documents || {};
      var hasInternal = !!docs.internal_strategy;
      var hasCongressional = !!docs.congressional_overview;

      if (!hasInternal && !hasCongressional) continue;
      hasAny = true;

      var card = document.createElement("div");
      card.className = "region-card";

      // Region name heading
      var h3 = document.createElement("h3");
      h3.className = "region-name";
      h3.textContent = r.region_name;
      card.appendChild(h3);

      // States
      if (r.states && r.states.length > 0) {
        var statesP = document.createElement("p");
        statesP.className = "region-states";
        statesP.textContent = r.states.join(", ");
        card.appendChild(statesP);
      }

      // Action buttons
      var actDiv = document.createElement("div");
      actDiv.className = "region-actions";

      var regionSafeName = sanitizeFilename(r.region_name);

      if (hasInternal) {
        var internalBtn = document.createElement("a");
        internalBtn.href = "tribes/" + docs.internal_strategy;
        internalBtn.download = regionSafeName + "_Internal_Strategy.docx";
        internalBtn.className = "btn-download btn-internal btn-sm";
        internalBtn.setAttribute("aria-label", "Download Internal Strategy for " + r.region_name);
        internalBtn.textContent = "Internal Strategy";
        actDiv.appendChild(internalBtn);
      }

      if (hasCongressional) {
        var congressionalBtn = document.createElement("a");
        congressionalBtn.href = "tribes/" + docs.congressional_overview;
        congressionalBtn.download = regionSafeName + "_Congressional_Overview.docx";
        congressionalBtn.className = "btn-download btn-congressional btn-sm";
        congressionalBtn.setAttribute("aria-label", "Download Congressional Overview for " + r.region_name);
        congressionalBtn.textContent = "Congressional Overview";
        actDiv.appendChild(congressionalBtn);
      }

      card.appendChild(actDiv);
      regionsList.appendChild(card);
    }

    if (hasAny) {
      regionsSection.hidden = false;
    }
  }

  // ====================================================================
  // Bootstrap
  // ====================================================================

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
