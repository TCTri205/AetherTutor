/**
 * Service Worker cho AetherTutor PWA.
 *
 * Features:
 * - Cache-first cho static assets
 * - Network-first cho API calls
 * - Offline fallback page
 * - Push notification handler
 * - Background sync cho pending operations
 *
 * Strategy:
 * - Static assets (JS/CSS/images): CacheFirst
 * - API calls: NetworkFirst với stale-while-revalidate
 * - Flashcards/Notes: StaleWhileRevalidate (cache để offline)
 * - HTML pages: NetworkFirst với offline fallback
 */

const CACHE_NAME = "aethertutor-v1";
const OFFLINE_URL = "/offline";

// Assets to cache immediately on install
const STATIC_ASSETS = [
  "/",
  "/offline",
  "/manifest.json",
  "/icons/icon-192x192.png",
  "/icons/icon-512x512.png",
];

// API routes to cache for offline access
const OFFLINE_CACHED_ROUTES = [
  "/api/v1/flashcards",
  "/api/v1/notes",
];

// ---------------------------------------------------------------------------
// Install event — cache static assets
// ---------------------------------------------------------------------------
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.error("Failed to cache static assets:", err);
      });
    })
  );
  self.skipWaiting();
});

// ---------------------------------------------------------------------------
// Activate event — clean old caches
// ---------------------------------------------------------------------------
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// ---------------------------------------------------------------------------
// Fetch event — serve from cache or network
// ---------------------------------------------------------------------------
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith("http")) return;

  // API requests: NetworkFirst
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets: CacheFirst
  event.respondWith(cacheFirst(request));
});

// ---------------------------------------------------------------------------
// Push event — show notification
// ---------------------------------------------------------------------------
self.addEventListener("push", (event) => {
  const data = event.data?.json();
  if (!data) return;

  const options: NotificationOptions = {
    body: data.body || "Bạn có thông báo mới",
    icon: data.icon || "/icons/icon-192x192.png",
    badge: data.badge || "/icons/icon-192x192.png",
    data: data.data || {},
    actions: data.actions || [],
    tag: data.tag || "default",
    renotify: !!data.tag,
  };

  event.waitUntil(
    self.registration.showNotification(data.title || "AetherTutor", options)
  );
});

// ---------------------------------------------------------------------------
// Notification click — open app
// ---------------------------------------------------------------------------
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clients) => {
      // Focus existing window if open
      for (const client of clients) {
        if (client.url.includes(self.location.origin)) {
          return client.focus();
        }
      }
      // Open new window
      return self.clients.openWindow("/");
    })
  );
});

// ---------------------------------------------------------------------------
// Cache strategies
// ---------------------------------------------------------------------------

async function networkFirst(request: Request): Promise<Response> {
  try {
    // Try network first
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (err) {
    // Network failed — try cache
    const cached = await caches.match(request);
    if (cached) return cached;

    // Return offline fallback for HTML
    if (request.destination === "document") {
      return caches.match(OFFLINE_URL) || Response.error();
    }

    throw err;
  }
}

async function cacheFirst(request: Request): Promise<Response> {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Return offline fallback
    if (request.destination === "document") {
      return caches.match(OFFLINE_URL) || Response.error();
    }

    throw err;
  }
}
