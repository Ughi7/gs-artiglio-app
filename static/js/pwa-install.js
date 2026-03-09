//======PWA INSTALL======
let deferredPrompt;
const installBanner = document.getElementById('pwa-install-banner');
const dismissInstallBannerBtn = document.getElementById('dismissInstallBannerBtn');
const installPWABtn = document.getElementById('installPWABtn');

window.addEventListener('beforeinstallprompt', (e) => {
    // Salva l'evento per usarlo dopo
    deferredPrompt = e;

    // Mostra banner custom al massimo 1 volta al giorno.
    if (installBanner) {
        const lastShown = localStorage.getItem('pwaBannerLastShown');
        const today = new Date().toISOString().slice(0, 10);
        const shouldShowCustom = (lastShown !== today);

        if (shouldShowCustom) {
            e.preventDefault();
            installBanner.style.display = 'block';
            localStorage.setItem('pwaBannerLastShown', today);
        }
    }
});

function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('✅ PWA installata');
            }
            deferredPrompt = null;
            if (installBanner) installBanner.style.display = 'none';
        });
    }
}

function dismissInstallBanner() {
    if (installBanner) installBanner.style.display = 'none';
}

if (dismissInstallBannerBtn && !dismissInstallBannerBtn.dataset.bound) {
    dismissInstallBannerBtn.dataset.bound = 'true';
    dismissInstallBannerBtn.addEventListener('click', dismissInstallBanner);
}

if (installPWABtn && !installPWABtn.dataset.bound) {
    installPWABtn.dataset.bound = 'true';
    installPWABtn.addEventListener('click', installPWA);
}
