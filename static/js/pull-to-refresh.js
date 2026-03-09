window.initPullToRefresh = function () {
    // Solo su mobile
    if (!/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        return;
    }

    const ptr = document.getElementById('ptr-indicator');
    if (!ptr) return;

    let startY = 0;
    let isPulling = false;
    const threshold = 80;

    document.addEventListener('touchstart', (e) => {
        // Solo se siamo in cima alla pagina e NON c'è un modal aperto
        if (window.scrollY === 0 && !document.body.classList.contains('modal-open')) {
            startY = e.touches[0].clientY;
            isPulling = true;
        }
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
        if (!isPulling) return;

        const currentY = e.touches[0].clientY;
        const diff = currentY - startY;

        // Mostra indicatore se tiriamo abbastanza
        if (diff > threshold / 2 && window.scrollY === 0) {
            ptr.classList.add('visible');
        }
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        if (!isPulling) return;
        isPulling = false;

        const wasVisible = ptr.classList.contains('visible');

        if (wasVisible) {
            // Refresh la pagina
            setTimeout(() => {
                window.location.reload();
            }, 300);
        }
    }, { passive: true });
};
