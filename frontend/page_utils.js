(function (window) {
  'use strict';

  function requireAuth() {
    return (async function () {
      if (!window.NewsdayAuth) {
        window.location.replace('auth.html');
        return false;
      }
      return window.NewsdayAuth.ensureAuthenticated({
        redirectTo: 'auth.html',
        syncProfileOnSuccess: true,
      });
    })();
  }

  function fetchWithTimeout(url, options, timeout) {
    var finalOptions = options || {};
    var finalTimeout = Number(timeout || 8000);
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, finalTimeout);
    return fetch(url, Object.assign({}, finalOptions, { signal: controller.signal }))
      .finally(function () { clearTimeout(timer); });
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function shortText(value, max) {
    var limit = Number(max || 110);
    var text = String(value || '').replace(/\s+/g, ' ').trim();
    if (!text) return '';
    return text.length > limit ? text.slice(0, limit - 3).trim() + '...' : text;
  }

  function normalizeText(value) {
    return String(value || '').toLowerCase();
  }

  function cleanAiLine(value) {
    return String(value || '')
      .replace(/\*\*/g, '')
      .replace(/^#+\s*/g, '')
      .replace(/^(hook|why it matters|key points|action step)\s*:\s*/i, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function stripSourcePrefix(text) {
    var out = String(text || '').trim();
    if (!out) return out;
    out = out.replace(/^(reddit|hacker\s*news|github|medium|product\s*hunt|x|twitter|cs\s*desk|campus\s*tech)\s*[-|:]\s*/i, '');
    out = out.replace(/^r\/[a-z0-9_]+\s*[-|:]\s*/i, '');
    out = out.replace(/^(reddit|hacker\s*news|github|medium)\s*[-|:]\s*r\/[a-z0-9_]+\s*[-|:]\s*/i, '');
    return out.trim();
  }

  function countWords(text) {
    return String(text || '').trim().split(/\s+/).filter(Boolean).length;
  }

  function trimToWordCount(text, maxWords) {
    var words = String(text || '').trim().split(/\s+/).filter(Boolean);
    if (words.length <= maxWords) return words.join(' ');
    return words.slice(0, maxWords).join(' ').replace(/[,:;\-]+$/, '') + '.';
  }

  function isUsefulAiLine(value) {
    var text = cleanAiLine(value);
    if (!text) return false;
    if (text.length < 16) return false;
    if (/^\W+$/.test(text)) return false;
    if (/^key points?$/i.test(text)) return false;
    return /[a-zA-Z]{4,}/.test(text);
  }

  window.NewsdayPageUtils = {
    requireAuth: requireAuth,
    fetchWithTimeout: fetchWithTimeout,
    escapeHtml: escapeHtml,
    shortText: shortText,
    normalizeText: normalizeText,
    cleanAiLine: cleanAiLine,
    stripSourcePrefix: stripSourcePrefix,
    countWords: countWords,
    trimToWordCount: trimToWordCount,
    isUsefulAiLine: isUsefulAiLine,
  };
})(window);
