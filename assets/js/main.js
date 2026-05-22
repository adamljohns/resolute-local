/* USMC Ministries — shared site JS (nav toggle, theme toggle, accessibility) */
(function () {
  'use strict';

  // ── Mobile nav toggle ─────────────────────────────────────────────
  var navToggle = document.querySelector('.nav-toggle');
  var navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.setAttribute('aria-expanded', 'false');
    navToggle.setAttribute('aria-controls', 'nav-links');
    if (!navLinks.id) navLinks.id = 'nav-links';
    navToggle.addEventListener('click', function () {
      var open = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // ── Theme toggle (dark default, light opt-in, persisted) ─────────
  var themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    var saved = localStorage.getItem('usmc-theme');
    var startDark = saved !== 'light';
    applyTheme(startDark);
    themeToggle.addEventListener('click', function () {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      applyTheme(!isDark);
      localStorage.setItem('usmc-theme', isDark ? 'light' : 'dark');
    });
  }

  function applyTheme(dark) {
    if (dark) {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (themeToggle) {
        themeToggle.textContent = '☀️'; // ☀️
        themeToggle.setAttribute('aria-pressed', 'true');
        themeToggle.setAttribute('aria-label', 'Switch to light mode');
      }
    } else {
      document.documentElement.removeAttribute('data-theme');
      if (themeToggle) {
        themeToggle.textContent = '🌙'; // 🌙
        themeToggle.setAttribute('aria-pressed', 'false');
        themeToggle.setAttribute('aria-label', 'Switch to dark mode');
      }
    }
  }
})();
