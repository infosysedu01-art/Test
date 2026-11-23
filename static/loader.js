/* Loader v2.  1) a thin orange/navy progress bar runs on every page change, form submit and download (never blocks);
   2) the glass card with the logo ring appears ONLY if the wait is longer than ~0.25 s, so fast pages show nothing but the bar.
   No artificial delay on page load any more.  It always hides itself (safety timer) and never breaks a link or a form. */
(function () {
  'use strict';
  var el = document.getElementById('appLoader');
  if (!el) { return; }
  var txt = document.getElementById('alText'), bar = document.getElementById('topBar');
  var barI = bar ? bar.firstElementChild : null;
  var M = { load: el.getAttribute('data-m-load') || 'Loading...', save: el.getAttribute('data-m-save') || 'Saving...',
            del: el.getAttribute('data-m-delete') || 'Deleting...', down: el.getAttribute('data-m-download') || 'Preparing your download...' };
  var SHOW_DELAY = 260, MIN_VISIBLE = 450;            // card only after 260 ms; once visible stay at least 450 ms (no flicker)
  var shownAt = 0, delayT = null, hideT = null, failT = null, barT = null, trickle = null, w = 0;

  function barStart() {
    if (!bar) { return; }
    clearInterval(trickle); clearTimeout(barT);
    w = 8; barI.style.transition = 'width .3s ease'; barI.style.width = w + '%'; bar.classList.add('on');
    trickle = setInterval(function () { w += (92 - w) * 0.08; barI.style.width = w + '%'; }, 300);
  }
  function barDone() {
    if (!bar) { return; }
    clearInterval(trickle); barI.style.width = '100%';
    barT = setTimeout(function () { bar.classList.remove('on'); barI.style.transition = 'none'; barI.style.width = '0'; }, 380);
  }
  function reveal() { shownAt = Date.now(); el.classList.add('show'); el.setAttribute('aria-hidden', 'false'); }
  function hideNow() {
    clearTimeout(delayT); clearTimeout(hideT); clearTimeout(failT);
    el.classList.remove('show'); el.setAttribute('aria-hidden', 'true'); barDone();
  }
  function hide() {
    clearTimeout(delayT);
    if (!el.classList.contains('show')) { hideNow(); return; }
    clearTimeout(hideT);
    hideT = setTimeout(hideNow, Math.max(0, MIN_VISIBLE - (Date.now() - shownAt)));
  }
  function show(msg, maxMs, delay) {
    clearTimeout(hideT); clearTimeout(failT); clearTimeout(delayT);
    if (txt) { txt.textContent = msg || M.load; }
    barStart();
    var d = (delay === undefined) ? SHOW_DELAY : delay;
    if (d <= 0 || el.classList.contains('show')) { reveal(); } else { delayT = setTimeout(reveal, d); }
    failT = setTimeout(hideNow, maxMs || 20000);       // never stay forever
  }
  window.AppLoader = { show: show, hide: hide, hideNow: hideNow, msg: M, minMs: MIN_VISIBLE };

  /* back / forward button (page restored from cache): clear everything and allow forms again */
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      hideNow();
      Array.prototype.forEach.call(document.forms, function (f) { f._busy = 0; });
    }
  });

  /* ---------- downloads (Excel / reports): fetch the file so we know exactly when it is ready ---------- */
  function isDownloadUrl(u) {
    return u.pathname.indexOf('/export') !== -1 || u.searchParams.get('download') === '1';
  }
  function fileName(cd) {
    var m = /filename\*=UTF-8''([^;]+)/i.exec(cd || '');
    if (m) { try { return decodeURIComponent(m[1]); } catch (e) { /* ignore */ } }
    m = /filename="?([^";]+)"?/i.exec(cd || '');
    return m ? m[1] : '';
  }
  function download(url) {
    show(M.down, 120000, 0);
    var plain = function () { hideNow(); window.location.href = url; };     // let the browser do it the normal way
    if (!window.fetch || !window.URL || !window.URL.createObjectURL) { plain(); return; }
    fetch(url, { credentials: 'same-origin' }).then(function (r) {
      var ct = r.headers.get('Content-Type') || '';
      if (!r.ok || ct.indexOf('text/html') === 0) { throw new Error('not a file'); }   // e.g. "no access" message page
      var name = fileName(r.headers.get('Content-Disposition')) || 'download.xlsx';
      return r.blob().then(function (b) { return { b: b, name: name }; });
    }).then(function (o) {
      var u = URL.createObjectURL(o.b), a = document.createElement('a');
      a.href = u; a.download = o.name; a.style.display = 'none';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(u); }, 15000);
      hide();
    }).catch(plain);
  }

  /* ---------- link clicks ---------- */
  document.addEventListener('click', function (e) {
    try {
      if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) { return; }
      var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
      if (!a) { return; }
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' || /^(javascript:|mailto:|tel:)/i.test(href)) { return; }
      if ((a.target && a.target !== '_self') || a.hasAttribute('download') || a.hasAttribute('data-bs-toggle') ||
          a.hasAttribute('data-noloader') || a.closest('[data-noloader]')) { return; }
      var u = new URL(a.href, window.location.href);
      if (u.origin !== window.location.origin) { return; }
      if (isDownloadUrl(u)) { e.preventDefault(); download(u.href); return; }
      if (u.pathname === window.location.pathname && u.search === window.location.search) { return; }
      show(M.load, 15000);
    } catch (err) { /* never break navigation */ }
  }, false);

  /* ---------- form submits: employee add / edit / update / delete, masters, users, login ... ---------- */
  document.addEventListener('submit', function (e) {
    try {
      var f = e.target;
      if (!f || f.tagName !== 'FORM' || e.defaultPrevented) { return; }     // e.g. waiting for the confirm box
      if (f.getAttribute('target') === '_blank') { return; }
      var method = (f.getAttribute('method') || 'get').toLowerCase();
      var sub = e.submitter;
      if (method === 'get' && sub && sub.name === 'download') {            // "Download Excel" button of a report form
        e.preventDefault();
        var u = new URL(f.getAttribute('action') || window.location.href, window.location.href);
        new FormData(f).forEach(function (v, k) { if (typeof v === 'string') { u.searchParams.set(k, v); } });
        u.searchParams.set('download', '1');
        download(u.href);
        return;
      }
      if (method === 'post') {                                              // a double click must not save twice
        if (f._busy && Date.now() - f._busy < 4000) { e.preventDefault(); return; }
        f._busy = Date.now();
      }
      var custom = f.getAttribute('data-loader-msg');
      var action = f.getAttribute('action') || '';
      show(custom || (method === 'post' ? (/\/delete(\/|\?|$)/.test(action) ? M.del : M.save) : M.load), 30000);
    } catch (err) { /* never break a form */ }
  }, false);
})();
