window.initStatsPartite = function (data) {
    data = data || window.__statsPartiteData;
    if (!data) return;

    // Configurazione globale Chart.js
    Chart.defaults.color = '#adb5bd';
    Chart.defaults.font.family = "'Roboto', sans-serif";
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';

    // Distruggi vecchi chart per evitare "canvas is already in use" bug su React/SPA
    if (window.statsPartiteCharts) {
        window.statsPartiteCharts.forEach(chart => chart.destroy());
    }
    window.statsPartiteCharts = [];

    // Funzione helper per creare gradienti
    function createGradient(ctx, color) {
        if (!ctx) return null;
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, color.replace('1)', '0.4)'));
        gradient.addColorStop(1, color.replace('1)', '0)'));
        return gradient;
    }

    // 1. Andamento Vittorie/Sconfitte nel Tempo (Linea Cumulativa)
    const vittorieTempoEl = document.getElementById('vittorieTempoChart');
    if (vittorieTempoEl) {
        const vittorieTempoCtx = vittorieTempoEl.getContext('2d');
        const cyanGradient = createGradient(vittorieTempoCtx, 'rgba(23, 162, 184, 1)');

        const vittorie = data.vittorieTempo;
        const sconfitte = data.sconfitteTempo;
        const bilancioCumulativo = [];
        let bilancio = 0;

        for (let i = 0; i < vittorie.length; i++) {
            if (vittorie[i] === 1) {
                bilancio++;
            } else {
                bilancio--;
            }
            bilancioCumulativo.push(bilancio);
        }

        const chart1 = new Chart(vittorieTempoCtx, {
            type: 'line',
            data: {
                labels: data.datePartite,
                datasets: [{
                    label: 'Bilancio Vittorie/Sconfitte',
                    data: bilancioCumulativo,
                    borderColor: '#17a2b8',
                    backgroundColor: cyanGradient,
                    borderWidth: 4,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointBackgroundColor: '#17a2b8',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointHoverRadius: 8,
                    pointHoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        padding: 12,
                        titleFont: { size: 14, weight: 'bold' },
                        bodyFont: { size: 13 },
                        displayColors: false,
                        callbacks: {
                            label: function (context) {
                                return 'Bilancio: ' + (context.parsed.y > 0 ? '+' : '') + context.parsed.y;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        grid: { drawBorder: false },
                        ticks: {
                            stepSize: 1,
                            callback: value => (value > 0 ? '+' : '') + value
                        }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
        window.statsPartiteCharts.push(chart1);
    }

    // 2. Vittorie/Sconfitte Totali (Doughnut)
    const vittorieTotaliEl = document.getElementById('vittorieTotaliChart');
    if (vittorieTotaliEl) {
        const vittorieTotaliCtx = vittorieTotaliEl.getContext('2d');
        const chart2 = new Chart(vittorieTotaliCtx, {
            type: 'doughnut',
            data: {
                labels: ['Vittorie', 'Sconfitte'],
                datasets: [{
                    data: [data.vittorieTotali, data.sconfitteTotali],
                    backgroundColor: ['#28a745', '#dc3545'],
                    hoverOffset: 15,
                    borderWidth: 0,
                    borderRadius: 10,
                    spacing: 5
                }]
            },
            options: {
                cutout: '75%',
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
                }
            }
        });
        window.statsPartiteCharts.push(chart2);
    }

    // 3. Set Vinti/Persi per Mese (Barre Soft)
    const setMensiliEl = document.getElementById('setMensiliChart');
    if (setMensiliEl) {
        const setMensiliCtx = setMensiliEl.getContext('2d');
        const chart3 = new Chart(setMensiliCtx, {
            type: 'bar',
            data: {
                labels: data.mesiPartite,
                datasets: [{
                    label: 'Set Vinti',
                    data: data.setVintiPerMese,
                    backgroundColor: '#28a745',
                    borderRadius: 8,
                    borderSkipped: false
                }, {
                    label: 'Set Persi',
                    data: data.setPersiPerMese,
                    backgroundColor: '#dc3545',
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true } }
                },
                scales: {
                    y: { beginAtZero: true, grid: { drawBorder: false } },
                    x: { grid: { display: false } }
                }
            }
        });
        window.statsPartiteCharts.push(chart3);
    }
};

window.initStatsMulte = function (data) {
    data = data || window.__statsMulteData;
    if (!data) return;

    // Configurazione globale Chart.js
    Chart.defaults.color = '#adb5bd';
    Chart.defaults.borderColor = '#495057';

    // Distruzione vecchi rendering
    if (window.statsMulteCharts) {
        window.statsMulteCharts.forEach(c => c.destroy());
    }
    window.statsMulteCharts = [];

    // 1. Trend Multe Mensili (Linea)
    const multeMensiliEl = document.getElementById('multeMensiliChart');
    if (multeMensiliEl) {
        const multeMensiliCtx = multeMensiliEl.getContext('2d');
        const c1 = new Chart(multeMensiliCtx, {
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
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
        window.statsMulteCharts.push(c1);
    }

    // 2. Multe per Giocatore (Barre)
    const multeGiocatoreEl = document.getElementById('multeGiocatoreChart');
    if (multeGiocatoreEl) {
        const multeGiocatoreCtx = multeGiocatoreEl.getContext('2d');
        const c2 = new Chart(multeGiocatoreCtx, {
            type: 'bar',
            data: {
                labels: (data.giocatoriNomi || []).map((name, index) => name || (data.giocatoriFallbackNomi || [])[index] || 'Sconosciuto'),
                datasets: [{
                    label: 'Totale Multe (€)',
                    data: data.giocatoriImporti,
                    backgroundColor: '#dc3545',
                    borderColor: '#c82333',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
        window.statsMulteCharts.push(c2);
    }

    // 3. Top 5 Denunciatori (Barre Orizzontali)
    const denunciatoriEl = document.getElementById('denunciatoriChart');
    if (denunciatoriEl) {
        const denunciatoriCtx = denunciatoriEl.getContext('2d');
        const c3 = new Chart(denunciatoriCtx, {
            type: 'bar',
            data: {
                labels: (data.denunciatoriNomi || []).map((name, index) => name || (data.denunciatoriFallbackNomi || [])[index] || 'Sconosciuto'),
                datasets: [{
                    label: 'Denunce Fatte',
                    data: data.denunciatoriConteggi,
                    backgroundColor: '#fd7e14',
                    borderColor: '#e8590c',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
        window.statsMulteCharts.push(c3);
    }
};
