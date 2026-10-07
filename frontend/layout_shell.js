(function (window, document) {
  'use strict';

  var OFFLINE_BANNER_ID = 'offline-banner';
  var SKIP_LINK_SELECTOR = 'a.skip-link[href="#main-content"]';

  function ensureOfflineBanner() {
    if (document.getElementById(OFFLINE_BANNER_ID)) return;
    var banner = document.createElement('div');
    banner.id = OFFLINE_BANNER_ID;
    banner.style.display = 'none';
    banner.style.position = 'fixed';
    banner.style.top = '0';
    banner.style.left = '0';
    banner.style.right = '0';
    banner.style.background = '#f59e0b';
    banner.style.color = '#000';
    banner.style.textAlign = 'center';
    banner.style.padding = '6px 12px';
    banner.style.fontSize = '13px';
    banner.style.zIndex = '9999';
    banner.style.fontFamily = 'sans-serif';
    banner.textContent = "⚡ You're offline — showing cached content";
    document.body.insertAdjacentElement('afterbegin', banner);
  }

  function ensureSkipLink() {
    if (document.querySelector(SKIP_LINK_SELECTOR)) return;
    var link = document.createElement('a');
    link.href = '#main-content';
    link.className = 'skip-link';
    link.style.position = 'absolute';
    link.style.top = '-40px';
    link.style.left = '0';
    link.style.background = '#818cf8';
    link.style.color = '#fff';
    link.style.padding = '8px 16px';
    link.style.zIndex = '10000';
    link.style.fontSize = '14px';
    link.style.transition = 'top 0.2s';
    link.textContent = 'Skip to content';
    link.addEventListener('focus', function () {
      link.style.top = '0';
    });
    link.addEventListener('blur', function () {
      link.style.top = '-40px';
    });
    document.body.insertAdjacentElement('afterbegin', link);
  }

  function ensureMobileNav() {
    if (document.getElementById('newsday-mobile-nav-style')) return;
    var style = document.createElement('style');
    style.id = 'newsday-mobile-nav-style';
    style.textContent = '@media (max-width:600px){.navbar{display:flex!important;align-items:center;gap:12px;min-height:64px;height:auto!important;padding:12px 16px!important}.navbar-brand{white-space:nowrap;flex-shrink:0}.navbar-links{display:flex!important;flex:1;min-width:0;overflow-x:auto;gap:16px!important;align-items:center}.navbar-links>a{flex-shrink:0;white-space:nowrap}.navbar-avatar{flex-shrink:0}}';
    document.head.appendChild(style);
  }

  function inject() {
    ensureMobileNav();
    ensureOfflineBanner();
    ensureSkipLink();
  }

  window.NewsdayLayoutShell = {
    inject: inject,
  };
})(window, document);
