/* ============================================================================
   portfolio_page.js — inlined into dist/index.html by portfolio_page.html
   through a Jinja include tag.

   Owns five enhancements: tab switching, scroll reveal, pointer tilt, metric
   counters, and the Selected Work sub-tabs.

   Constraints this file is written to respect:

   1. Google Sites serves embeds inside a sandboxed iframe. localStorage and
      cookies may throw on access, so nothing here persists state.
   2. The iframe has a FIXED height set by the Sites editor and does not
      auto-resize. We postMessage our height anyway, which is a no-op there but
      lets a self-hosted parent page auto-fit.
   3. THIS FILE IS PARSED BY JINJA. Never write a doubled opening brace or a
      brace-percent pair anywhere, including in comments — Jinja treats them as
      its own delimiters and the build dies. (Plain single braces are fine, and
      so are ES template literals, as long as they avoid those two sequences.)
   4. Everything is feature-detected and wrapped so that a failure in one
      enhancement cannot blank the page. In particular the markup ships with no
      panel hidden: hiding is this file's job, so a total JS failure degrades to
      one long scrolling page rather than a blank frame.
   5. History is written with replaceState, never pushState. Inside an iframe,
      pushing entries would hijack the host page's Back button.
   ========================================================================== */

(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var coarse = window.matchMedia('(hover: none), (pointer: coarse)').matches;

  /* Set by initReveal so tab switches can re-run the visibility sweep over a
     panel that was display:none when the observer first looked at it. */
  var refreshReveal = function () {};

  /* ---------------------------------------------------------------- reveal */
  /* Staggered scroll-in. Elements are pre-hidden by CSS; if IntersectionObserver
     is missing we reveal everything immediately so content is never lost. */
  function initReveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
    if (!items.length) return;

    if (reduced || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('is-in'); });
      return;
    }

    // Stagger siblings within the same grid/stack, capped so a 9-card grid does
    // not take two seconds to finish arriving.
    function show(el) {
      var siblings = el.parentNode ? Array.prototype.slice.call(el.parentNode.children) : [];
      var idx = siblings.indexOf(el);
      el.style.setProperty('--d', Math.min(idx < 0 ? 0 : idx, 5) * 70 + 'ms');
      el.classList.add('is-in');
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        show(entry.target);
        io.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.06 });

    items.forEach(function (el) { io.observe(el); });

    // Backstop. Three things can leave an element permanently invisible if the
    // observer is the only trigger: a fast wheel flick, an anchor jump, and —
    // since the tab rework — a panel that was display:none when the observer
    // last evaluated it, which reports zero intersection forever after until
    // something moves. Sweeping on scroll and on tab switch covers all three.
    var pending = false;
    function sweep() {
      pending = false;
      var bottom = window.innerHeight;
      for (var i = items.length - 1; i >= 0; i--) {
        var el = items[i];
        if (el.classList.contains('is-in')) { items.splice(i, 1); continue; }
        var r = el.getBoundingClientRect();
        // A hidden panel's children measure 0x0 at 0,0 — skip them rather than
        // treating them as visible, or a tab switch reveals with no stagger.
        if (r.width === 0 && r.height === 0) continue;
        if (r.top < bottom) {
          show(el);
          io.unobserve(el);
          items.splice(i, 1);
        }
      }
    }
    function onScroll() {
      if (pending) return;
      pending = true;
      requestAnimationFrame(sweep);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    refreshReveal = function () { requestAnimationFrame(sweep); };
  }

  /* ------------------------------------------------------------------ tabs */
  /* ARIA tabs. Panels are hidden with the `hidden` attribute rather than a
     class so assistive tech and in-page find both skip them. The markup ships
     with nothing hidden, so if this never runs the page degrades to the long
     scrolling layout it used to be instead of showing one panel. */
  function initTabs() {
    var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
    var panels = Array.prototype.slice.call(document.querySelectorAll('.panel'));
    if (!tabs.length || !panels.length) return;

    var params = new URLSearchParams(window.location.search);
    var solo = params.get('solo') === '1';

    function keyOf(el) { return el.getAttribute('data-tab') || el.getAttribute('data-panel'); }

    function panelFor(key) {
      for (var i = 0; i < panels.length; i++) {
        if (keyOf(panels[i]) === key) return panels[i];
      }
      return null;
    }

    function activate(key, focusTab) {
      if (!panelFor(key)) return false;

      tabs.forEach(function (tab) {
        var on = keyOf(tab) === key;
        tab.classList.toggle('is-active', on);
        tab.setAttribute('aria-selected', on ? 'true' : 'false');
        tab.tabIndex = on ? 0 : -1;
        if (on && focusTab) tab.focus();
      });

      panels.forEach(function (panel) {
        var on = keyOf(panel) === key;
        panel.hidden = !on;
        panel.classList.remove('is-entering');
        if (on && !reduced) {
          // Reading offsetWidth restarts the animation when the same panel is
          // re-activated; without it the class is added while already present.
          void panel.offsetWidth;
          panel.classList.add('is-entering');
        }
      });

      // Reflect state in the URL so a tab is linkable, without adding history
      // entries — inside an iframe those would hijack the visitor's Back button.
      try {
        var url = window.location.pathname + window.location.search + '#' + key;
        window.history.replaceState(null, '', url);
      } catch (err) {
        /* opaque origin or a sandbox that blocks history — cosmetic only */
      }

      refreshReveal();
      notifyHeight();
      return true;
    }

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () { activate(keyOf(tab), false); });
    });

    // Roving-tabindex keyboard support, per the ARIA tabs pattern.
    document.querySelectorAll('[role="tablist"]').forEach(function (list) {
      list.addEventListener('keydown', function (e) {
        var idx = tabs.indexOf(document.activeElement);
        if (idx < 0) return;
        var next = -1;
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (idx + 1) % tabs.length;
        else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (idx - 1 + tabs.length) % tabs.length;
        else if (e.key === 'Home') next = 0;
        else if (e.key === 'End') next = tabs.length - 1;
        if (next < 0) return;
        e.preventDefault();
        activate(keyOf(tabs[next]), true);
      });
    });

    // Any control can request a tab: data-goto="work".
    document.querySelectorAll('[data-goto]').forEach(function (el) {
      el.addEventListener('click', function () {
        if (activate(el.getAttribute('data-goto'), false)) window.scrollTo(0, 0);
      });
    });

    // ?tab= wins over #hash; otherwise use whichever tab the markup marked
    // active, which is how the no-JS fallback and the real default agree.
    var wanted = params.get('tab') || window.location.hash.replace('#', '');
    var initial = (wanted && panelFor(wanted)) ? wanted : null;
    if (!initial) {
      var marked = tabs.filter(function (t) { return t.classList.contains('is-active'); })[0];
      initial = keyOf(marked || tabs[0]);
    }

    if (solo) document.body.classList.add('is-solo');
    activate(initial, false);
  }

  /* ------------------------------------------------------------------ tilt */
  /* Pointer-driven 3D rotation plus a cursor-following specular highlight.
     Both are written as CSS custom properties; the CSS owns the actual
     transform so reduced-motion can override it in one place. Skipped
     entirely on touch/coarse pointers, where it only causes jitter. */
  function initTilt() {
    if (reduced || coarse) return;
    var cards = document.querySelectorAll('.tilt');
    var MAX = 3.6; // degrees — past ~5 the text starts to look warped

    Array.prototype.forEach.call(cards, function (card) {
      var frame = null;

      function apply(e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width;
        var py = (e.clientY - r.top) / r.height;
        card.style.setProperty('--ry', ((px - 0.5) * 2 * MAX).toFixed(2) + 'deg');
        card.style.setProperty('--rx', ((0.5 - py) * 2 * MAX).toFixed(2) + 'deg');
        card.style.setProperty('--mx', (px * 100).toFixed(1) + '%');
        card.style.setProperty('--my', (py * 100).toFixed(1) + '%');
        frame = null;
      }

      card.addEventListener('pointermove', function (e) {
        if (frame !== null) return;         // coalesce to one write per frame
        frame = requestAnimationFrame(function () { apply(e); });
      });

      card.addEventListener('pointerenter', function () {
        card.style.setProperty('--lift', '-5px');
      });

      card.addEventListener('pointerleave', function () {
        if (frame !== null) { cancelAnimationFrame(frame); frame = null; }
        card.style.setProperty('--rx', '0deg');
        card.style.setProperty('--ry', '0deg');
        card.style.setProperty('--lift', '0px');
      });
    });
  }

  /* --------------------------------------------------------------- counters */
  /* Animates the numeric part of a metric while preserving its prefix and
     suffix ("~40%", "15M+", "1-2%"). Values with no leading number, or with a
     range like "1-2", are left alone rather than animated wrongly. */
  function initCounters() {
    var nodes = document.querySelectorAll('[data-count]');
    if (!nodes.length) return;
    if (reduced || !('IntersectionObserver' in window)) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var el = entry.target;
        io.unobserve(el);

        var raw = el.textContent.trim();

        // Ranges ("1-2%", "40-50%") must not animate: counting to the first
        // number would render a nonsense intermediate like "0-2%".
        if (/\d\s*[-–]\s*\d/.test(raw)) return;

        // Optional prefix, a number, then the rest ("20M+" -> 20 + "M+").
        var m = /^([^\d]*)(\d+(?:\.\d+)?)([^\d].*)?$/.exec(raw);
        if (!m) return;

        var prefix = m[1] || '';
        var target = parseFloat(m[2]);
        var suffix = m[3] || '';
        var decimals = (m[2].indexOf('.') >= 0) ? 1 : 0;
        if (!isFinite(target) || target === 0) return;

        var DURATION = 1100;
        var start = null;

        function step(ts) {
          if (start === null) start = ts;
          var t = Math.min((ts - start) / DURATION, 1);
          var eased = 1 - Math.pow(1 - t, 3);           // easeOutCubic
          el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
          if (t < 1) requestAnimationFrame(step);
          else el.textContent = raw;                     // restore exact source
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });

    Array.prototype.forEach.call(nodes, function (el) { io.observe(el); });
  }

  /* ---------------------------------------------------------------- filters */
  /* Discipline sub-tabs inside the Selected Work panel. One pillar is active on
     entry so the panel opens at three cards rather than nine. Deliberately not
     persisted — see header note 1. */
  function initFilters() {
    var buttons = document.querySelectorAll('.filter');
    var pillars = document.querySelectorAll('.pillar');
    if (!buttons.length || !pillars.length) return;

    Array.prototype.forEach.call(buttons, function (btn) {
      btn.addEventListener('click', function () {
        var want = btn.getAttribute('data-filter');

        Array.prototype.forEach.call(buttons, function (b) {
          var on = b === btn;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-pressed', on ? 'true' : 'false');
        });

        Array.prototype.forEach.call(pillars, function (p) {
          var show = (want === 'all') || (p.getAttribute('data-pillar') === want);
          p.classList.toggle('is-hidden', !show);
        });

        // Cards in a pillar that was hidden when the observer last looked at it
        // report no intersection, so the sweep has to be re-run by hand.
        refreshReveal();
        notifyHeight();
      });
    });
  }

  /* ----------------------------------------------------------- host height */
  /* Harmless where ignored (Google Sites), useful where honoured. */
  function notifyHeight() {
    if (window.parent === window) return;
    try {
      var h = Math.ceil(document.documentElement.scrollHeight);
      window.parent.postMessage({ type: 'portfolio:height', height: h }, '*');
    } catch (err) {
      /* cross-origin parent refused the message — nothing to do */
    }
  }

  /* -------------------------------------------------------------- smooth nav */
  /* Anchor jumps inside an iframe: scroll our own document, not the host's. */
  function initAnchors() {
    Array.prototype.forEach.call(
      document.querySelectorAll('a[href^="#"]'),
      function (a) {
        a.addEventListener('click', function (e) {
          var id = a.getAttribute('href').slice(1);
          if (!id) return;
          var target = document.getElementById(id);
          if (!target) return;
          e.preventDefault();
          target.scrollIntoView({
            behavior: reduced ? 'auto' : 'smooth',
            block: 'start'
          });
        });
      }
    );
  }

  function boot() {
    try { initReveal(); } catch (e) {}
    try { initTabs(); } catch (e) {}
    try { initTilt(); } catch (e) {}
    try { initCounters(); } catch (e) {}
    try { initFilters(); } catch (e) {}
    try { initAnchors(); } catch (e) {}
    notifyHeight();
    window.addEventListener('load', notifyHeight);
    window.addEventListener('resize', notifyHeight);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
