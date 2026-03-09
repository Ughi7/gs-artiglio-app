// Service Worker Registration
const PUSH_BANNER_DISMISS_MS = 30 * 24 * 60 * 60 * 1000;
const PUSH_BANNER_SHOW_DELAY_MS = 3000;

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => {
                console.log('✅ SW Registrato');
                initPushUI(); // Inizializza UI solo dopo la registrazione
            })
            .catch(err => console.log('❌ SW Error:', err));
    });
}

const dismissPushBannerBtn = document.getElementById('dismissPushBannerBtn');
const activatePushBannerBtn = document.getElementById('activatePushBannerBtn');
const pushToggleSwitch = document.getElementById('pushToggleSwitch');

if (dismissPushBannerBtn && !dismissPushBannerBtn.dataset.bound) {
    dismissPushBannerBtn.dataset.bound = 'true';
    dismissPushBannerBtn.addEventListener('click', dismissPushBanner);
}

if (activatePushBannerBtn && !activatePushBannerBtn.dataset.bound) {
    activatePushBannerBtn.dataset.bound = 'true';
    activatePushBannerBtn.addEventListener('click', activatePushFromBanner);
}

if (pushToggleSwitch && !pushToggleSwitch.dataset.bound) {
    pushToggleSwitch.dataset.bound = 'true';
    pushToggleSwitch.addEventListener('change', function () {
        togglePushFromModal(this);
    });
}

// Rilevamento browser per compatibilità notifiche
function detectBrowser() {
    const ua = navigator.userAgent;
    const isFirefox = ua.includes('Firefox');
    const isSafari = /^((?!chrome|android).)*safari/i.test(ua) && !ua.includes('Chrome');
    const isChrome = /Chrome/.test(ua) && /Google Inc/.test(navigator.vendor);
    const isEdge = /Edg/.test(ua);
    const isPWA = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

    return { isFirefox, isSafari, isChrome, isEdge, isPWA };
}

// Gestione UI Notifiche
async function initPushUI() {
    //const notifBtn = document.getElementById('enableNotifBtn'); // REMOVED
    const switchEl = document.getElementById('pushToggleSwitch');

    if (!('PushManager' in window)) {
        const container = document.getElementById('pushControlBox');
        if (container) container.style.display = 'none';
        return;
    }

    const browser = detectBrowser();

    // Firefox PWA: notifiche NON supportate
    if (browser.isFirefox && browser.isPWA) {
        console.warn('[PUSH] Firefox PWA non supporta notifiche push');
        updatePushModalUI(false, true);
        // Non nascondiamo, ma mostriamo lo stato bloccato
        return;
    }

    try {
        // Aspetta che il SW sia PRONTO
        const registration = await navigator.serviceWorker.ready;

        if (!registration.pushManager) {
            console.warn('[PUSH] PushManager non disponibile');
            return;
        }

        const subscription = await registration.pushManager.getSubscription();

        if (subscription) {
            // Utente già iscritto
            updatePushModalUI(true);
            hidePushBanner(); // Nascondi banner se attivo
        } else if (Notification.permission === 'denied') {
            // Utente ha bloccato
            updatePushModalUI(false, true);
        } else {
            // Utente non iscritto - mostra banner se appropriato
            updatePushModalUI(false);
            checkPushBanner();
        }
    } catch (error) {
        console.error('[PUSH] Errore inizializzazione:', error);
    }
}

// === PUSH NOTIFICATION BANNER LOGIC ===
function checkPushBanner() {
    const banner = document.getElementById('push-prompt-banner');
    if (!banner) return;

    // Controlla se l'utente ha chiesto di non mostrare
    const dismissedDate = localStorage.getItem('push-banner-dismissed');
    if (dismissedDate) {
        const dismissed = new Date(dismissedDate);
        const now = new Date();
        if (!Number.isNaN(dismissed.getTime()) && now - dismissed < PUSH_BANNER_DISMISS_MS) {
            return; // Non mostrare, non è passato un mese
        }
    }

    // Mostra il banner dopo un breve ritardo
    setTimeout(() => {
        banner.style.display = 'block';
    }, PUSH_BANNER_SHOW_DELAY_MS);
}

function dismissPushBanner() {
    const banner = document.getElementById('push-prompt-banner');
    if (banner) banner.style.display = 'none';
    localStorage.setItem('push-banner-dismissed', new Date().toISOString());
}

function hidePushBanner() {
    const banner = document.getElementById('push-prompt-banner');
    if (banner) banner.style.display = 'none';
}

async function activatePushFromBanner() {
    const banner = document.getElementById('push-prompt-banner');
    if (banner) banner.style.display = 'none';

    try {
        if (typeof subscribeUserToPush === 'function') {
            await subscribeUserToPush();
        } else {
            // Fallback: chiedi permesso e ricarica
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                location.reload();
            }
        }
    } catch (err) {
        console.error('[PUSH BANNER] Errore attivazione:', err);
    }
}

function updatePushModalUI(isActive, isBlocked = false) {
    const switchEl = document.getElementById('pushToggleSwitch');
    const statusText = document.querySelector('.display-notif-status');
    const statusDesc = document.querySelector('.display-notif-desc');
    const icon = document.getElementById('pushIconModal');
    const errorMsg = document.getElementById('pushErrorMsg');

    if (!switchEl) return;

    if (isActive) {
        switchEl.checked = true;
        switchEl.disabled = false;
        if (statusText) statusText.textContent = 'Attive';
        if (statusText) statusText.classList.add('text-success');
        if (statusText) statusText.classList.remove('text-danger', 'text-warning');
        if (statusDesc) statusDesc.textContent = 'Ricevi aggiornamenti sulle partite';
        if (icon) icon.className = 'bi bi-bell-fill text-success me-3 fs-4';
    } else if (isBlocked) {
        switchEl.checked = false;
        switchEl.disabled = true; // Non può attivare da qui se bloccato
        if (statusText) statusText.textContent = 'Bloccate dal Browser';
        if (statusText) statusText.classList.add('text-danger');
        if (statusDesc) statusDesc.textContent = 'Devi sbloccarle dalle impostazioni del browser';
        if (icon) icon.className = 'bi bi-bell-slash-fill text-danger me-3 fs-4';
        if (errorMsg) {
            errorMsg.style.display = 'block';
            errorMsg.textContent = '⚠️ Permessi notifiche negati. Modifica le impostazioni del sito nel browser.';
        }
    } else {
        switchEl.checked = false;
        switchEl.disabled = false;
        if (statusText) statusText.textContent = 'Disattivate';
        if (statusText) statusText.classList.remove('text-success', 'text-danger');
        if (statusDesc) statusDesc.textContent = 'Attiva per ricevere aggiornamenti';
        if (icon) icon.className = 'bi bi-bell text-warning me-3 fs-4';
    }
}

// Funzione chiamata dal toggle switch del modal
async function togglePushFromModal(el) {
    const isChecking = el.checked;

    if (isChecking) {
        // Tenta ATTIVAZIONE
        const browser = detectBrowser();

        // Check preliminari (compatibilità)
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            // Check specifico per Firefox PWA
            if (browser.isFirefox && browser.isPWA) {
                alert('⚠️ Firefox non supporta le notifiche nelle app installate (PWA).\n\n💡 Riapri l\'app con Chrome o Edge per ricevere notifiche.');
            } else {
                alert('Il tuo browser non supporta le notifiche push.');
            }
            el.checked = false;
            return;
        }

        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                await subscribeUserToPush();
                updatePushModalUI(true);
            } else {
                updatePushModalUI(false, true); // Negato
            }
        } catch (e) {
            console.error(e);
            el.checked = false;
            // Mostra errore
            const errorMsg = document.getElementById('pushErrorMsg');
            if (errorMsg) {
                errorMsg.style.display = 'block';
                errorMsg.textContent = 'Errore attivazione: ' + e.message;
            }
        }
    } else {
        // Tenta DISATTIVAZIONE
        try {
            await unsubscribeUserFromPush();
            updatePushModalUI(false);
        } catch (e) {
            console.error(e);
            el.checked = true; // Revert
            alert('Errore disattivazione: ' + e.message);
        }
    }
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function subscribeUserToPush() {
    const registration = await navigator.serviceWorker.ready;

    // Fetch vapid key
    const response = await fetch('/get_vapid_public_key');
    if (!response.ok) {
        throw new Error('Impossibile recuperare la chiave pubblica VAPID');
    }
    const data = await response.json();
    if (!data.public_key) {
        throw new Error('Chiave pubblica VAPID mancante');
    }
    const applicationServerKey = urlBase64ToUint8Array(data.public_key);

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey
    });

    // Invia al backend
    const saveResponse = await fetch('/api/push/subscribe', {
        method: 'POST',
        body: JSON.stringify(subscription),
        headers: {
            'Content-Type': 'application/json'
        }
    });

    if (!saveResponse.ok) {
        throw new Error('Registrazione subscription fallita');
    }
}

async function unsubscribeUserFromPush() {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (subscription) {
        // Notifica prima il backend
        const deleteResponse = await fetch('/api/push/unsubscribe', {
            method: 'POST',
            body: JSON.stringify({ endpoint: subscription.endpoint }),
            headers: { 'Content-Type': 'application/json' }
        });

        if (!deleteResponse.ok) {
            throw new Error('Disattivazione lato server fallita');
        }

        // Poi disiscrivi dal browser
        await subscription.unsubscribe();
    }
}
