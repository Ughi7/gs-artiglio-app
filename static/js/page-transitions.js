// ========================================
// 🛡️ GS ARTIGLIO - SPA ROUTER (Vanilla JS)
// ========================================

document.addEventListener('DOMContentLoaded', () => {

    function initCurrentPage() {
        const path = window.location.pathname;

        if (path === '/' || path.includes('/dashboard')) {
            if (typeof window.initDashboard === 'function') window.initDashboard();
        } else if (path.includes('/stats_partite')) {
            if (typeof window.initStatsPartite === 'function') window.initStatsPartite(window.__statsPartiteData);
        } else if (path.includes('/stats_multe')) {
            if (typeof window.initStatsMulte === 'function') window.initStatsMulte(window.__statsMulteData);
        } else if (path.includes('/rosa')) {
            if (typeof window.initRosa === 'function') window.initRosa();
        } else if (path.includes('/partite')) {
            if (typeof window.initPartite === 'function') window.initPartite();
        } else if (path.includes('/multe')) {
            if (typeof window.initMulte === 'function') window.initMulte();
        } else if (path.includes('/admin/feedback')) {
            if (typeof window.initAdminFeedback === 'function') window.initAdminFeedback();
        } else if (path.includes('/aggiornamenti')) {
            if (typeof window.initAggiornamenti === 'function') window.initAggiornamenti();
        } else if (/^\/video\/\d+\/comments$/.test(path)) {
            if (typeof window.initVideoComments === 'function') window.initVideoComments();
        } else if (path === '/video') {
            if (typeof window.initVideoList === 'function') window.initVideoList();
        } else if (path.includes('/game') || path.includes('/flappy-eagle')) {
            const canvasObj = document.getElementById('gameCanvas');
            const adminObj = canvasObj ? canvasObj.dataset.isAdmin === 'true' : false;
            if (typeof window.initGameUI === 'function') window.initGameUI(adminObj);
            if (typeof window.initGameEngine === 'function') window.initGameEngine(adminObj);
        } else if (path.includes('/calendario')) {
            if (typeof window.initCalendario === 'function') window.initCalendario();
        } else if (path.includes('/presenze')) {
            if (typeof window.initPresenze === 'function') window.initPresenze();
        }
    }

    async function hydrateInjectedScripts(root) {
        const scripts = Array.from(root.querySelectorAll('script'));

        for (const oldScript of scripts) {
            const src = oldScript.getAttribute('src');

            if (src) {
                const resolvedSrc = new URL(src, window.location.href).href;
                const alreadyLoaded = Array.from(document.scripts).some(script => script.src === resolvedSrc);

                if (!alreadyLoaded) {
                    await new Promise(resolve => {
                        const newScript = document.createElement('script');
                        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                        newScript.onload = resolve;
                        newScript.onerror = resolve;
                        document.body.appendChild(newScript);
                    });
                }

                oldScript.remove();
                continue;
            }

            const newScript = document.createElement('script');
            Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
            newScript.textContent = oldScript.textContent;
            oldScript.replaceWith(newScript);
        }
    }

    function cleanupBootstrapState() {
        document.querySelectorAll('.modal.show').forEach(modalEl => {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        });

        document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('padding-right');
        document.body.style.removeProperty('overflow');
    }

    // === GLOBAL APP INITIALIZER ===
    // Chiamata al primo caricamento e dopo ogni navigazione SPA
    window.initAppFeatures = function () {
        if (typeof window.initAnimations === 'function') window.initAnimations();
        if (typeof window.initPullToRefresh === 'function') window.initPullToRefresh();
        if (typeof window.initAntiDoubleSubmit === 'function') window.initAntiDoubleSubmit();
        if (typeof window.initToast === 'function') window.initToast();

        // Reinizializza i componenti Bootstrap sui nodi corretti dopo l'iniezione SPA.
        document.querySelectorAll('.collapse').forEach(el => bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }));
        document.querySelectorAll('.dropdown-toggle').forEach(el => bootstrap.Dropdown.getOrCreateInstance(el));
        document.querySelectorAll('.modal').forEach(el => bootstrap.Modal.getOrCreateInstance(el));
    };

    // Inizializza subito al primo caricamento
    initAppFeatures();

    const mainContainer = document.getElementById('main-container');
    if (!mainContainer) return;

    // Aggiunge logica per catturare link SPA
    const setupSPALinks = () => {
        // Intercetta link nella bottom nav e ovunque tranne forms, bottoni o esterni
        document.querySelectorAll('a').forEach(link => {
            if (link.hostname !== window.location.hostname) return; // Escludi link esterni
            if (link.getAttribute('target') === '_blank') return; // Escludi download/nuove tab
            if (link.hasAttribute('data-bs-toggle')) return; // Escludi link bootstrap (tab, modal)
            if (link.getAttribute('href') && link.getAttribute('href').startsWith('#')) return; // Escludi anchor interni
            if (link.getAttribute('href') && link.getAttribute('href').includes('/admin')) return; // Escludi /admin routes
            if (link.getAttribute('href') && link.getAttribute('href').includes('/auth')) return; // Escludi roba auth
            if (link.getAttribute('href') && link.getAttribute('href').includes('/logout')) return; // Logout deve rifare render completo
            if (link.getAttribute('href') && window.location.pathname.startsWith('/game')) return; // Evita problemi col game

            // Aggiungi un flag per non attaccare doppio listener
            if (link.dataset.spaBound) return;
            link.dataset.spaBound = 'true';

            link.addEventListener('click', async function (e) {
                // Se modifier keys sono usati, lascia decidere al browser (apri in nuova tab)
                if (e.ctrlKey || e.metaKey || e.shiftKey) return;

                e.preventDefault();
                const url = this.getAttribute('href');
                if (!url) return;

                // 1. UPDATE NAVBAR HIGHLIGHT
                if (this.classList.contains('nav-icon-link')) {
                    document.querySelectorAll('.nav-icon-link').forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                }

                // 2. ESEGUI TRANSIZIONE E FETCH
                await navigateTo(url);
            });
        });
    };

    // Chiama al caricamento e dopo ogni cambio pagina per bindare nuovi link
    setupSPALinks();
    initCurrentPage();

    // Navigazione principale Ajax
    window.navigateTo = async function (url, isPopState = false) {
        cleanupBootstrapState();

        // Effetto FADE OUT immediato per nascondere il container
        mainContainer.style.opacity = '0.3';
        mainContainer.style.transition = 'opacity 0.2s ease-out';

        // Barra caricamento top (opzionale se piace, o solo feedback nav)

        try {
            const response = await fetch(url, {
                headers: { 'X-SPA-Request': 'true' }
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const text = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');

            const newMain = doc.getElementById('main-container');
            if (newMain) {
                // Aggiorna History (se non è un tasto Indietro)
                if (!isPopState) {
                    history.pushState({ url: url }, '', url);
                }

                // Aggiorna titolo
                const newTitle = doc.querySelector('title');
                if (newTitle) {
                    document.title = newTitle.textContent;
                }

                // Inietta stili extra caricati in head (es: components.css)
                doc.querySelectorAll('head link[rel="stylesheet"]').forEach(newLink => {
                    const href = newLink.getAttribute('href');
                    if (href && !document.head.querySelector(`link[href="${href}"]`)) {
                        const linkNode = document.createElement('link');
                        linkNode.rel = 'stylesheet';
                        linkNode.href = href;
                        document.head.appendChild(linkNode);
                    }
                });

                // Iniettiamo nuovo HTML
                mainContainer.innerHTML = newMain.innerHTML;
                await hydrateInjectedScripts(mainContainer);

                // Riesegui lo script specifico della pagina montata
                initCurrentPage();

                // Scrolla in cima asincronamente
                window.scrollTo({ top: 0, behavior: 'instant' });

                // Riesegue binding SPA per link appena iniettati
                setupSPALinks();

                // Ripristina logiche interne di JS sulle card etc.
                initAppFeatures();

                // Aggiorna l'icona attiva della nav (es nel caso si usi "Indietro")
                updateNavbarState(window.location.pathname);

                // Effetto FADE IN
                mainContainer.style.opacity = '1';

            } else {
                // Se manca id main-container dalla rispota, facciamo nav normale
                window.location.href = url;
            }

        } catch (error) {
            console.error('Error during SPA navigation. Fallback to normal navigation.', error);
            window.location.href = url;
        }
    };

    // Update the active state on the navbar primarily when using back/forward browser buttons
    function updateNavbarState(path) {
        document.querySelectorAll('.nav-icon-link').forEach(link => {
            link.classList.remove('active');
            let href = link.getAttribute('href');
            if (href) {
                // Regex rudimentale per match per lo state. es: /multe 
                if (href === path) {
                    link.classList.add('active');
                } else if (path.includes('partite') && href.includes('partite')) {
                    link.classList.add('active');
                } else if (path.includes('calendario') && href.includes('calendario')) {
                    link.classList.add('active');
                } else if (path.includes('rosa') && href.includes('rosa')) {
                    link.classList.add('active');
                } else if (href === '/' && path === '/') {
                    link.classList.add('active');
                }
            }
        });
    }

    // Gestione pulsanti Indietro/Avanti del browser o telefono
    window.addEventListener('popstate', (e) => {
        // e.state contains what we passed to pushState. Se null, è la prima entry
        const targetUrl = window.location.pathname + window.location.search;
        navigateTo(targetUrl, true);
    });

});
