const CACHE_NAME = 'beauty-shine-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/pos.html',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests: network-first with offline fallback
  if (url.pathname.startsWith('/api/')) {
    // GET: network-first, fallback to cache
    if (request.method === 'GET') {
      event.respondWith(
        fetch(request)
          .then((response) => {
            const cloned = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned));
            return response;
          })
          .catch(() => caches.match(request))
      );
      return;
    }
    // POST/PUT/DELETE: try network, queue if offline
    if (['POST', 'PUT', 'DELETE'].includes(request.method)) {
      event.respondWith(
        fetch(request.clone()).catch(() => {
          // Store request for background sync
          return request.clone().text().then((body) => {
            const pending = {
              url: request.url,
              method: request.method,
              headers: Object.fromEntries(request.headers.entries()),
              body,
              timestamp: Date.now(),
            };
            // Save to IndexedDB via client message
            self.clients.matchAll().then((clients) => {
              clients.forEach((client) => {
                client.postMessage({ type: 'QUEUE_REQUEST', payload: pending });
              });
            });
            return new Response(
              JSON.stringify({ queued: true, message: 'Request queued for sync' }),
              { status: 202, headers: { 'Content-Type': 'application/json' } }
            );
          });
        })
      );
      return;
    }
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.status === 200) {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, cloned));
        }
        return response;
      });
    })
  );
});

// Background sync
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending-requests') {
    event.waitUntil(syncPendingRequests());
  }
});

async function syncPendingRequests() {
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_START' });
  });
}

// Listen for sync complete message from client
self.addEventListener('message', (event) => {
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
