(function () {
    // Controlla se l'utente ha una preferenza salvata manualmente
    const savedTheme = localStorage.getItem('artiglio-theme');
    const isManuallySet = savedTheme !== null;

    // Se non c'è preferenza salvata, usa SEMPRE dark (non seguire tema dispositivo)
    let activeTheme;
    if (isManuallySet) {
        activeTheme = savedTheme;
        document.body.setAttribute('data-theme-manual', 'true');
    } else {
        activeTheme = 'dark';
    }

    document.documentElement.setAttribute('data-bs-theme', activeTheme);
    document.body.setAttribute('data-theme', activeTheme);
    document.body.setAttribute('data-bs-theme', activeTheme);

    // Aggiorna checkbox
    document.addEventListener('DOMContentLoaded', function () {
        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.checked = activeTheme === 'light';

            // Aggiorna icona nel toggle
            const thumb = toggle.parentElement.querySelector('.toggle-thumb');
            if (thumb) {
                thumb.textContent = activeTheme === 'light' ? '☀️' : '🌙';
            }

            toggle.addEventListener('change', function () {
                const newTheme = this.checked ? 'light' : 'dark';
                document.documentElement.setAttribute('data-bs-theme', newTheme);
                document.body.setAttribute('data-theme', newTheme);
                document.body.setAttribute('data-bs-theme', newTheme);
                document.body.setAttribute('data-theme-manual', 'true');
                localStorage.setItem('artiglio-theme', newTheme);

                // Aggiorna icona
                if (thumb) {
                    thumb.textContent = newTheme === 'light' ? '☀️' : '🌙';
                }

                console.log('[TEMA] Cambiato a:', newTheme, '(manuale)');
            });
        }
    });
})();
