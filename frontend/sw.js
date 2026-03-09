const CACHE_NAME = 'newsday-v1';
const STATIC_CACHE = 'newsday-static-v1';
const API_CACHE = 'newsday-api-v1';

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
        // Don't cache user-specific or mutation endpoints
        if (url.pathname.includes('/save') ||
            url.pathname.includes('/read') ||
            url.pathname.includes('/feedback') ||
            url.pathname.includes('/auth/')) {
            return;
        }

        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (response.ok) {
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
                    const clone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => cache.put(event.request, clone));
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
