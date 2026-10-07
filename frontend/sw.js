const CACHE_NAME = 'newsday-v3';
const STATIC_CACHE = 'newsday-static-v3';
const API_CACHE = 'newsday-api-v3';

// Pages to pre-cache (must match backend routes)
const PRECACHE_URLS = [
    '/',
    '/department.html',
    '/insights.html',
    '/stories.html',
    '/research.html',
    '/auth.html',
    '/skills.html'
];

// Install: pre-cache HTML pages
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => cache.addAll(PRECACHE_URLS))
    );
    self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(names =>
            Promise.all(names.filter(n => n !== STATIC_CACHE && n !== API_CACHE).map(n => caches.delete(n)))
        )
    );
    self.clients.claim();
});

// Fetch strategy
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // API requests: Network First, Cache Fallback
    if (url.pathname.startsWith('/api/')) {
        // Only explicitly public feed responses can enter shared offline caches.
        const publicPath = /^\/api\/v1\/(feed\/(trending|breaking|daily-digest|all-sections|category\/[^/]+))$/.test(url.pathname);
        if (!publicPath || url.origin !== self.location.origin) return;

        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response.ok && !/private|no-store/i.test(response.headers.get("Cache-Control") || "")) {
                        const clone = response.clone();
                        caches.open(API_CACHE).then(cache => cache.put(event.request, clone));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // HTML pages: Network First, Cache Fallback
    if (event.request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (!response.ok) return response;
                    const clone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // Keep auth session helper fresh to avoid stale login/session logic.
    if (url.pathname === '/auth_session.js') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    // Static assets: Cache First, Network Fallback
    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) return cached;
            return fetch(event.request).then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
                }
                return response;
            });
        })
    );
});
