(function () {
  'use strict';

  var tableBody = document.querySelector('#models-table tbody');
  var cardsContainer = document.getElementById('cards');
  if (!tableBody || !cardsContainer) return;

  var headers = document.querySelectorAll('#models-table th[data-sort]');
  var sortSelect = document.getElementById('sort-select');
  var searchInput = document.getElementById('search-input');
  var chips = document.querySelectorAll('.chip[data-modality]');
  var hideExpired = document.getElementById('hide-expired');
  var clearBtn = document.getElementById('clear-filters');
  var resultsCount = document.getElementById('results-count');
  var emptyState = document.getElementById('empty-state');
  var toast = document.getElementById('toast');

  var totalCount = tableBody.children.length;

  var cardById = {};
  Array.prototype.forEach.call(cardsContainer.children, function (card) {
    cardById[card.dataset.modelId] = card;
  });

  // ---------------- sorting ----------------

  var sortState = { key: 'rank', dir: 'asc' };

  function numericVal(el, key) {
    return parseFloat(el.dataset[key]);
  }

  function compareEls(a, b, key, dir) {
    if (key === 'name') {
      var av = a.dataset.name || '';
      var bv = b.dataset.name || '';
      return dir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    var an = numericVal(a, key);
    var bn = numericVal(b, key);
    return dir === 'asc' ? an - bn : bn - an;
  }

  function applySort(key, dir) {
    sortState = { key: key, dir: dir };
    [tableBody, cardsContainer].forEach(function (container) {
      var items = Array.prototype.slice.call(container.children);
      items.sort(function (a, b) { return compareEls(a, b, key, dir); });
      items.forEach(function (el) { container.appendChild(el); });
    });
    headers.forEach(function (h) {
      h.classList.remove('sorted-asc', 'sorted-desc');
      if (h.dataset.sort === key) h.classList.add(dir === 'asc' ? 'sorted-asc' : 'sorted-desc');
    });
  }

  function syncSortSelect(key, dir) {
    if (!sortSelect) return;
    var value = key + '-' + dir;
    var match = Array.prototype.some.call(sortSelect.options, function (o) { return o.value === value; });
    if (match) sortSelect.value = value;
  }

  headers.forEach(function (h) {
    h.tabIndex = 0;
    h.addEventListener('click', function () {
      var key = h.dataset.sort;
      var dir = (sortState.key === key && sortState.dir === 'asc') ? 'desc' : 'asc';
      applySort(key, dir);
      syncSortSelect(key, dir);
    });
    h.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        h.click();
      }
    });
  });

  if (sortSelect) {
    sortSelect.addEventListener('change', function () {
      var parts = sortSelect.value.split('-');
      applySort(parts[0], parts[1]);
    });
  }

  applySort('rank', 'asc');

  // ---------------- filtering ----------------

  var activeModalities = new Set();

  function matchesFilters(el) {
    var name = el.dataset.name || '';
    var id = (el.dataset.modelId || '').toLowerCase();
    var q = (searchInput.value || '').trim().toLowerCase();
    if (q && name.indexOf(q) === -1 && id.indexOf(q) === -1) return false;

    if (activeModalities.size) {
      var mods = (el.dataset.modalities || '').split(',');
      var any = false;
      activeModalities.forEach(function (m) { if (mods.indexOf(m) !== -1) any = true; });
      if (!any) return false;
    }

    if (hideExpired.checked && el.dataset.expired === 'true') return false;

    return true;
  }

  function applyFilters() {
    var visible = 0;
    Array.prototype.forEach.call(tableBody.children, function (row) {
      var show = matchesFilters(row);
      row.hidden = !show;
      var card = cardById[row.dataset.modelId];
      if (card) card.hidden = !show;
      if (show) visible++;
    });
    resultsCount.textContent = visible + ' of ' + totalCount + ' models';
    emptyState.hidden = visible !== 0;
  }

  searchInput.addEventListener('input', applyFilters);
  hideExpired.addEventListener('change', applyFilters);

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var m = chip.dataset.modality;
      var pressed = chip.getAttribute('aria-pressed') === 'true';
      chip.setAttribute('aria-pressed', pressed ? 'false' : 'true');
      if (pressed) activeModalities.delete(m); else activeModalities.add(m);
      applyFilters();
    });
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      searchInput.value = '';
      activeModalities.clear();
      chips.forEach(function (c) { c.setAttribute('aria-pressed', 'false'); });
      hideExpired.checked = false;
      applyFilters();
    });
  }

  applyFilters();

  // ---------------- copy id + toast ----------------

  var toastTimer;
  function showToast(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 2000);
  }

  document.querySelectorAll('.copy-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var modelId = btn.dataset.modelId;
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        showToast('Copy not supported');
        return;
      }
      navigator.clipboard.writeText(modelId).then(function () {
        btn.classList.add('copied');
        showToast('Copied ' + modelId);
        setTimeout(function () { btn.classList.remove('copied'); }, 2000);
      }).catch(function () {
        showToast('Failed to copy');
      });
    });
  });

  // ---------------- keyboard row navigation (table) ----------------

  Array.prototype.forEach.call(tableBody.children, function (row) { row.tabIndex = 0; });

  tableBody.addEventListener('keydown', function (e) {
    if (e.key === 'Tab') return;
    var row = e.target.closest ? e.target.closest('tr') : null;
    if (!row) return;

    var rows = Array.prototype.filter.call(tableBody.children, function (r) { return !r.hidden; });
    var idx = rows.indexOf(row);
    if (idx === -1) return;

    var target = null;
    if (e.key === 'ArrowDown' && idx < rows.length - 1) target = rows[idx + 1];
    else if (e.key === 'ArrowUp' && idx > 0) target = rows[idx - 1];
    else if (e.key === 'Home') target = rows[0];
    else if (e.key === 'End') target = rows[rows.length - 1];

    if (target) {
      e.preventDefault();
      target.focus({ preventScroll: true });
    }
  });
})();
