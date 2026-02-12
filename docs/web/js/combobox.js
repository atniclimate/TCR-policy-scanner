/**
 * TribeCombobox -- W3C APG ARIA 1.2 Editable Combobox with List Autocomplete
 *
 * Implements the "Editable Combobox with List Autocomplete" pattern from the
 * W3C ARIA Authoring Practices Guide.  Provides keyboard navigation
 * (ArrowDown/Up/Enter/Escape), aria-activedescendant focus management,
 * aria-expanded toggle, result count announcements via a live region,
 * and click selection.
 *
 * Usage:
 *   var combo = new TribeCombobox(inputEl, listboxEl, statusEl, fuseInstance);
 *   combo.onTribeSelected = function(tribe) { ... };
 *
 * @see https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
 */
(function() {
  "use strict";

  /**
   * @constructor
   * @param {HTMLInputElement} inputEl   - The input[role="combobox"] element
   * @param {HTMLUListElement} listboxEl - The ul[role="listbox"] element
   * @param {HTMLElement} statusEl       - The div[role="status"] live region
   * @param {object} fuseInstance        - A configured Fuse.js instance
   */
  function TribeCombobox(inputEl, listboxEl, statusEl, fuseInstance) {
    this.input = inputEl;
    this.listbox = listboxEl;
    this.status = statusEl;
    this.fuse = fuseInstance;

    /** @type {HTMLLIElement[]} Currently rendered option elements */
    this.options = [];
    /** @type {number} Index of visually focused option (-1 = none) */
    this.activeIndex = -1;
    /** @type {string} Last search query */
    this._lastQuery = "";
    /** @type {Array} Cached Fuse.js results for last query */
    this._lastResults = [];
    /** @type {function|null} Callback when a Tribe is selected */
    this.onTribeSelected = null;
    /** @type {number|null} Blur timeout handle */
    this._blurTimeout = null;

    // Bind event handlers
    var self = this;
    this.input.addEventListener("input", function() { self.onInput(); });
    this.input.addEventListener("keydown", function(e) { self.onKeyDown(e); });
    this.input.addEventListener("blur", function() { self.onBlur(); });
    this.listbox.addEventListener("click", function(e) { self.onOptionClick(e); });
  }

  /**
   * Handle input events -- run fuzzy search and render results.
   */
  TribeCombobox.prototype.onInput = function() {
    var query = this.input.value.trim();
    this._lastQuery = query;

    if (query.length < 2) {
      this.close();
      this.status.textContent = "";
      return;
    }

    var results = this.fuse.search(query);
    // Cap at 15 results for performance and readability
    if (results.length > 15) {
      results = results.slice(0, 15);
    }
    this._lastResults = results;

    this.renderOptions(results);
    this.open();

    if (results.length === 0) {
      this.status.textContent = "No results found";
    } else if (results.length === 1) {
      this.status.textContent = "1 result available";
    } else {
      this.status.textContent = results.length + " results available";
    }
  };

  /**
   * Handle keydown events for keyboard navigation.
   * @param {KeyboardEvent} e
   */
  TribeCombobox.prototype.onKeyDown = function(e) {
    var key = e.key;

    if (key === "ArrowDown") {
      e.preventDefault();
      if (!this.isOpen()) {
        this.onInput();
      }
      if (this.options.length > 0) {
        this.moveFocus(1);
      }
      return;
    }

    if (key === "ArrowUp") {
      e.preventDefault();
      if (!this.isOpen()) {
        this.onInput();
        if (this.options.length > 0) {
          // Move to last option when opening with ArrowUp
          this.activeIndex = -1;
          this.moveFocus(-1);
        }
      } else if (this.options.length > 0) {
        this.moveFocus(-1);
      }
      return;
    }

    if (key === "Enter") {
      e.preventDefault();
      if (this.activeIndex >= 0) {
        this.selectOption(this.activeIndex);
      }
      return;
    }

    if (key === "Escape") {
      if (this.isOpen()) {
        this.close();
      } else if (this.input.value) {
        this.input.value = "";
        this.status.textContent = "";
      }
      return;
    }
  };

  /**
   * Move visual focus by delta positions with wrapping.
   * @param {number} delta - Direction to move (+1 down, -1 up)
   */
  TribeCombobox.prototype.moveFocus = function(delta) {
    var len = this.options.length;
    if (len === 0) return;

    // Clear previous active option
    if (this.activeIndex >= 0 && this.activeIndex < len) {
      this.options[this.activeIndex].setAttribute("aria-selected", "false");
    }

    // Calculate new index with wrapping
    if (this.activeIndex < 0 && delta < 0) {
      // Coming from no selection going up -> go to last
      this.activeIndex = len - 1;
    } else {
      this.activeIndex = ((this.activeIndex + delta) % len + len) % len;
    }

    // Set new active option
    var opt = this.options[this.activeIndex];
    opt.setAttribute("aria-selected", "true");
    this.input.setAttribute("aria-activedescendant", opt.id);
    opt.scrollIntoView({ block: "nearest" });
  };

  /**
   * Render search results as listbox options.
   * @param {Array} results - Fuse.js search results
   */
  TribeCombobox.prototype.renderOptions = function(results) {
    // Clear existing options
    while (this.listbox.firstChild) {
      this.listbox.removeChild(this.listbox.firstChild);
    }
    this.options = [];
    this.activeIndex = -1;
    this.input.removeAttribute("aria-activedescendant");

    for (var i = 0; i < results.length; i++) {
      var result = results[i];
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.id = "opt-" + i;
      li.setAttribute("aria-selected", "false");

      // Primary text: Tribe name
      var nameSpan = document.createElement("span");
      nameSpan.className = "option-name";
      nameSpan.textContent = result.item.name;
      li.appendChild(nameSpan);

      // Check for alias match and show "Also known as" hint
      var aliasMatch = this._findAliasMatch(result);
      if (aliasMatch) {
        var aliasSpan = document.createElement("span");
        aliasSpan.className = "option-alias";
        aliasSpan.textContent = "Also known as: " + aliasMatch;
        li.appendChild(aliasSpan);
      }

      // State abbreviation on the right
      if (result.item.states && result.item.states.length > 0) {
        var stateSpan = document.createElement("span");
        stateSpan.className = "option-state";
        stateSpan.textContent = result.item.states.join(", ");
        li.appendChild(stateSpan);
      }

      this.listbox.appendChild(li);
      this.options.push(li);
    }
  };

  /**
   * Find alias match from Fuse.js result matches.
   * @param {object} result - A single Fuse.js search result
   * @returns {string|null} The matched alias text, or null
   */
  TribeCombobox.prototype._findAliasMatch = function(result) {
    if (!result.matches) return null;
    for (var j = 0; j < result.matches.length; j++) {
      var match = result.matches[j];
      if (match.key && match.key.indexOf("aliases") !== -1 && match.value) {
        return match.value;
      }
    }
    return null;
  };

  /**
   * Select the option at the given index.
   * @param {number} index - Index in the options and _lastResults arrays
   */
  TribeCombobox.prototype.selectOption = function(index) {
    if (index < 0 || index >= this._lastResults.length) return;

    var result = this._lastResults[index];
    this.input.value = result.item.name;
    this.close();

    if (typeof this.onTribeSelected === "function") {
      this.onTribeSelected(result.item);
    }
  };

  /**
   * Open the listbox dropdown.
   */
  TribeCombobox.prototype.open = function() {
    this.listbox.hidden = false;
    this.input.setAttribute("aria-expanded", "true");
  };

  /**
   * Close the listbox dropdown and reset focus state.
   */
  TribeCombobox.prototype.close = function() {
    this.listbox.hidden = true;
    this.input.setAttribute("aria-expanded", "false");
    this.activeIndex = -1;
    this.input.removeAttribute("aria-activedescendant");
  };

  /**
   * Check if the listbox is currently open.
   * @returns {boolean}
   */
  TribeCombobox.prototype.isOpen = function() {
    return !this.listbox.hidden;
  };

  /**
   * Handle blur on the input -- close after short delay to allow click events.
   */
  TribeCombobox.prototype.onBlur = function() {
    var self = this;
    if (this._blurTimeout) {
      clearTimeout(this._blurTimeout);
    }
    this._blurTimeout = setTimeout(function() {
      self.close();
      self._blurTimeout = null;
    }, 200);
  };

  /**
   * Handle click events on listbox options.
   * @param {MouseEvent} e
   */
  TribeCombobox.prototype.onOptionClick = function(e) {
    var target = e.target;
    // Walk up to find the [role="option"] element
    while (target && target !== this.listbox) {
      if (target.getAttribute && target.getAttribute("role") === "option") {
        break;
      }
      target = target.parentElement;
    }
    if (!target || target === this.listbox) return;

    var index = this.options.indexOf(target);
    if (index >= 0) {
      this.selectOption(index);
    }
  };

  // Expose on window for use by app.js
  window.TribeCombobox = TribeCombobox;

})();
