// --- GAME UI MODULE ---
window.initGameUI = function(isAdminValue) {
    if (window._gameUIInitialized) {
        return;
    }
    window._gameUIInitialized = true;
    
// --- Script 1 (Leaderboard/UI) ---

            function showTab(tab) {
                document.getElementById('tab-generale').style.display = (tab === 'generale') ? '' : 'none';
                document.getElementById('tab-mensile').style.display = (tab === 'mensile') ? '' : 'none';
                document.getElementById('month-filter').style.display = (tab === 'mensile') ? '' : 'none';
                document.getElementById('tabGenerale').classList.toggle('active', tab === 'generale');
                document.getElementById('tabMensile').classList.toggle('active', tab === 'mensile');

                // Rimuovi classe active dall'altro
                if (tab === 'generale') {
                    document.getElementById('tabGenerale').classList.add('btn-warning', 'active');
                    document.getElementById('tabGenerale').classList.remove('btn-outline-secondary');
                    document.getElementById('tabMensile').classList.remove('btn-warning', 'active');
                    document.getElementById('tabMensile').classList.add('btn-outline-secondary');
                } else {
                    document.getElementById('tabMensile').classList.add('btn-warning', 'active');
                    document.getElementById('tabMensile').classList.remove('btn-outline-secondary');
                    document.getElementById('tabGenerale').classList.remove('btn-warning', 'active');
                    document.getElementById('tabGenerale').classList.add('btn-outline-secondary');
                }
            }

            // Funzioni globali per i pulsanti onclick
            function showLeaderboard() {
                const leaderboardScreen = document.getElementById('leaderboard-screen');
                if (leaderboardScreen) {
                    leaderboardScreen.classList.remove('hidden');
                    leaderboardScreen.scrollTop = 0;
                }
            }

            function hideLeaderboard() {
                const leaderboardScreen = document.getElementById('leaderboard-screen');
                if (leaderboardScreen) leaderboardScreen.classList.add('hidden');
            }

            // Funzione per avviare il gioco (wrapper)
            window.avviaGioco = function() {
                if (window.gameAllowed && typeof window.startGameEngine === 'function') {
                    window.startGameEngine();
                }
            };

            // Funzione per riavviare il gioco (wrapper)
            window.riavviaGioco = function() {
                if (window.gameAllowed && typeof window.resetGameEngine === 'function') {
                    window.resetGameEngine();
                }
            };

            // Funzione condivisione WhatsApp
            function shareOnWhatsApp() {
                const score = document.getElementById('final-score').innerText;
                const text = `🦅 Ho fatto ${score} punti a Floppy Eagle (GS Artiglio)! Riesci a battermi?`;
                const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
                window.open(url, '_blank');
            }

            function updateMonthlyLeaderboard(month) {
                const container = document.querySelector('#tab-mensile .leaderboard-list');
                container.innerHTML = '<li class="leaderboard-item" style="justify-content: center;">Caricamento...</li>';

                fetch(`/api/game/leaderboard/monthly?month=${month}`)
                    .then(r => r.json())
                    .then(data => {
                        container.innerHTML = '';
                        if (data.results && data.results.length > 0) {
                            data.results.forEach((item, index) => {
                                const li = document.createElement('li');
                                li.className = 'leaderboard-item';
                                li.innerHTML = `
                                    <span class="rank-num">${index + 1}.</span>
                                    <span class="player-name">${item.name}</span>
                                    <span class="player-score">${item.score}</span>
                                `;
                                container.appendChild(li);
                            });
                        } else {
                            container.innerHTML = '<li class="leaderboard-item" style="justify-content: center;">Nessun punteggio registrato questo mese</li>';
                        }
                    })
                    .catch(e => {
                        console.error('Errore caricamento classifica:', e);
                        container.innerHTML = '<li class="leaderboard-item" style="justify-content: center; color: red;">Errore caricamento</li>';
                    });
            }
        



// --- BRIDGE CALLBACKS DA game.js ---
window.onGameScoreUpdate = function(score, level) {
    const currentScoreEl = document.getElementById('current-score');
    if (currentScoreEl) {
        currentScoreEl.innerText = score;
        currentScoreEl.style.transform = 'translate(-50%, 0) scale(1.2)';
        currentScoreEl.style.color = '#FFA500';
        setTimeout(() => {
            if (currentScoreEl) {
                currentScoreEl.style.transform = 'translate(-50%, 0) scale(1)';
                currentScoreEl.style.color = 'white';
            }
        }, 150);
    }
};

window.onGameDeath = function(score, bestScore, coins) {
    const startScreen = document.getElementById('start-screen');
    const gameOverScreen = document.getElementById('game-over-screen');
    const finalScoreEl = document.getElementById('final-score');

    if (startScreen) startScreen.classList.add('hidden');
    if (gameOverScreen) gameOverScreen.classList.remove('hidden');
    if (finalScoreEl) finalScoreEl.innerText = score;

    if (navigator.vibrate) navigator.vibrate([200, 100, 200]);

    if (typeof checkAndSyncHighscore === 'function') {
        checkAndSyncHighscore(score, bestScore);
    }
};

window.onNewHighScoreAchieved = function(score) {
    console.log('Nuovo record raggiunto: ' + score);
};

// --- ESPORTA FUNZIONI UI PER ONCLICK ---
window.showTab = showTab;
window.updateMonthlyLeaderboard = updateMonthlyLeaderboard;

};
