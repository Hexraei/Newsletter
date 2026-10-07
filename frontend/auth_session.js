(function (window) {
  'use strict';

  var STORAGE_KEY = 'newsday_session';
  var DEPT_KEY = 'newsday_dept';
  var origin = (window.location && window.location.origin && window.location.origin !== 'null')
    ? window.location.origin
    : '';
  var API_BASE = origin + '/api/v1';

  var DEPT_NAME_TO_KEY = {
    'COMPUTER SCIENCE & ENGINEERING': 'CSE',
    'INFORMATION TECHNOLOGY': 'IT',
    'ARTIFICIAL INTELLIGENCE & DATA SCIENCE': 'AIDS',
    'ELECTRONICS & COMMUNICATION': 'ECE',
    'ELECTRICAL & ELECTRONICS': 'EEE',
    'MECHANICAL ENGINEERING': 'ME',
    'CIVIL ENGINEERING': 'CE',
    'BIOTECHNOLOGY ENGINEERING': 'BT',
    'CHEMICAL ENGINEERING': 'CH',
    'AERONAUTICAL / AEROSPACE': 'AE',
    'ROBOTICS & AUTOMATION ENGINEERING': 'RAE',
    'PRODUCTION TECHNOLOGY': 'PT',
  };

  function normalizeDeptKey(value) {
    if (!value || typeof value !== 'string') return null;
    var raw = value.trim().toUpperCase();
    return DEPT_NAME_TO_KEY[raw] || raw;
  }

  function readRawSession() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    } catch (e) {
      return null;
    }
  }

  function getSession(options) {
    var opts = options || {};
    var allowExpired = !!opts.allowExpired;
    var session = readRawSession();
    if (!session || !session.authenticated) return null;
    if (!allowExpired && session.expires_at && Date.now() > session.expires_at) {
      clearSession();
      return null;
    }
    return session;
  }

  function saveSession(data, options) {
    var payload = data || {};
    var opts = options || {};
    var existing = readRawSession() || {};
    var expiresIn = Number(payload.expires_in || opts.expiresIn || 3600);
    var hasExplicitExpiry = (opts.expiresAt !== undefined) || (payload.expires_at !== undefined);
    var hasTokenPayload = !!(payload.access_token || payload.refresh_token || payload.expires_in);
    var expiresAt;

    if (hasExplicitExpiry) {
      expiresAt = Number((opts.expiresAt !== undefined) ? opts.expiresAt : payload.expires_at);
    } else if (hasTokenPayload || !existing.expires_at) {
      // Fresh login/refresh should always mint a new client-side expiry window.
      expiresAt = Date.now() + expiresIn * 1000;
    } else {
      // Profile-only sync keeps current expiry unchanged.
      expiresAt = Number(existing.expires_at);
    }
    if (!Number.isFinite(expiresAt) || expiresAt <= 0) {
      expiresAt = Date.now() + expiresIn * 1000;
    }
    var user = (opts.user !== undefined) ? opts.user : (payload.user || existing.user || null);

    var session = {
      authenticated: true,
      user: user,
      expires_at: expiresAt,
      token_type: payload.token_type || existing.token_type || 'bearer',
      last_synced_at: Date.now(),
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));

    var dept = user ? normalizeDeptKey(user.department_key || user.department) : null;
    var currentDept = localStorage.getItem(DEPT_KEY);
    if (dept && (!currentDept || opts.syncDeptFromProfile === true)) {
      localStorage.setItem(DEPT_KEY, dept);
    }
    return session;
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function parseResponseJson(response) {
    return response.json().catch(function () { return null; });
  }

  async function api(path, init) {
    var response = await fetch(API_BASE + path, Object.assign({
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    }, init || {}));
    var data = await parseResponseJson(response);
    return { ok: response.ok, status: response.status, data: data, response: response };
  }

  async function refreshSession() {
    var refreshed = await api('/auth/refresh', { method: 'POST' });
    if (!refreshed.ok || !refreshed.data) return false;
    saveSession(refreshed.data);
    return true;
  }

  async function syncProfile(options) {
    var opts = options || {};
    var allowRefresh = opts.allowRefresh !== false;

    var me = await api('/auth/me');
    if (!me.ok && allowRefresh && me.status === 401) {
      var refreshed = await refreshSession();
      if (refreshed) me = await api('/auth/me');
    }

    if (!me.ok || !me.data || !me.data.data) {
      if (me.status === 401 || me.status === 403) clearSession();
      return null;
    }
    var user = me.data.data;
    saveSession({}, { user: user });
    return user;
  }

  async function ensureAuthenticated(options) {
    var opts = options || {};
    var redirectTo = (opts.redirectTo === undefined) ? 'auth.html' : opts.redirectTo;
    var syncProfileOnSuccess = opts.syncProfileOnSuccess !== false;
    var allowRefresh = opts.allowRefresh !== false;

    var session = getSession();
    if (!session) {
      var recoveredUser = await syncProfile({ allowRefresh: allowRefresh });
      if (!recoveredUser) {
        clearSession();
        if (redirectTo) window.location.replace(redirectTo);
        return false;
      }
      return true;
    }

    if (syncProfileOnSuccess) {
      var user = await syncProfile({ allowRefresh: allowRefresh });
      if (!user && !getSession()) {
        clearSession();
        if (redirectTo) window.location.replace(redirectTo);
        return false;
      }
    }

    return true;
  }

  function userDisplayName(user) {
    if (!user) return '';
    return user.full_name || (user.user_metadata && user.user_metadata.full_name) || user.email || '';
  }

  function userInitials(user) {
    var name = userDisplayName(user).trim();
    if (!name) return '';
    if (name.indexOf('@') !== -1) return name.charAt(0).toUpperCase();
    return name
      .split(/\s+/)
      .filter(Boolean)
      .map(function (part) { return part.charAt(0).toUpperCase(); })
      .join('')
      .slice(0, 2);
  }

  function ensureAvatarElement(navLink, selector) {
    var avatar = selector ? document.querySelector(selector) : document.getElementById('navbar-avatar');
    if (!avatar && navLink) {
      avatar = document.createElement('div');
      avatar.id = 'navbar-avatar';
      avatar.className = 'navbar-avatar';
      navLink.insertAdjacentElement('afterend', avatar);
    }
    return avatar;
  }

  async function initNavbarAuth(options) {
    var opts = options || {};
    var navLink = (opts.linkSelector && document.querySelector(opts.linkSelector))
      || document.getElementById('nav-auth-link')
      || document.querySelector('.navbar-links a[href="auth.html"]');
    if (!navLink) return false;

    var ok = await ensureAuthenticated({ redirectTo: null, syncProfileOnSuccess: true });
    var session = getSession();
    if (!ok || !session) {
      navLink.textContent = 'Log In';
      navLink.href = 'auth.html';
      return false;
    }

    navLink.textContent = 'Log Out';
    navLink.href = '#';
    navLink.onclick = async function (event) {
      event.preventDefault();
      try {
        await api('/auth/logout', { method: 'POST' });
      } catch (e) {
        // no-op; local clear still guarantees logout UX
      }
      clearSession();
      window.location.href = opts.redirectTo || 'auth.html';
    };

    var avatar = ensureAvatarElement(navLink, opts.avatarSelector);
    if (avatar) {
      var initials = userInitials(session.user);
      if (initials) {
        avatar.textContent = initials;
        avatar.title = userDisplayName(session.user);
        avatar.style.display = 'flex';
        avatar.style.alignItems = 'center';
        avatar.style.justifyContent = 'center';
        avatar.style.width = '30px';
        avatar.style.height = '30px';
        avatar.style.borderRadius = '999px';
        avatar.style.fontSize = '11px';
        avatar.style.fontWeight = '700';
      } else {
        avatar.style.display = 'none';
      }
    }

    return true;
  }

  window.NewsdayAuth = {
    API_BASE: API_BASE,
    getSession: getSession,
    saveSession: saveSession,
    clearSession: clearSession,
    refreshSession: refreshSession,
    syncProfile: syncProfile,
    ensureAuthenticated: ensureAuthenticated,
    initNavbarAuth: initNavbarAuth,
  };
})(window);
