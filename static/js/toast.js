(function () {
    window.showToast = function (message, type = 'default', duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const icons = {
            'success': '✨',
            'error': '❌',
            'info': 'ℹ️',
            'warning': '⚠️'
        };

        const toast = document.createElement('div');
        toast.className = `toast-item ${type}`;
        toast.innerHTML = `
                    <div class="toast-icon">${icons[type] || '🦅'}</div>
                    <div class="toast-message">${message}</div>
                `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastExit 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    };

    // Override flash messages
    window.initToast = function () {
        // Cerca i flash se iniettati nel #main-container o dove risiedono
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(alert => {
            const type = alert.classList.contains('alert-success') ? 'success' :
                alert.classList.contains('alert-danger') ? 'error' : 'info';

            // Ritarda un attimo per dare priorità ad altre pipeline di rendering
            setTimeout(() => {
                showToast(alert.textContent.replace('×', '').trim(), type);
                alert.remove();
            }, 100);
        });
    };
})();
