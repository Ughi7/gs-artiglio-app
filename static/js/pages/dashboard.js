window.initDashboard = function (data) {
    const clearNotificationsBtn = document.getElementById('clearNotificationsBtn');
    if (clearNotificationsBtn && !clearNotificationsBtn.dataset.spaBound) {
        clearNotificationsBtn.dataset.spaBound = 'true';
        clearNotificationsBtn.addEventListener('click', function (event) {
            if (!window.confirm('Svuotare la bacheca?')) {
                event.preventDefault();
            }
        });
    }

    document.querySelectorAll('.remove-squadra-btn').forEach(button => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            const squadraName = button.dataset.squadraName || 'questa squadra';
            if (!window.confirm(`Rimuovere ${squadraName}?`)) return;

            const formId = button.dataset.formId;
            const form = formId ? document.getElementById(formId) : null;
            if (form) form.submit();
        });
    });

    if (!data) return;

    // Distruggi chart precedenti se stiamo ri-navigando sulla stessa pagina, eviterà glitch di Chart.js
    if (window.dashboardCharts) {
        window.dashboardCharts.forEach(c => c.destroy());
    }
    window.dashboardCharts = [];

    // Configurazione globale Chart.js
    Chart.defaults.color = '#adb5bd';
    Chart.defaults.borderColor = '#495057';

    // === GRAFICI MULTE ===

    // 1. Trend Multe Mensili (Linea)
    const multeMensiliCtx = document.getElementById('multeMensiliChart');
    if (multeMensiliCtx) {
        window.dashboardCharts.push(new Chart(multeMensiliCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.mesiMulte,
                datasets: [{
                    label: 'Numero Multe',
                    data: data.multeCountPerMese,
                    borderColor: '#FFC107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: true, position: 'top' } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        }));
    }

    // 2. Distribuzione Multe per Importo (Torta)
    const multeDistribuzioneCtx = document.getElementById('multeDistribuzioneChart');
    if (multeDistribuzioneCtx) {
        window.dashboardCharts.push(new Chart(multeDistribuzioneCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.multaRangesLabels,
                datasets: [{
                    data: data.multaRangesValues,
                    backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545'],
                    borderWidth: 2,
                    borderColor: '#212529'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom' } }
            }
        }));
    }

    // 3. Multe per Giocatore (Barre)
    const multeGiocatoreCtx = document.getElementById('multeGiocatoreChart');
    if (multeGiocatoreCtx && data.multePerGiocatore) {
        window.dashboardCharts.push(new Chart(multeGiocatoreCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.multePerGiocatore.labels,
                datasets: [{
                    label: 'Totale Multe (€)',
                    data: data.multePerGiocatore.data,
                    backgroundColor: '#dc3545',
                    borderColor: '#c82333',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true, indexAxis: 'y',
                plugins: { legend: { display: false } }, scale: { x: { beginAtZero: true } }
            }
        }));
    }

    // 4. Top 5 Denunciatori (Barre Orizzontali)
    const denunciatoriCtx = document.getElementById('denunciatoriChart');
    if (denunciatoriCtx && data.denunciatori) {
        window.dashboardCharts.push(new Chart(denunciatoriCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.denunciatori.labels,
                datasets: [{
                    label: 'Denunce Fatte',
                    data: data.denunciatori.data,
                    backgroundColor: '#fd7e14',
                    borderColor: '#e8590c',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true, indexAxis: 'y',
                plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        }));
    }

    // === GRAFICI PARTITE ===

    // 5. Andamento Vittorie/Sconfitte nel Tempo (Linea)
    const vittorieTempoCtx = document.getElementById('vittorieTempoChart');
    if (vittorieTempoCtx) {
        window.dashboardCharts.push(new Chart(vittorieTempoCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.datePartite,
                datasets: [{
                    label: 'Vittorie',
                    data: data.vittorieTempo,
                    borderColor: '#28a745', backgroundColor: 'rgba(40, 167, 69, 0.1)', borderWidth: 2, fill: true, tension: 0.4
                }, {
                    label: 'Sconfitte',
                    data: data.sconfitteTempo,
                    borderColor: '#dc3545', backgroundColor: 'rgba(220, 53, 69, 0.1)', borderWidth: 2, fill: true, tension: 0.4
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'top' } },
                scales: {
                    y: { beginAtZero: true, max: 1, ticks: { stepSize: 1 } }
                }
            }
        }));
    }

    // 6. Vittorie/Sconfitte Totali (Torta)
    const vittorieTotaliCtx = document.getElementById('vittorieTotaliChart');
    if (vittorieTotaliCtx) {
        window.dashboardCharts.push(new Chart(vittorieTotaliCtx.getContext('2d'), {
            type: 'pie',
            data: {
                labels: ['Vittorie', 'Sconfitte'],
                datasets: [{
                    data: [data.vittorieTotali, data.sconfitteTotali],
                    backgroundColor: ['#28a745', '#dc3545'], borderWidth: 2, borderColor: '#212529'
                }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
        }));
    }

    // 7. Set Vinti/Persi per Mese (Barre)
    const setMensiliCtx = document.getElementById('setMensiliChart');
    if (setMensiliCtx && data.mesiPartite) {
        window.dashboardCharts.push(new Chart(setMensiliCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.mesiPartite,
                datasets: [{
                    label: 'Set Vinti', data: data.setVintiPerMese, backgroundColor: '#28a745', borderColor: '#218838', borderWidth: 1
                }, {
                    label: 'Set Persi', data: data.setPersiPerMese, backgroundColor: '#dc3545', borderColor: '#c82333', borderWidth: 1
                }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
        }));
    }
};
