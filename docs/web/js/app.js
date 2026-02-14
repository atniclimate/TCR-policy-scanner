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
  var MANIFEST_URL = "data/manifest.json";

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
  var resultCountEl = document.getElementById("result-count");

  // --- Data storage ---
  var allTribes = [];
  var tribeMap = {};
  var manifestData = null;
  var comboboxInstance = null;

  // ====================================================================
  // Initialization
  // ====================================================================

  /**
   * Build an error message element with a Refresh Page link.
   * Uses safe DOM methods (no innerHTML) to prevent XSS.
   * @param {string} messageText - Plain text error message
   * @returns {DocumentFragment}
   */
  function buildErrorWithRefresh(messageText) {
    var frag = document.createDocumentFragment();
    var textNode = document.createTextNode(messageText + " ");
    frag.appendChild(textNode);
    var refreshLink = document.createElement("a");
    refreshLink.href = "#";
    refreshLink.textContent = "Refresh Page";
    refreshLink.addEventListener("click", function(e) {
      e.preventDefault();
      location.reload();
    });
    frag.appendChild(refreshLink);
    return frag;
  }

  /**
   * Initialize the application: fetch data, build search index, wire UI.
   */
  function init() {
    // CYCLOPS-015: Check if Fuse.js loaded successfully
    if (typeof window.Fuse === "undefined") {
      showError(buildErrorWithRefresh("Search functionality failed to load. Please"));
      return;
    }

    // Fetch manifest for deployment date (non-blocking)
    fetch(MANIFEST_URL).then(function(response) {
      if (response.ok) return response.json();
      return null;
    }).then(function(data) {
      manifestData = data;
    }).catch(function() {
      // Non-critical, ignore
    });

    var controller = new AbortController();
    var timeoutId = setTimeout(function() { controller.abort(); }, 15000);

    fetch(TRIBES_URL, { signal: controller.signal }).then(function(response) {
      clearTimeout(timeoutId);
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
      comboboxInstance = new TribeCombobox(searchInput, listboxEl, statusEl, fuse);
      comboboxInstance.onTribeSelected = function(tribe) {
        showCard(tribe);
        updateHash(tribe.name);
      };

      // MAGOO-004: Hide card when user starts typing new search
      searchInput.addEventListener("input", function() {
        hideCard();
      });

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

      // MAGOO-009: Check for hash-based deep link
      handleHashNavigation();

    }).catch(function(err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        showError(buildErrorWithRefresh("Loading timed out."));
      } else {
        showError(buildErrorWithRefresh("Failed to load Tribe data. Please try again in a few minutes or"));
      }
      if (typeof console !== "undefined") {
        console.error("Failed to load tribes.json:", err);
      }
    });
  }

  /**
   * Show error message and hide loading indicator.
   * Accepts either a string or a DocumentFragment for safe DOM rendering.
   * @param {string|DocumentFragment} message
   */
  function showError(message) {
    loadingEl.hidden = true;
    // Clear previous content
    while (errorEl.firstChild) {
      errorEl.removeChild(errorEl.firstChild);
    }
    if (typeof message === "string") {
      errorEl.textContent = message;
    } else {
      errorEl.appendChild(message);
    }
    errorEl.hidden = false;
  }

  // ====================================================================
  // Hash-based shareable URLs (MAGOO-009)
  // ====================================================================

  /**
   * Update the URL hash when a Tribe is selected.
   * @param {string} name - Tribe name
   */
  function updateHash(name) {
    if (history.replaceState) {
      history.replaceState(null, "", "#tribe=" + encodeURIComponent(name));
    } else {
      location.hash = "#tribe=" + encodeURIComponent(name);
    }
  }

  /**
   * On page load, check if URL contains a #tribe= hash and auto-select.
   */
  function handleHashNavigation() {
    var hash = location.hash;
    if (!hash || hash.indexOf("#tribe=") !== 0) return;

    var name = decodeURIComponent(hash.substring(7));
    var tribe = tribeMap[name];
    if (tribe) {
      searchInput.value = name;
      showCard(tribe);
    }
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
          updateHash(t.name);
        });
        item.addEventListener("keydown", function(e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            showCard(t);
            updateHash(t.name);
          }
        });
      })(tribe);

      stateResultsList.appendChild(item);
    }

    stateResultsSection.hidden = false;

    // CYCLOPS-006: Announce result count
    announceResultCount(tribes.length, allTribes.length);
  }

  // ====================================================================
  // Screen Reader Announcements (CYCLOPS-006)
  // ====================================================================

  /**
   * Announce search result count to screen readers via aria-live region.
   * @param {number} shown - Number of results displayed
   * @param {number} total - Total number of Tribal Nations
   */
  function announceResultCount(shown, total) {
    if (!resultCountEl) return;
    if (shown >= 15) {
      resultCountEl.textContent = "Showing 15 of " + total + " matches";
    } else {
      resultCountEl.textContent = "Showing " + shown + " matches";
    }
  }

  // ====================================================================
  // Tribe Card
  // ====================================================================

  /**
   * Hide the tribe card (MAGOO-004: hide on new search).
   */
  function hideCard() {
    cardEl.removeAttribute("data-visible");
    // Let transition complete before hiding
    setTimeout(function() {
      if (!cardEl.hasAttribute("data-visible")) {
        cardEl.hidden = true;
      }
    }, 250);
  }

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
      var internalWrapper = document.createElement("div");
      internalWrapper.className = "btn-download-wrapper";
      var internalBtn = document.createElement("a");
      internalBtn.href = "tribes/" + docs.internal_strategy;
      internalBtn.download = safeName + "_Internal_Strategy.docx";
      internalBtn.rel = "noopener";
      internalBtn.className = "btn-download btn-internal";
      internalBtn.setAttribute("aria-label", "Download Internal Strategy for " + tribe.name);
      internalBtn.textContent = "Internal Strategy";
      internalWrapper.appendChild(internalBtn);
      // MAGOO-003: Document type description
      var internalDesc = document.createElement("span");
      internalDesc.className = "doc-description";
      internalDesc.textContent = "Detailed analysis with talking points for your team";
      internalWrapper.appendChild(internalDesc);
      tribeActions.appendChild(internalWrapper);
    }

    if (hasCongressional) {
      var congressionalWrapper = document.createElement("div");
      congressionalWrapper.className = "btn-download-wrapper";
      var congressionalBtn = document.createElement("a");
      congressionalBtn.href = "tribes/" + docs.congressional_overview;
      congressionalBtn.download = safeName + "_Congressional_Overview.docx";
      congressionalBtn.rel = "noopener";
      congressionalBtn.className = "btn-download btn-congressional";
      congressionalBtn.setAttribute("aria-label", "Download Congressional Overview for " + tribe.name);
      congressionalBtn.textContent = "Congressional Overview";
      congressionalWrapper.appendChild(congressionalBtn);
      // MAGOO-003: Document type description
      var congressionalDesc = document.createElement("span");
      congressionalDesc.className = "doc-description";
      congressionalDesc.textContent = "Facts-only briefing for congressional offices";
      congressionalWrapper.appendChild(congressionalDesc);
      tribeActions.appendChild(congressionalWrapper);
    }

    if (hasInternal && hasCongressional) {
      var bothBtn = document.createElement("button");
      bothBtn.type = "button";
      bothBtn.className = "btn-download btn-both";
      bothBtn.setAttribute("aria-label", "Download both documents for " + tribe.name);
      bothBtn.textContent = "Download Both";
      bothBtn.addEventListener("click", function() {
        // CYCLOPS-004: Double-click guard
        bothBtn.disabled = true;
        bothBtn.textContent = "Downloading...";
        downloadBoth(docs.internal_strategy, docs.congressional_overview, tribe.name);
        setTimeout(function() {
          bothBtn.disabled = false;
          bothBtn.textContent = "Download Both";
        }, 2000);
      });
      tribeActions.appendChild(bothBtn);
    }

    if (!hasInternal && !hasCongressional) {
      // CYCLOPS-008: Better "documents being prepared" context
      var disabledSpan = document.createElement("span");
      disabledSpan.className = "btn-download";
      disabledSpan.setAttribute("aria-disabled", "true");
      var prepMsg = "Documents are being prepared for " + tribe.name + ". Check back after the next daily update.";
      if (manifestData && manifestData.deployed_at) {
        var deployDate = new Date(manifestData.deployed_at).toLocaleDateString();
        prepMsg = "Documents are being prepared for " + tribe.name + ". Last deployment: " + deployDate + ". Check back after the next daily update.";
      }
      disabledSpan.textContent = prepMsg;
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

    // Scroll card into view (respect reduced motion preference: P2-04)
    var motionOK = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    cardEl.scrollIntoView({ behavior: motionOK ? "smooth" : "auto", block: "nearest" });
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
    a1.rel = "noopener";
    document.body.appendChild(a1);
    a1.click();
    document.body.removeChild(a1);

    setTimeout(function() {
      var a2 = document.createElement("a");
      a2.href = "tribes/" + docBPath;
      a2.download = safeName + "_Congressional_Overview.docx";
      a2.rel = "noopener";
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
        internalBtn.rel = "noopener";
        internalBtn.className = "btn-download btn-internal btn-sm";
        internalBtn.setAttribute("aria-label", "Download Internal Strategy for " + r.region_name);
        internalBtn.textContent = "Internal Strategy";
        actDiv.appendChild(internalBtn);
      }

      if (hasCongressional) {
        var congressionalBtn = document.createElement("a");
        congressionalBtn.href = "tribes/" + docs.congressional_overview;
        congressionalBtn.download = regionSafeName + "_Congressional_Overview.docx";
        congressionalBtn.rel = "noopener";
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
