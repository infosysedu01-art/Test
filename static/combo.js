/* Search box that replaces a long <select>: type a few digits / letters, pick from at most 30 server-side matches.
   Markup: <div class="combo" data-url="..."> <input type="hidden"> <input class="combo-in"> <button class="combo-x"> <ul class="combo-list"> </div>
   The page can set root._zone = function () { return zoneId; }, and listens to the 'combo:pick' / 'combo:clear' events. */
(function () {
  'use strict';
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) { e.className = cls; } if (txt !== undefined) { e.textContent = txt; } return e; }

  function init(root) {
    var hid = root.querySelector('input[type=hidden]'), inp = root.querySelector('.combo-in'),
        x = root.querySelector('.combo-x'), list = root.querySelector('.combo-list');
    var T = { none: root.getAttribute('data-none') || 'No match found', more: root.getAttribute('data-more') || 'Type more to narrow the list' };
    var items = [], hi = -1, timer = null, ctl = null, label = inp.value, reqId = 0, inflight = false, pendingPick = false;

    function open() { return list.style.display === 'block'; }
    function close() { list.style.display = 'none'; hi = -1; inp.setAttribute('aria-expanded', 'false'); }
    function mark() {
      var opts = list.querySelectorAll('.combo-opt');
      for (var i = 0; i < opts.length; i++) {
        opts[i].classList.toggle('active', i === hi);
        if (i === hi && opts[i].scrollIntoView) { opts[i].scrollIntoView({ block: 'nearest' }); }
      }
    }
    function fire(name, detail) { root.dispatchEvent(new CustomEvent(name, { bubbles: true, detail: detail || {} })); }
    function sync() { x.style.display = (hid.value && !inp.disabled) ? 'block' : 'none'; }
    function pick(i) {
      var it = items[i]; if (!it) { return; }
      hid.value = it.id; label = it.label; inp.value = label; root.setAttribute('data-zone', it.zone || '');
      close(); sync(); fire('combo:pick', { zone: String(it.zone || ''), id: it.id });
    }
    function clear(silent) {
      hid.value = ''; label = ''; inp.value = ''; root.setAttribute('data-zone', ''); sync();
      if (!silent) { fire('combo:clear'); }
    }
    function render(data) {
      items = data.items || []; list.innerHTML = '';
      if (!items.length) { list.appendChild(el('li', 'combo-empty', T.none)); }
      items.forEach(function (it, i) {
        var li = el('li', 'combo-opt'); li.appendChild(el('span', 'combo-lab', it.label));
        if (it.sub) { li.appendChild(el('small', 'combo-sub', it.sub)); }
        li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(i); });      // before the input loses focus
        li.addEventListener('mousemove', function () { if (hi !== i) { hi = i; mark(); } });
        list.appendChild(li);
      });
      if (data.more) { list.appendChild(el('li', 'combo-more', T.more)); }
      hi = items.length ? 0 : -1; mark(); list.style.display = 'block'; inp.setAttribute('aria-expanded', 'true');
      if (pendingPick) { pendingPick = false; if (items.length) { pick(0); } }       // Enter was pressed while the answer was still on its way
    }
    function search() {
      var typed = inp.value.trim(), my = ++reqId; inflight = true;
      if (ctl && window.AbortController) { ctl.abort(); }
      ctl = window.AbortController ? new AbortController() : null;
      var u = new URL(root.getAttribute('data-url'), window.location.href);
      u.searchParams.set('q', typed === label ? '' : typed);          // showing the chosen value = show the whole list
      var zn = root._zone ? root._zone() : ''; if (zn) { u.searchParams.set('zone_id', zn); }
      fetch(u.href, { credentials: 'same-origin', signal: ctl ? ctl.signal : undefined, headers: { Accept: 'application/json' } })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (d) { if (my === reqId) { inflight = false; render(d); } })
        .catch(function () { if (my === reqId) { inflight = false; pendingPick = false; } });      // aborted (newer search) or offline
    }

    inp.addEventListener('focus', function () { if (!inp.disabled) { inp.select(); search(); } });
    inp.addEventListener('click', function () { if (!inp.disabled && !open()) { search(); } });
    inp.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { timer = null; search(); }, 180); });
    inp.addEventListener('keydown', function (e) {
      var k = e.key;
      if (k === 'ArrowDown' || k === 'ArrowUp') {
        e.preventDefault();
        if (!open()) { search(); return; }
        if (items.length) { hi = (hi + (k === 'ArrowDown' ? 1 : -1) + items.length) % items.length; mark(); }
      } else if (k === 'Enter') {
        if (timer !== null || inflight) { e.preventDefault(); clearTimeout(timer); timer = null; pendingPick = true; search(); return; }   // wait for the fresh list
        if (open()) { e.preventDefault(); if (hi >= 0) { pick(hi); } }
      } else if (k === 'Escape') {
        if (open()) { e.preventDefault(); e.stopPropagation(); close(); inp.value = label; }
      } else if (k === 'Tab') {
        if (timer === null && !inflight && open() && hi >= 0 && inp.value.trim() !== label && inp.value.trim() !== '') { pick(hi); }
      }
    });
    inp.addEventListener('blur', function () {
      clearTimeout(timer); timer = null; pendingPick = false; close();
      if (inp.value.trim() === '') { if (hid.value) { clear(); } } else { inp.value = label; }       // never leave half-typed text
    });
    x.addEventListener('mousedown', function (e) { e.preventDefault(); });
    x.addEventListener('click', function () { clear(); inp.focus(); });
    root.comboSetEnabled = function (on) { inp.disabled = !on; hid.disabled = !on; if (!on) { clear(true); close(); } sync(); };
    root.comboClear = function () { clear(); };
    sync();
  }
  window.Combo = { init: init, initAll: function () { Array.prototype.forEach.call(document.querySelectorAll('.combo[data-url]'), init); } };
})();
