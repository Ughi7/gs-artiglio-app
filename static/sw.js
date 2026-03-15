const CACHE_NAME = 'artiglio-cache-v5.0.0';
const urlsToCache = [
  '/',
  '/login',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
  'https://fonts.googleapis.com/css2?family=Oswald:wght@400;700&family=Roboto:wght@400;700&display=swap',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'
];

// Installazione del Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Cache aperta');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.log('[SW] Errore durante il caching:', err);
      })
  );
  // Attiva immediatamente il nuovo service worker
  self.skipWaiting();
});

// Attivazione - pulizia vecchie cache
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Eliminazione vecchia cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  // Prendi il controllo di tutte le pagine
  self.clients.claim();
});

// Strategia di fetch IBRIDA per massima fluidità
self.addEventListener('fetch', event => {
  // Ignora richieste non-GET
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora richieste chrome-extension e altri protocolli non-http
  if (!event.request.url.startsWith('http')) {
    return;
  }

  const url = new URL(event.request.url);

  // === STRATEGIA 1: CACHE-FIRST per risorse CDN statiche (Bootstrap, Fonts, Icons) ===
  // Queste risorse cambiano raramente, usiamo la cache per velocità massima
  if (url.hostname.includes('cdn.jsdelivr.net') ||
    url.hostname.includes('fonts.googleapis.com') ||
    url.hostname.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.match(event.request).then(cachedResponse => {
        if (cachedResponse) {
          // Aggiorna in background per prossima visita
          fetch(event.request).then(response => {
            if (response && response.status === 200) {
              caches.open(CACHE_NAME).then(cache => {
                cache.put(event.request, response);
              });
            }
          }).catch(() => { });
          return cachedResponse;
        }
        // Se non in cache, scarica e salva
        return fetch(event.request).then(response => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // === STRATEGIA 2: NETWORK-FIRST per API (dati sempre freschi) ===
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => response)
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // === STRATEGIA 3: NETWORK-FIRST per pagine HTML (dati sempre freschi!) ===
  // Le modifiche dell'utente (multe, assenze, turni) sono visibili SUBITO
  // La cache viene usata solo come fallback quando offline
  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        // Salva in cache per uso offline
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Se offline, usa la cache
        return caches.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Se navigazione e niente in cache, ritorna homepage
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
          return new Response('', {
            status: 503,
            statusText: 'Offline'
          });
        });
      })
  );
});

// Gestione messaggi dal client
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// ====== PUSH NOTIFICATIONS ======

// Gestione evento PUSH (quando arriva una notifica dal server)
self.addEventListener('push', event => {
  console.log('[SW] Push ricevuto:', event);

  let data = {
    title: 'GS Artiglio',
    body: 'Nuova notifica!',
    icon: '/static/icons3/icon-192x192.png',
    badge: '/static/icons3/icon-72x72.png',
    tag: 'artiglio-notification',
    data: { url: '/' }
  };

  // Prova a parsare il payload JSON
  if (event.data) {
    try {
      const payload = event.data.json();
      data = { ...data, ...payload };
    } catch (e) {
      // Se non è JSON, usa il testo come body
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || '/static/icons3/icon-192x192.png',
    badge: data.badge || '/static/icons3/icon-72x72.png',
    tag: data.tag || 'artiglio-notification',
    vibrate: [200, 100, 200],
    data: data.data || { url: '/' },
    requireInteraction: false
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Gestione click sulla notifica
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notifica cliccata:', event.notification.tag);

  event.notification.close();

  // Apri o focalizza la finestra dell'app
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windowClients => {
        // Cerca una finestra già aperta
        for (const client of windowClients) {
          // Controlla se è una finestra della nostra app
          if ('focus' in client) {
            // Se siamo già sull'URL giusto, dacci solo il focus
            if (client.url === new URL(urlToOpen, self.location.origin).href) {
              return client.focus();
            }
            // Altrimenti naviga e poi focus
            client.navigate(urlToOpen);
            return client.focus();
          }
        }
        // Altrimenti apri una nuova finestra
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Gestione chiusura notifica
self.addEventListener('notificationclose', event => {
  console.log('[SW] Notifica chiusa:', event.notification.tag);
});
