// --- GAME ENGINE MODULE ---
window.initGameEngine = function(isAdminValue) {
    if (window._gameEngineInitialized) {
        if (window._updateGameDomRefs) window._updateGameDomRefs(isAdminValue);
        return;
    }
    window._gameEngineInitialized = true;
    let isAdmin = isAdminValue;


        // Variabili globali del gioco - esposte a window per onclick inline
        var isPlaying = false;
        var isGameOver = false;
        var gameAllowed = false;
        var scaleTimeStop = false;
        var lastDeathTime = 0;
        var vibrationEnabled = true;

        // Load vibration setting
        try {
            const savedVib = localStorage.getItem('artiglio_vibration');
            if (savedVib !== null) {
                vibrationEnabled = savedVib === 'true';
            }
        } catch (e) { }

        function getCsrfToken() {
            const el = document.querySelector('meta[name="csrf-token"]');
            return el ? el.getAttribute('content') : '';
        }

        function toggleVibration() {
            vibrationEnabled = !vibrationEnabled;
            localStorage.setItem('artiglio_vibration', vibrationEnabled);
            updateVibrationUi();
            if (vibrationEnabled && navigator.vibrate) navigator.vibrate(50);
        }

        function updateVibrationUi() {
            const btn = document.getElementById('vib-toggle-btn');
            if (btn) {
                if (vibrationEnabled) {
                    btn.innerHTML = '📳';
                    btn.style.opacity = '1';
                    btn.classList.add('btn-outline');
                    btn.classList.remove('btn-outline-secondary');
                } else {
                    btn.innerHTML = '📴';
                    btn.style.opacity = '0.5';
                    btn.classList.remove('btn-outline');
                    btn.classList.add('btn-outline-secondary');
                }
            }
        }

        function triggerVibration(pattern) {
            if (vibrationEnabled && navigator.vibrate) {
                try { navigator.vibrate(pattern); } catch (e) { }
            }
        }

        // === CONTROLLO REQUISITI: PWA + MOBILE + PORTRAIT ===
        let requirementsScreen = document.getElementById('requirements-screen');

        // UI refs dichiarati prima
        let canvas = document.getElementById('gameCanvas');
        let ctx = canvas.getContext('2d', {
            alpha: true,
            colorSpace: 'srgb',
            willReadFrequently: false
        });
        let startScreen = document.getElementById('start-screen');
        let gameOverScreen = document.getElementById('game-over-screen');
        let leaderboardScreen = document.getElementById('leaderboard-screen');
        let currentScoreEl = document.getElementById('current-score');
        let finalScoreEl = document.getElementById('final-score');
        let bestScoreEl = document.getElementById('best-score');

        // ====== DOM EMOJI LAYER (iOS fix) ======
        let emojiLayer = document.getElementById('emoji-layer');
        let isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        let USE_DOM_EMOJI = isIOS;

        
    window._updateGameDomRefs = function(adminVal) {
        isAdmin = adminVal;
        requirementsScreen = document.getElementById('requirements-screen');
        canvas = document.getElementById('gameCanvas');
        if (!canvas) return;
        ctx = canvas.getContext('2d', { alpha: true, colorSpace: 'srgb', willReadFrequently: false });
        startScreen = document.getElementById('start-screen');
        gameOverScreen = document.getElementById('game-over-screen');
        leaderboardScreen = document.getElementById('leaderboard-screen');
        currentScoreEl = document.getElementById('current-score');
        finalScoreEl = document.getElementById('final-score');
        bestScoreEl = document.getElementById('best-score');
        emojiLayer = document.getElementById('emoji-layer');
        if (typeof resizeCanvas === 'function') resizeCanvas();
        if (typeof checkRequirements === 'function') checkRequirements();
        if (typeof updateVibrationUi === 'function') updateVibrationUi();
        
                // EXPORTS AUTOMATICI - esponi tutte le funzioni per onclick HTML
        window.activatePowerup = activatePowerup;
        window.bindUi = bindUi;
        window.buyShopItem = buyShopItem;
        window.checkRequirements = checkRequirements;
        window.clampNumber = clampNumber;
        window.cleanOldMissionKeys = cleanOldMissionKeys;
        window.creaNotificaGioco = creaNotificaGioco;
        window.difficultyAtLevel = difficultyAtLevel;
        window.drawPipe = drawPipe;
        window.drawPipeCap = drawPipeCap;
        window.drawPipeSegment = drawPipeSegment;
        window.endGame = endGame;
        window.equipPreviewedSkin = equipPreviewedSkin;
        window.findSafeSpawnPosition = findSafeSpawnPosition;
        window.getPipeColorsForLevel = getPipeColorsForLevel;
        window.getPipeVariation = getPipeVariation;
        window.hideInfoScreen = hideInfoScreen;
        window.hideLeaderboard = hideLeaderboard;
        window.hideShopScreen = hideShopScreen;
        window.hideSkinsScreen = hideSkinsScreen;
        window.initAudio = initAudio;
        window.initDailyMissions = initDailyMissions;
        window.initParallax = initParallax;
        window.isItemCollidingWithAnyPipe = isItemCollidingWithAnyPipe;
        window.isItemCollidingWithPipe = isItemCollidingWithPipe;
        window.isStartScreenVisible = isStartScreenVisible;
        window.isUiInteractiveTarget = isUiInteractiveTarget;
        window.jump = jump;
        window.playTone = playTone;
        window.resetGameEngine = resetGame;
        window.resizeCanvas = resizeCanvas;
        window.roundRectPath = roundRectPath;
        window.sfxCoinCollect = sfxCoinCollect;
        window.sfxCollision = sfxCollision;
        window.sfxCombo = sfxCombo;
        window.sfxJump = sfxJump;
        window.sfxLevelUp = sfxLevelUp;
        window.sfxNegative = sfxNegative;
        window.sfxPositive = sfxPositive;
        window.sfxPowerup = sfxPowerup;
        window.showInfoScreen = showInfoScreen;
        window.showInfoTab = showInfoTab;
        window.showLeaderboard = showLeaderboard;
        window.showShopScreen = showShopScreen;
        window.showSkinUnlock = showSkinUnlock;
        window.showSkinsScreen = showSkinsScreen;
        window.showStartScreen = showStartScreen;
        window.showToast = showToast;
        window.spawnDecoration = spawnDecoration;
        window.spawnItem = spawnItem;
        window.spawnPipe = spawnPipe;
        window.startBackgroundMusic = startBackgroundMusic;
        window.startGameEngine = startGame;
        window.stopBackgroundMusic = stopBackgroundMusic;
        window.syncProfile = syncProfile;
        window.toggleMute = toggleMute;
        window.toggleVibration = toggleVibration;
        window.triggerShake = triggerShake;
        window.triggerVibration = triggerVibration;
        window.updateHudCoins = updateHudCoins;
        window.updateMissions = updateMissions;
        window.updateMissionsUi = updateMissionsUi;
        window.updateMusicIntensity = updateMusicIntensity;
        window.updateRankChanges = updateRankChanges;
        window.updateScoreDisplay = updateScoreDisplay;
        window.updateShake = updateShake;
        window.updateShopCoinsDisplay = updateShopCoinsDisplay;
        window.updateShopItems = updateShopItems;
        window.updateSkinPreview = updateSkinPreview;
        window.updateSkinSelector = updateSkinSelector;
        window.updateStartScreenSkin = updateStartScreenSkin;
        window.updateVibrationUi = updateVibrationUi;
    };

        const domEmoji = {
            birdEl: null,
            itemEls: new Map(),
            decoEls: new Map()
        };

        function ensureEmojiEl(map, id) {
            let el = map.get(id);
            if (!el) {
                el = document.createElement('span');
                el.className = 'emoji-sprite';
                emojiLayer.appendChild(el);
                map.set(id, el);
            }
            return el;
        }

        function cleanupEmojiMap(map, keepIds) {
            for (const [id, el] of map.entries()) {
                if (!keepIds.has(id)) {
                    try { el.remove(); } catch (_) { }
                    map.delete(id);
                }
            }
        }

        function clearEmojiLayer() {
            if (!emojiLayer) return;
            emojiLayer.innerHTML = '';
            domEmoji.birdEl = null;
            domEmoji.itemEls.clear();
            domEmoji.decoEls.clear();
        }

        // Nuova funzione: pulisce items e decorazioni ma mantiene il bird visibile (per game over)
        function clearEmojiLayerKeepBird() {
            if (!emojiLayer) return;
            // Rimuovi solo items e decorazioni, mantieni il bird
            for (const [id, el] of domEmoji.itemEls.entries()) {
                try { el.remove(); } catch (_) { }
            }
            domEmoji.itemEls.clear();
            for (const [id, el] of domEmoji.decoEls.entries()) {
                try { el.remove(); } catch (_) { }
            }
            domEmoji.decoEls.clear();
            // NON rimuovere il birdEl - rimane visibile
        }

        function updateDomEmojiLayer(shakeX, shakeY) {
            if (!USE_DOM_EMOJI || !emojiLayer) return;

            // Nascondi/mostra il layer in base allo stato del gioco
            const shouldShowLayer = isPlaying;
            emojiLayer.style.display = shouldShowLayer ? 'block' : 'none';
            if (!isPlaying) return;

            const rect = canvas.getBoundingClientRect();
            const scaleX = rect.width / logicalWidth;
            const scaleY = rect.height / logicalHeight;
            const scale = (scaleX + scaleY) / 2;

            // Le decorazioni vengono ora disegnate direttamente sul canvas per stare dietro i tubi

            // Items (pizza/birra/powerups/hazard)
            const keepItems = new Set();
            for (const b of items) {
                if (!b || b.collected || b.id == null) continue;
                keepItems.add(b.id);
                const el = ensureEmojiEl(domEmoji.itemEls, b.id);
                el.textContent = b.icon;
                el.style.opacity = '1';
                el.style.fontSize = `${(32 * scale).toFixed(2)}px`;
                el.style.left = `${rect.left + (b.x + (shakeX || 0)) * scaleX}px`;
                el.style.top = `${rect.top + (b.y + (shakeY || 0)) * scaleY}px`;
                el.style.transform = 'translate(-50%, -50%)';
            }
            cleanupEmojiMap(domEmoji.itemEls, keepItems);

            // Bird (con mirror e rotazione)
            if (!domEmoji.birdEl) {
                domEmoji.birdEl = document.createElement('span');
                domEmoji.birdEl.className = 'emoji-sprite';
                emojiLayer.appendChild(domEmoji.birdEl);
            }
            domEmoji.birdEl.textContent = (typeof SKINS === 'object' && SKINS[selectedSkin]) ? SKINS[selectedSkin] : EAGLE_ICON;
            const ghostOpacity = (activePowerups && activePowerups.ghost && activePowerups.ghost.active) ? '0.7' : '1';
            domEmoji.birdEl.style.opacity = ghostOpacity;

            // Apply tiny mode scaling for Safari/iOS
            const tinyScale = (activePowerups && activePowerups.tiny && activePowerups.tiny.active) ? 0.5 : 1.0;
            domEmoji.birdEl.style.fontSize = `${(42 * scale * tinyScale).toFixed(2)}px`;
            domEmoji.birdEl.style.left = `${rect.left + (bird.x + (shakeX || 0)) * scaleX}px`;
            domEmoji.birdEl.style.top = `${rect.top + (bird.y + (shakeY || 0)) * scaleY}px`;
            domEmoji.birdEl.style.transform = `translate(-50%, -50%) rotate(${bird.rotation || 0}rad) scaleX(-1)`;
        }

        function checkRequirements() {
            // Admin bypassa tutti i requisiti
            if (isAdmin) {
                gameAllowed = true;
                window.gameAllowed = true; // Esponi a window
                if (requirementsScreen) requirementsScreen.classList.add('hidden');
                if (startScreen && !isPlaying && !isGameOver) startScreen.classList.remove('hidden');
                return true;
            }

            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            const isPWA = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
            const isPortrait = window.innerHeight > window.innerWidth;

            // Aggiorna UI requisiti
            const reqMobile = document.getElementById('req-mobile');
            const reqPWA = document.getElementById('req-pwa');
            const reqPortrait = document.getElementById('req-portrait');

            if (reqMobile) {
                reqMobile.className = isMobile ? 'requirement met' : 'requirement not-met';
                reqMobile.innerHTML = isMobile ?
                    '<div style="font-size: 24px; margin-bottom: 5px;">✅</div><div><strong>Dispositivo Mobile</strong></div><div style="font-size: 14px; color: #4CAF50;">Requisito soddisfatto</div>' :
                    '<div style="font-size: 24px; margin-bottom: 5px;">📱</div><div><strong>Dispositivo Mobile</strong></div><div style="font-size: 14px; color: #f44336;">Usa uno smartphone</div>';
            }

            if (reqPWA) {
                reqPWA.className = isPWA ? 'requirement met' : 'requirement not-met';
                reqPWA.innerHTML = isPWA ?
                    '<div style="font-size: 24px; margin-bottom: 5px;">✅</div><div><strong>App Installata</strong></div><div style="font-size: 14px; color: #4CAF50;">PWA attiva</div>' :
                    '<div style="font-size: 24px; margin-bottom: 5px;">📲</div><div><strong>App Installata</strong></div><div style="font-size: 14px; color: #f44336;">Installa l\'app dalla home</div>';
            }

            if (reqPortrait) {
                reqPortrait.className = isPortrait ? 'requirement met' : 'requirement not-met';
                reqPortrait.innerHTML = isPortrait ?
                    '<div style="font-size: 24px; margin-bottom: 5px;">✅</div><div><strong>Orientamento Verticale</strong></div><div style="font-size: 14px; color: #4CAF50;">Orientamento corretto</div>' :
                    '<div style="font-size: 24px; margin-bottom: 5px;">🔄</div><div><strong>Orientamento Verticale</strong></div><div style="font-size: 14px; color: #f44336;">Ruota il dispositivo</div>';
            }

            // Determina se il gioco è permesso
            gameAllowed = isMobile && isPWA && isPortrait;
            window.gameAllowed = gameAllowed;

            // Mostra/nascondi schermate appropriate
            if (gameAllowed) {
                if (requirementsScreen) requirementsScreen.classList.add('hidden');
                if (startScreen && !isPlaying && !isGameOver) startScreen.classList.remove('hidden');
            } else {
                if (requirementsScreen) requirementsScreen.classList.remove('hidden');
                if (startScreen) startScreen.classList.add('hidden');
                if (gameOverScreen) gameOverScreen.classList.add('hidden');
                // Interrompi il gioco se in corso
                if (isPlaying) {
                    isPlaying = false;
                    isGameOver = true;
                }
            }

            return gameAllowed;
        }

        // Controlla requisiti all'avvio
        // NON chiamiamo checkRequirements() qui perché showStartScreen() deve essere chiamato prima

        // Monitora cambio orientamento
        window.addEventListener('resize', checkRequirements);
        window.addEventListener('orientationchange', checkRequirements);

        // === FINE CONTROLLO REQUISITI ===

        function showStartScreen() {
            // Controlla requisiti ogni volta che mostriamo la schermata start
            checkRequirements();

            if (!gameAllowed) {
                // Se requisiti non soddisfatti, mostra schermata requisiti
                if (requirementsScreen) requirementsScreen.classList.remove('hidden');
                if (startScreen) startScreen.classList.add('hidden');
                if (gameOverScreen) gameOverScreen.classList.add('hidden');
                if (leaderboardScreen) leaderboardScreen.classList.add('hidden');
            } else {
                // Se requisiti OK, mostra schermata start
                if (startScreen) startScreen.classList.remove('hidden');
                if (gameOverScreen) gameOverScreen.classList.add('hidden');
                if (leaderboardScreen) leaderboardScreen.classList.add('hidden');
                if (requirementsScreen) requirementsScreen.classList.add('hidden');
            }
        }

        function isStartScreenVisible() {
            return startScreen && !startScreen.classList.contains('hidden');
        }

        showStartScreen();

        // --- AUDIO SYSTEM ---
        const audio = { ctx: null, masterGain: null, muted: false };

        // Dynamic Music System
        let musicOscillators = [];
        let musicGain = null;
        let bassGain = null;
        let melodyGain = null;
        let currentMusicLevel = 0;

        function initAudio() {
            if (audio.ctx) return;
            try {
                audio.ctx = new (window.AudioContext || window.webkitAudioContext)();
                audio.masterGain = audio.ctx.createGain();
                audio.masterGain.connect(audio.ctx.destination);
                audio.masterGain.gain.value = audio.muted ? 0 : 0.3;

                // Initialize music gains
                musicGain = audio.ctx.createGain();
                musicGain.gain.value = 0;
                musicGain.connect(audio.masterGain);

                bassGain = audio.ctx.createGain();
                bassGain.gain.value = 0;
                bassGain.connect(musicGain);

                melodyGain = audio.ctx.createGain();
                melodyGain.gain.value = 0;
                melodyGain.connect(musicGain);
            } catch (e) {
                console.warn('Audio not supported', e);
            }
        }

        function toggleMute() {
            audio.muted = !audio.muted;
            if (audio.masterGain) {
                audio.masterGain.gain.value = audio.muted ? 0 : 0.3;
            }
            const muteBtn = document.getElementById('mute-btn');
            if (muteBtn) muteBtn.innerText = audio.muted ? '🔇' : '🔊';
        }

        function playTone(freq, duration, type = 'sine', vol = 1.0, detune = 0) {
            if (!audio.ctx || audio.muted) return;
            try {
                const osc = audio.ctx.createOscillator();
                const gain = audio.ctx.createGain();
                osc.type = type;
                osc.frequency.value = freq;
                osc.detune.value = detune;
                gain.gain.value = vol * 0.15;
                osc.connect(gain);
                gain.connect(audio.masterGain);
                osc.start();
                gain.gain.exponentialRampToValueAtTime(0.001, audio.ctx.currentTime + duration);
                osc.stop(audio.ctx.currentTime + duration);
            } catch (_) { }
        }

        // Start dynamic background music
        function startBackgroundMusic() {
            if (!audio.ctx || audio.muted) return;
            stopBackgroundMusic(); // Clear any existing

            try {
                // Bass line (low frequency pulse)
                const bass = audio.ctx.createOscillator();
                bass.type = 'sine';
                bass.frequency.value = 55; // Low A
                bassGain.gain.value = 0.15;
                bass.connect(bassGain);
                bass.start();
                musicOscillators.push(bass);

                // Ambient pad
                const pad = audio.ctx.createOscillator();
                pad.type = 'triangle';
                pad.frequency.value = 220;
                const padGain = audio.ctx.createGain();
                padGain.gain.value = 0.08;
                pad.connect(padGain);
                padGain.connect(musicGain);
                pad.start();
                musicOscillators.push(pad);

                // Fade in music
                musicGain.gain.setValueAtTime(0, audio.ctx.currentTime);
                musicGain.gain.linearRampToValueAtTime(0.4, audio.ctx.currentTime + 2);

            } catch (e) {
                console.warn("Music error:", e);
            }
        }

        function stopBackgroundMusic() {
            if (musicGain && audio.ctx) {
                musicGain.gain.linearRampToValueAtTime(0, audio.ctx.currentTime + 0.5);
            }

            musicOscillators.forEach(osc => {
                try {
                    osc.stop(audio.ctx.currentTime + 0.5);
                } catch (e) { }
            });
            musicOscillators = [];
        }

        function updateMusicIntensity(level, speed) {
            if (!audio.ctx || !bassGain || !melodyGain || audio.muted) return;

            try {
                // Increase bass presence with level
                const bassIntensity = Math.min(0.2 + (level * 0.02), 0.4);
                bassGain.gain.linearRampToValueAtTime(bassIntensity, audio.ctx.currentTime + 0.5);

                // Add melody layers at higher levels
                if (level >= 3 && melodyGain.gain.value < 0.1) {
                    const melody = audio.ctx.createOscillator();
                    melody.type = 'square';
                    melody.frequency.value = 440 + (level * 20);
                    melodyGain.gain.value = 0.12;
                    melody.connect(melodyGain);
                    melody.start();
                    musicOscillators.push(melody);
                }

                // Pitch shifts with speed
                musicOscillators.forEach((osc, i) => {
                    if (i === 0) { // Bass
                        osc.frequency.linearRampToValueAtTime(
                            55 + (speed * 5),
                            audio.ctx.currentTime + 0.3
                        );
                    }
                });

            } catch (e) { }
        }

        // --- NEW CLASSES & SYSTEMS ---

        class Particle {
            constructor(x, y, color, speed, size, life) {
                this.x = x;
                this.y = y;
                this.color = color;
                this.vx = (Math.random() - 0.5) * speed;
                this.vy = (Math.random() - 0.5) * speed;
                this.size = size;
                this.life = life;
                this.maxLife = life;
            }
            update(dt) {
                this.x += this.vx * dt;
                this.y += this.vy * dt;
                this.life -= dt;
                this.size *= 0.95; // Shrink
            }
            draw(ctx) {
                ctx.globalAlpha = Math.max(0, this.life / this.maxLife);
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.globalAlpha = 1.0;
            }
        }

        // Sistema Particelle
        const particleSystem = {
            particles: [],
            maxParticles: 50,  // Performance limit (reduced)
            emit: function (x, y, color, count, speed = 5, size = 3) {
                // Limit particles for performance
                const actualCount = Math.max(0, Math.min(count, this.maxParticles - this.particles.length));
                for (let i = 0; i < actualCount; i++) {
                    this.particles.push(new Particle(x, y, color, speed, size, 1.0)); // 1 sec life
                }
            },
            update: function (dt) {
                for (let i = this.particles.length - 1; i >= 0; i--) {
                    const p = this.particles[i];
                    p.update(dt);
                    if (p.life <= 0) this.particles.splice(i, 1);
                }
            },
            draw: function (ctx) {
                this.particles.forEach(p => p.draw(ctx));
            }
        };

        // Screen Shake
        let shakeTimer = 0;
        let shakeIntensity = 0;

        function triggerShake(duration, intensity) {
            shakeTimer = duration;
            shakeIntensity = intensity;
        }

        function updateShake(dt) {
            if (shakeTimer > 0) {
                shakeTimer -= dt;
                // Shake offset applied in draw() separately or via ctx save/restore wrapper
            }
        }

        // --- POWER UPS & GAME STATE EXTENSIONS ---
        // --- DAILY MISSIONS ---
        const MISSIONS_POOL = [
            { id: 'collect_50_pizza', desc: 'Raccogli 50 Pizze', target: 50, type: 'collect', item: 'pizza' },
            { id: 'collect_50_beer', desc: 'Raccogli 50 Birre', target: 50, type: 'collect', item: 'beer' },
            { id: 'score_2500', desc: 'Punteggio 2500 in una partita', target: 2500, type: 'score' },
            { id: 'reach_level_5', desc: 'Raggiungi Livello 5', target: 5, type: 'level' },
            { id: 'play_10_games', desc: 'Gioca 10 Partite', target: 10, type: 'games' },
            { id: 'collect_no_hazard', desc: 'Raccogli 20 oggetti senza colpire X', target: 20, type: 'combo' },
            { id: 'survive_60s', desc: 'Sopravvivi 60 secondi', target: 60, type: 'time' },
            { id: 'collect_magnet', desc: 'Raccogli 7 Magneti', target: 7, type: 'collect', item: 'powerup_magnet' },
            { id: 'collect_shield', desc: 'Raccogli 10 Scudi', target: 10, type: 'collect', item: 'powerup_shield' }
        ];

        // Simula missioni giornaliere (in futuro backend)
        let dailyMissions = [];
        let lastMissionsDateStr = null; // Track the date for missions

        function cleanOldMissionKeys() {
            // Pulisce le chiavi delle missioni dei giorni precedenti dal localStorage
            try {
                const todayStr = new Date().toDateString();
                const keysToRemove = [];

                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    // Pulisci solo chiavi non di oggi (sia col vecchio formato sia col nuovo formato con userId)
                    if (key && key.startsWith('floppy_missions_') && !key.endsWith(todayStr)) {
                        keysToRemove.push(key);
                    }
                }

                keysToRemove.forEach(key => {
                    localStorage.removeItem(key);
                    console.log('[Missions] Rimossa chiave vecchia:', key);
                });

                if (keysToRemove.length > 0) {
                    console.log(`[Missions] Pulite ${keysToRemove.length} chiavi vecchie dal localStorage`);
                }
            } catch (e) {
                console.warn('[Missions] Errore pulizia localStorage:', e);
            }
        }

        function initDailyMissions() {
            // Pulisci sempre le chiavi vecchie all'avvio
            cleanOldMissionKeys();

            // Seleziona 3 a caso
            // Seed basilare con la data per renderle uguali oggi
            const dateStr = new Date().toDateString();
            console.log('[Missions] Inizializzazione missioni per data:', dateStr);

            // Se la data è cambiata, reset completo
            if (lastMissionsDateStr && lastMissionsDateStr !== dateStr) {
                console.log('[Missions] Data cambiata! Reset missioni da', lastMissionsDateStr, 'a', dateStr);
            }
            lastMissionsDateStr = dateStr;

            let seed = 0;
            const seedStr = dateStr + (window.currentUserId || '');
            for (let i = 0; i < seedStr.length; i++) seed += seedStr.charCodeAt(i);

            const pool = [...MISSIONS_POOL];
            dailyMissions = [];
            for (let i = 0; i < 3; i++) {
                const idx = (seed + i * 7) % pool.length;
                dailyMissions.push({ ...pool[idx], progress: 0, completed: false });
                pool.splice(idx, 1);
            }

            // Load progress SOLO se la chiave corrisponde alla data di oggi e all'utente loggato se disponibile
            try {
                const userIdSuffix = window.currentUserId ? `_${window.currentUserId}_` : '_';
                const savedKey = `floppy_missions${userIdSuffix}${dateStr}`;
                const saved = localStorage.getItem(savedKey);
                if (saved) {
                    const savedData = JSON.parse(saved);

                    // Verifica che i dati salvati abbiano gli stessi ID delle missioni di oggi
                    const savedIds = new Set(savedData.map(x => x.id));
                    const todayIds = new Set(dailyMissions.map(m => m.id));

                    // Se gli ID non corrispondono, ignora i dati salvati (missioni diverse)
                    const idsMatch = dailyMissions.every(m => savedIds.has(m.id));

                    if (idsMatch) {
                        // Merge progress
                        dailyMissions.forEach(m => {
                            const s = savedData.find(x => x.id === m.id);
                            if (s) {
                                m.progress = s.progress;
                                m.completed = s.completed;
                            }
                        });
                        console.log('[Missions] Progressi caricati:', dailyMissions.map(m => `${m.id}: ${m.progress}/${m.target}`));
                    } else {
                        console.log('[Missions] ID missioni non corrispondono, ignoro dati salvati');
                        localStorage.removeItem(savedKey);
                    }
                } else {
                    console.log('[Missions] Nessun progresso salvato per oggi, missioni fresche');
                }
            } catch (e) {
                console.warn('[Missions] Errore caricamento progressi:', e);
            }
        }

        function updateMissions(event, val) {
            let userNotified = false;
            dailyMissions.forEach(m => {
                if (m.completed) return;

                if (m.type === 'collect' && event === 'collect' && val.type === m.item) {
                    m.progress++;
                } else if (m.type === 'score' && event === 'game_over' && val >= m.target) {
                    m.progress = m.target;
                } else if (m.type === 'level' && event === 'level_up' && val >= m.target) {
                    m.progress = m.target;
                } else if (m.type === 'games' && event === 'game_start') {
                    m.progress++;
                } else if (m.type === 'combo' && event === 'collect_safe') {
                    m.progress++;
                } else if (m.type === 'combo' && event === 'hit_hazard') {
                    m.progress = 0;
                } else if (m.type === 'time' && event === 'survived' && val >= m.target) {
                    m.progress = val;
                }

                if (m.progress >= m.target && !m.completed) {
                    m.completed = true;
                    // Notifica UI
                    if (!userNotified) {
                        creaNotificaGioco(`🎯 Missione Completata: ${m.desc}!`);
                        userNotified = true;
                    }

                    // Send completion to backend
                    fetch('/api/flappy/complete_mission', {
                        method: 'POST',
                        headers: { 
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ mission_id: m.id })
                    })
                        .then(r => r.json())
                        .then(data => {
                            if (data.new_unlock && data.unlocked_skin_name) {
                                creaNotificaGioco(`🎉 NUOVA SKIN SBLOCCATA: ${data.unlocked_skin_name}! ${data.unlocked_skin_icon || ''}`);
                                syncProfile();
                            } else if (data.new_unlock) {
                                creaNotificaGioco("🎉 NUOVA SKIN SBLOCCATA!");
                                syncProfile();
                            }
                        })
                        .catch(e => console.log("Mission sync error:", e));
                }
            });

            // Save Progress
            try {
                const dateStr = new Date().toDateString();
                const userIdSuffix = window.currentUserId ? `_${window.currentUserId}_` : '_';
                const key = `floppy_missions${userIdSuffix}${dateStr}`;
                // Save sparse data
                const toSave = dailyMissions.map(m => ({ id: m.id, progress: m.progress, completed: m.completed }));
                localStorage.setItem(key, JSON.stringify(toSave));
            } catch (e) { }

            // Update UI
            updateMissionsUi();
        }

        let activePowerups = {
            shield: { active: false, timer: 0, icon: '🛡️' },
            slow: { active: false, timer: 0, icon: '🐌' },
            magnet: { active: false, timer: 0, icon: '🧲' },
            tiny: { active: false, timer: 0, icon: '🐜' },
            score_mult: { active: false, timer: 0, icon: '🎰' },
            laser: { active: false, timer: 0, icon: '🔫' },
            flame: { active: false, timer: 0, icon: '🔥' },
            ghost: { active: false, timer: 0, icon: '👻' }
        };

        let combo = {
            count: 0,
            timer: 0,
            maxTime: 2.5,
            lastType: null,
            flameFreebieActive: false
        };

        function activatePowerup(type) {
            const POWERUP_DURATIONS = {
                shield: 10000,
                ghost: 5000,
                slow: 5000,
                magnet: 8000,
                tiny: 5000,
                score_mult: 7000,
                laser: 5000,
                flame: 0  // Instant effect, no duration
            };

            // Generic activation logic
            const p = type.replace('powerup_', ''); // handle 'powerup_shield' vs 'shield' internally if needed, mostly 'shield' passed

            // Map types if needed (spawnItem sends 'powerup_shield', checks here expect 'shield'?)
            // Actually spawnItem sends 'powerup_shield', logic below compares type === 'shield'. 
            // Fix: Clean type string or handle mapping. 
            // Current code passes 'shield' directly from update(). 
            // Let's standardise on short names in this function.

            let key = type;

            // Special Flame Logic: Instant combo boost
            if (key === 'flame') {
                // If combo is 0, enable freebie (next item starts combo regardless of type)
                if (combo.count === 0) {
                    combo.flameFreebieActive = true;
                }
                combo.count += 3;
                combo.timer = combo.maxTime;
                creaNotificaGioco(`🔥 COMBO +3! (${combo.count}x)`);
                if (vibrationEnabled) triggerVibration([100, 50, 100]);
                return; // Don't run standard activation logic
            }

            if (activePowerups[key]) {
                if (activePowerups[key].active) {
                    activePowerups[key].timer += POWERUP_DURATIONS[key];
                } else {
                    activePowerups[key].active = true;
                    activePowerups[key].timer = POWERUP_DURATIONS[key];
                }
                const totalSecs = Math.ceil(activePowerups[key].timer / 1000);

                let msg = "";
                if (key === 'shield') msg = `🛡️ SCUDO ATTIVO! (${totalSecs}s)`;
                else if (key === 'slow') msg = `🐌 SLOW MOTION! (${totalSecs}s)`;
                else if (key === 'magnet') msg = `🧲 MAGNETE ATTIVO! (${totalSecs}s)`;
                else if (key === 'tiny') msg = `🐜 PICCOLO! (${totalSecs}s)`;
                else if (key === 'score_mult') msg = `🎰 PUNTI DOPPI! (${totalSecs}s)`;
                else if (key === 'laser') msg = `🔫 LASER! (${totalSecs}s)`;
                else if (key === 'flame') msg = `🔥 COMBO +3!`;
                else if (key === 'ghost') msg = `👻 FANTASMA! (${totalSecs}s)`;

                creaNotificaGioco(msg);
            }

            if (vibrationEnabled) triggerVibration([100, 50, 100]);
        }

        let gameNotifications = [];
        function creaNotificaGioco(text) {
            gameNotifications.push({ text: text, life: 2.0, y: Math.random() * 100 + 100 });
        }

        function showToast(text) {
            let t = document.getElementById('toast-msg');
            if (!t) {
                t = document.createElement('div');
                t.id = 'toast-msg';
                t.className = 'toast';
                document.body.appendChild(t);
            }
            t.innerText = text;
            t.classList.add('visible');
            if (t.timeout) clearTimeout(t.timeout);
            t.timeout = setTimeout(() => t.classList.remove('visible'), 2500);
        }

        // SKINS
        let unlockedSkins = ["default"];
        let selectedSkin = "default";
        let gamesOver2000Count = 0;
        let morningPlays = 0;
        let nightPlays = 0;
        let highScore = 0; // Sync from backend
        let missionsCompleted = 0; // Total missions completed
        let playerCoins = 0; // In-game currency
        let coinsCollectedThisGame = 0; // Coins collected in current game

        const SKINS = {
            "default": "🦅",
            "duck": "🦆",
            "pigeon": "🐦",
            "parrot": "🦜",
            "owl": "🦉",
            "rooster": "🐓",
            "dodo": "🦤",
            "phoenix": "🐦‍🔥",
            "dragon": "🐉",
            "flamingo": "🦩",
            "peacock": "🦚",
            "penguin": "🐧",
            "turkey": "🦃",
            "chick": "🐤",
            "hen": "🐔",
            "bat": "🦇",
            "swan": "🦢",
            "goose": "🪿",
            "hatchling": "🐣",
            "bee": "🐝",
            "raven": "🐦‍⬛",
            "dove": "🕊️",
            "goat": "🐐",
            "canary": "🐥",
            "butterfly": "🦋",
            "unicorn": "🦄",
            "ladybug": "🐞",
            "mosquito": "🦟"
        };

        function syncProfile() {
            fetch('/api/flappy/sync', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            })
                .then(r => r.json())
                .then(data => {
                    unlockedSkins = data.skins || ["default"];
                    selectedSkin = data.selected_skin || "default";
                    gamesOver2000Count = data.games_over_2000 || 0;
                    morningPlays = data.morning_plays || 0;
                    nightPlays = data.night_plays || 0;
                    highScore = data.high_score || 0;
                    missionsCompleted = data.missions_count || 0;
                    playerCoins = data.coins || 0;
                    updateSkinSelector();
                    updateStartScreenSkin();
                    updateShopCoinsDisplay();
                })
                .catch(e => console.log("Offline or error sync", e));
        }

        // --- CONFIG BILANCIATO: più difficile, più oggetti ---
        const CONFIG = {
            // Fisica: gravità più forte, salto uguale → più "tecnico"
            gravity: 0.42,
            jumpStrength: -6.8,

            // Velocità e gap: progressione RAPIDA e aggressiva
            baseSpeed: 3.0,  // Velocità base (era 2.7)
            baseGap: 210,
            minGap: 155,  // Gap minimo (era 140)
            pipeWidth: 66,

            // Difficoltà progressiva RAPIDA
            pipesPerLevel: 10,  // Più tubi per livello = passaggio di livello più lento

            // Tubi con intervallo adeguato alla velocità ridotta
            basePipeSpawnMs: 1610,  // Proporzionale a velocità 2.7
            minPipeSpawnMs: 1280,  // Proporzionale a velocità 2.7
            pipeSpawnVariation: 0.10,

            // Safe zone rare e brevi
            safeZoneChance: 0.04,
            safeZoneDurationMs: 1000,

            // Oggetti: margini ridotti, spawn più frequente
            itemGapMarginY: 50,
            itemAheadOffsetX: 160,
            itemMinDistFromPipe: 80,

            // Distanza tra item ridotta → più oggetti a schermo
            itemMinDistBetweenItemsX: 180,
            itemMinDistBetweenItemsY: 50,

            // Timer oggetti più veloce, spawn rate più alto
            itemCooldownMs: 600,
            itemSpawnRateMult: 0.70,
            itemDensityChangeChance: 0.05,

            decoSpawnIntervalMs: 10000,
            parallaxSpeeds: [0.1, 0.3, 0.6],

            // Controllo distanza verticale tra tubi consecutivi
            maxVerticalJumpBetweenPipes: 180,  // Pixel massimi di differenza verticale tra tubi (ridotto da 200 a 120)

            showSafeZoneOverlay: false,
            debug: false
        };

        // --- GAME STATE (usa le variabili globali già dichiarate sopra) ---
        // isPlaying e isGameOver sono già dichiarate all'inizio dello script
        let score = 0;
        let currentLevel = 1;
        let lastTime = 0;
        let elapsedMs = 0;
        let pipeTimerMs = 0;
        let safeZoneTimerMs = 0;
        let itemTimerMs = 0;
        let decoTimerMs = 0;
        let pipesSpawned = 0;
        let backgroundOffset = 0;
        let currentDensity = 0.50;

        let gameSpeed = CONFIG.baseSpeed;
        let bgColor = { h: 210, s: 15, l: 15 };

        const EAGLE_ICON = "🦅";
        const PIZZA_ICON = "🍕";
        const BEER_ICON = "🍺";
        const X_ICON = "❌";
        const DECO_ICONS = ["🛰️", "🛸", "🎈", "🚀", "🪐", "💫"];

        let bird = { x: 50, y: 150, radius: 18, velocity: 0, rotation: 0 };

        let pipes = [];
        let items = [];
        let decorations = [];
        let nextEmojiId = 1;
        let stars = [];
        let particles = [];

        let logicalWidth = 0;
        let logicalHeight = 0;
        let dpr = 1;

        function clampNumber(value, min, max) {
            return Math.max(min, Math.min(max, value));
        }

        function initParallax() {
            stars = [];
            for (let i = 0; i < 50; i++) {
                stars.push({
                    x: Math.random() * logicalWidth,
                    y: Math.random() * logicalHeight,
                    size: Math.random() * 2,
                    speed: CONFIG.parallaxSpeeds[0]
                });
            }
            particles = [];
            for (let i = 0; i < 20; i++) {
                particles.push({
                    x: Math.random() * logicalWidth,
                    y: Math.random() * logicalHeight,
                    size: Math.random() * 3 + 1,
                    speed: CONFIG.parallaxSpeeds[1]
                });
            }
        }

        function resizeCanvas() {
            dpr = Math.max(1, window.devicePixelRatio || 1);
            logicalWidth = Math.max(1, window.innerWidth);
            logicalHeight = Math.max(1, window.innerHeight);

            canvas.style.width = logicalWidth + 'px';
            canvas.style.height = logicalHeight + 'px';
            canvas.width = Math.floor(logicalWidth * dpr);
            canvas.height = Math.floor(logicalHeight * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            // Ottimizzazioni per rendering emoji iOS
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            bird.x = logicalWidth * 0.22;
            bird.y = clampNumber(bird.y || (logicalHeight / 2), bird.radius + 1, logicalHeight - bird.radius - 1);

            initParallax();
            try { draw(); } catch (_) { }
        }
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();

        function sfxJump() {
            playTone(620, 0.08, 'square', 0.9);
            playTone(820, 0.06, 'square', 0.6);
        }

        function sfxPositive() {
            const pitch = 540 + Math.random() * 100;
            playTone(pitch, 0.06, 'triangle', 0.9);
            playTone(pitch * 1.5, 0.08, 'triangle', 0.7);
        }

        function sfxNegative() {
            playTone(160, 0.14, 'sawtooth', 0.8);
            playTone(120, 0.10, 'sawtooth', 0.6);
        }

        function sfxCollision() {
            playTone(90, 0.18, 'sawtooth', 1.0);
            playTone(60, 0.15, 'sawtooth', 0.8);
        }

        function sfxPowerup() {
            playTone(800, 0.1, 'sine', 0.8);
            playTone(1000, 0.15, 'sine', 0.6);
            playTone(1200, 0.2, 'sine', 0.4);
        }

        function sfxCombo(count) {
            const basePitch = 600 + (count * 50);
            playTone(basePitch, 0.08, 'square', 0.9);
            playTone(basePitch * 1.5, 0.12, 'square', 0.7);
        }

        function sfxLevelUp() {
            playTone(440, 0.1, 'triangle', 1.0);
            playTone(554, 0.1, 'triangle', 0.9);
            playTone(659, 0.15, 'triangle', 0.8);
        }

        function sfxCoinCollect() {
            // Bright coin sound: two quick ascending tones
            playTone(880, 0.08, 'sine', 0.7);
            playTone(1320, 0.12, 'sine', 0.5);
        }

        function jump() {
            if (!isPlaying) return;
            bird.velocity = CONFIG.jumpStrength;
            try {
                initAudio();
                if (audio.ctx && audio.ctx.state === 'suspended') audio.ctx.resume();
            } catch (_) { }
            sfxJump();
        }

        window.addEventListener('keydown', (e) => {
            if (e.code === 'KeyD') CONFIG.debug = !CONFIG.debug;
            if (e.code === 'Space') {
                // Controlla requisiti prima di permettere l'avvio
                if (!isPlaying && isStartScreenVisible()) {
                    if (!gameAllowed) {
                        return; // Non avviare se requisiti non soddisfatti
                    }
                    startGame();
                    return;
                }
                if (isGameOver) resetGame();
                else if (isPlaying) jump();
            }
        });

        // IMPORTANTISSIMO: non bloccare click/tap UI.
        // touchstart globale -> fa jump solo se NON tocchi UI interattiva.
        function isUiInteractiveTarget(target) {
            return !!(
                target.closest('#start-screen') ||
                target.closest('#game-over-screen') ||
                target.closest('#leaderboard-screen') ||
                target.closest('#requirements-screen') ||
                target.closest('#shop-screen') ||
                target.closest('#skins-screen') ||
                target.closest('#info-screen') ||
                target.closest('#volume-control') ||
                target.closest('button') ||
                target.closest('a') ||
                target.closest('.skin-btn') // Prevent jump when clicking skins
            );
        }

        window.addEventListener('touchstart', (e) => {
            const target = e.target;
            // Additional check: never jump if clicking inside skins container
            if (target.closest('#skins-container') || isUiInteractiveTarget(target)) return;

            if (!isPlaying && isStartScreenVisible()) return;
            if (isGameOver) return;

            e.preventDefault();
            jump();
        }, { passive: false });

        window.addEventListener('mousedown', (e) => {
            const target = e.target;
            if (target.closest('#skins-container') || isUiInteractiveTarget(target)) return;

            if (isGameOver) return;
            if (!isPlaying && isStartScreenVisible()) return;
            jump();
        });

        // Binding robusti: invece di onclick inline (che su mobile può non scattare in alcuni contesti)
        function showLeaderboard() {
            if (leaderboardScreen) {
                leaderboardScreen.classList.remove('hidden');
                leaderboardScreen.scrollTop = 0;

                // === RANK CHANGE TRACKING ===
                updateRankChanges();
            }
        }

        function updateRankChanges() {
            const STORAGE_KEY = 'flappy_leaderboard_snapshot';
            const EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 ore

            const leaderboardList = document.getElementById('leaderboard-generale');
            if (!leaderboardList) return;

            const items = leaderboardList.querySelectorAll('.leaderboard-item[data-player-id]');
            if (!items.length) return;

            // Costruisci la classifica attuale
            const currentRanks = {};
            items.forEach(item => {
                const playerId = item.dataset.playerId;
                const position = parseInt(item.dataset.position);
                currentRanks[playerId] = position;
            });

            // Carica snapshot precedente
            let snapshot = null;
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored) {
                    snapshot = JSON.parse(stored);
                    // Verifica se è scaduto (più di 24h)
                    if (Date.now() - snapshot.timestamp > EXPIRY_MS) {
                        snapshot = null;
                    }
                }
            } catch (e) {
                console.log('Errore lettura snapshot:', e);
            }

            // Mostra le freccette
            items.forEach(item => {
                const playerId = item.dataset.playerId;
                const currentPos = parseInt(item.dataset.position);
                const changeSpan = item.querySelector('.rank-change');
                if (!changeSpan) return;

                changeSpan.className = 'rank-change'; // Reset

                if (snapshot && snapshot.ranks) {
                    const oldPos = snapshot.ranks[playerId];
                    if (oldPos === undefined) {
                        // Nuovo giocatore in classifica
                        changeSpan.classList.add('new');
                    } else if (oldPos > currentPos) {
                        // Salito (posizione più bassa = migliore)
                        changeSpan.classList.add('up');
                        changeSpan.title = `+${oldPos - currentPos} posizion${oldPos - currentPos > 1 ? 'i' : 'e'}`;
                    } else if (oldPos < currentPos) {
                        // Sceso
                        changeSpan.classList.add('down');
                        changeSpan.title = `-${currentPos - oldPos} posizion${currentPos - oldPos > 1 ? 'i' : 'e'}`;
                    }
                    // Se oldPos === currentPos, nessuna freccia (invariato)
                }
            });

            // Salva nuovo snapshot solo se non c'è o è scaduto
            if (!snapshot) {
                localStorage.setItem(STORAGE_KEY, JSON.stringify({
                    timestamp: Date.now(),
                    ranks: currentRanks
                }));
            }
        }

        function hideLeaderboard() {
            if (leaderboardScreen) leaderboardScreen.classList.add('hidden');
        }

        // start/restart/mute/classifica chiudi
        function bindUi() {
            const startBtn = document.getElementById('start-btn');
            if (startBtn) {
                startBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (gameAllowed) startGame();
                });
                startBtn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    if (gameAllowed) startGame();
                }, { passive: false });
            } else {
                console.log('Start button NON trovato!');
            }

            const restartBtn = document.getElementById('restart-btn');
            if (restartBtn) {
                restartBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (gameAllowed) resetGame();
                });
                restartBtn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    if (gameAllowed) resetGame();
                }, { passive: false });
            }

            const muteBtn = document.getElementById('mute-btn');
            if (muteBtn) {
                muteBtn.addEventListener('click', (e) => { e.preventDefault(); toggleMute(); });
                muteBtn.addEventListener('touchend', (e) => { e.preventDefault(); toggleMute(); }, { passive: false });
            }

            // bottoni classifica: ce ne sono due (start e game over)
            document.querySelectorAll('[data-action="leaderboard-open"]').forEach((btn) => {
                btn.addEventListener('click', (e) => { e.preventDefault(); showLeaderboard(); });
                btn.addEventListener('touchend', (e) => { e.preventDefault(); showLeaderboard(); }, { passive: false });
            });

            const closeLb = document.querySelector('[data-action="leaderboard-close"]');
            if (closeLb) {
                closeLb.addEventListener('click', (e) => { e.preventDefault(); hideLeaderboard(); });
                closeLb.addEventListener('touchend', (e) => { e.preventDefault(); hideLeaderboard(); }, { passive: false });
                closeLb.addEventListener('touchend', (e) => { e.preventDefault(); hideLeaderboard(); }, { passive: false });
            }

            const vibBtn = document.getElementById('vib-toggle-btn');
            if (vibBtn) {
                updateVibrationUi(); // Init UI
                vibBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    toggleVibration();
                });
                vibBtn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    toggleVibration();
                }, { passive: false });
            }

            // Skins screen back button
            const skinsBackBtn = document.getElementById('skins-back-btn');
            if (skinsBackBtn) {
                skinsBackBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    hideSkinsScreen();
                });
                skinsBackBtn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    hideSkinsScreen();
                }, { passive: false });
            }

            // Equip skin button
            const equipBtn = document.getElementById('equip-skin-btn');
            if (equipBtn) {
                equipBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    equipPreviewedSkin();
                });
                equipBtn.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    equipPreviewedSkin();
                }, { passive: false });
            }
        }


        function updateMissionsUi() {
            const container = document.getElementById('missions-list');
            if (!container) return;
            container.innerHTML = dailyMissions.map(m => `
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>${m.completed ? '✅' : '⬜'} ${m.desc}</span>
                    <span>${Math.min(m.progress, m.target)}/${m.target}</span>
                </div>
             `).join('');
        }

        const skinRequirements = {
            "default": "Base",
            "duck": "15 partite > 2000pt",
            "pigeon": "50 partite > 2000pt",
            "chick": "100 partite > 2000pt",
            "swan": "200 partite > 2000pt",
            "goose": "500 partite > 2000pt",
            "hatchling": "1000 partite > 2000pt",
            "parrot": "Record 7500",
            "owl": "3 Notti Diverse (1-5 AM)",
            "bat": "10 Notti Diverse (1-5 AM)",
            "rooster": "3 Mattine Diverse (5-7 AM)",
            "hen": "10 Mattine Diverse (5-7 AM)",
            "dodo": "30 Missioni Completate",
            "bee": "100 Missioni Completate",
            "dragon": "200 Missioni Completate",
            "phoenix": "Raggiungi Livello 10",
            "raven": "🏆 Top Denunciatore del Mese",
            "dove": "🏆 Top MVP del Mese",
            "goat": "🏆 Top Floppy Eagle del Mese",
            "flamingo": "💰 150 Monete (Negozio)",
            "peacock": "💰 250 Monete (Negozio)",
            "penguin": "💰 500 Monete (Negozio)",
            "turkey": "💰 50 Monete (Negozio)",
            "canary": "💰 750 Monete (Negozio)",
            "butterfly": "💰 1000 Monete (Negozio)",
            "unicorn": "💰 5000 Monete (Negozio)",
            "ladybug": "🏆 Assegnato da Admin",
            "mosquito": "🏆 Top Donatore del Mese"
        };

        const skinNames = {
            "default": "Aquila",
            "duck": "Papera",
            "pigeon": "Piccione",
            "parrot": "Pappagallo",
            "owl": "Gufo",
            "rooster": "Gallo",
            "dodo": "Dodo",
            "phoenix": "Fenice",
            "dragon": "Drago",
            "flamingo": "Fenicottero",
            "peacock": "Pavone",
            "penguin": "Pinguino",
            "turkey": "Tacchino",
            "chick": "Pulcino",
            "hen": "Gallina",
            "bat": "Pipistrello",
            "swan": "Cigno",
            "goose": "Oca",
            "hatchling": "Pulcino Nascente",
            "bee": "Ape",
            "raven": "Corvo",
            "dove": "Colomba",
            "goat": "Capra",
            "canary": "Canarino",
            "butterfly": "Farfalla",
            "unicorn": "Unicorno",
            "ladybug": "Coccinella",
            "mosquito": "Zanzara"
        };

        // Track which skin is being previewed (separate from equipped)
        let previewingSkin = null;

        function showSkinsScreen() {
            const skinsScreen = document.getElementById('skins-screen');
            let startScreen = document.getElementById('start-screen');
            if (skinsScreen) skinsScreen.classList.remove('hidden');
            if (startScreen) startScreen.classList.add('hidden');
            previewingSkin = selectedSkin; // Start showing equipped skin
            updateSkinSelector();
        }

        function hideSkinsScreen() {
            const skinsScreen = document.getElementById('skins-screen');
            let startScreen = document.getElementById('start-screen');
            if (skinsScreen) skinsScreen.classList.add('hidden');
            if (startScreen) startScreen.classList.remove('hidden');
            previewingSkin = null;
        }

        // === INFO SCREEN ===
        function showInfoScreen() {
            const infoScreen = document.getElementById('info-screen');
            let startScreen = document.getElementById('start-screen');
            if (infoScreen) infoScreen.classList.remove('hidden');
            if (startScreen) startScreen.classList.add('hidden');
        }

        function hideInfoScreen() {
            const infoScreen = document.getElementById('info-screen');
            let startScreen = document.getElementById('start-screen');
            if (infoScreen) infoScreen.classList.add('hidden');
            if (startScreen) startScreen.classList.remove('hidden');
        }

        function showInfoTab(tab) {
            const rulesTab = document.getElementById('info-tab-rules');
            const scoreTab = document.getElementById('info-tab-scoreops');
            const btnRules = document.getElementById('tabRules');
            const btnScore = document.getElementById('tabScoreOps');

            if (tab === 'rules') {
                if (rulesTab) rulesTab.classList.remove('hidden');
                if (scoreTab) scoreTab.classList.add('hidden');
                if (btnRules) { btnRules.classList.add('active'); btnRules.classList.remove('btn-outline-secondary'); }
                if (btnScore) { btnScore.classList.remove('active'); btnScore.classList.add('btn-outline-secondary'); }
            } else {
                if (rulesTab) rulesTab.classList.add('hidden');
                if (scoreTab) scoreTab.classList.remove('hidden');
                if (btnRules) { btnRules.classList.remove('active'); btnRules.classList.add('btn-outline-secondary'); }
                if (btnScore) { btnScore.classList.add('active'); btnScore.classList.remove('btn-outline-secondary'); }
            }
        }

        // === SHOP SYSTEM ===
        const SHOP_ITEMS = {
            flamingo: { price: 150, name: 'Fenicottero', icon: '🦩' },
            peacock: { price: 250, name: 'Pavone', icon: '🦚' },
            penguin: { price: 500, name: 'Pinguino', icon: '🐧' },
            turkey: { price: 50, name: 'Tacchino', icon: '🦃' },
            canary: { price: 750, name: 'Canarino', icon: '🐥' },
            butterfly: { price: 1000, name: 'Farfalla', icon: '🦋' },
            unicorn: { price: 5000, name: 'Unicorno', icon: '🦄' }
        };

        function showShopScreen() {
            const shopScreen = document.getElementById('shop-screen');
            let startScreen = document.getElementById('start-screen');
            if (shopScreen) shopScreen.classList.remove('hidden');
            if (startScreen) startScreen.classList.add('hidden');
            updateShopCoinsDisplay();
            updateShopItems();
        }

        function hideShopScreen() {
            const shopScreen = document.getElementById('shop-screen');
            let startScreen = document.getElementById('start-screen');
            if (shopScreen) shopScreen.classList.add('hidden');
            if (startScreen) startScreen.classList.remove('hidden');
        }

        function updateShopCoinsDisplay() {
            const el = document.getElementById('shop-coins-display');
            if (el) el.innerText = playerCoins;
            updateHudCoins();  // Also update HUD
        }

        function updateHudCoins() {
            const hudEl = document.getElementById('hud-coin-count');
            if (hudEl && typeof playerCoins !== 'undefined') {
                hudEl.innerText = playerCoins;
            }
        }

        function updateShopItems() {
            const grid = document.getElementById('shop-items-grid');
            if (!grid) return;
            grid.innerHTML = '';

            for (let key in SHOP_ITEMS) {
                const item = SHOP_ITEMS[key];
                const isOwned = unlockedSkins.includes(key);
                const canAfford = playerCoins >= item.price;

                const card = document.createElement('div');
                card.style.cssText = `
                    background: ${isOwned ? 'rgba(76, 175, 80, 0.2)' : 'rgba(255,255,255,0.05)'};
                    border: 2px solid ${isOwned ? '#4CAF50' : (canAfford ? '#FFC107' : '#666')};
                    border-radius: 16px;
                    padding: 15px 10px;
                    text-align: center;
                    transition: all 0.3s;
                `;

                card.innerHTML = `
                    <div style="font-size: 40px; margin-bottom: 8px;">${item.icon}</div>
                    <div style="font-size: 14px; color: #FFC107; margin-bottom: 5px;">${item.name}</div>
                    <div style="font-size: 16px; color: ${isOwned ? '#4CAF50' : '#fff'}; margin-bottom: 10px;">
                        ${isOwned ? '✅ Acquistato' : `🪙 ${item.price}`}
                    </div>
                    ${!isOwned ? `
                        <button class="btn ${canAfford ? '' : 'btn-outline'}" 
                            style="padding: 6px 15px; font-size: 12px; ${!canAfford ? 'opacity: 0.5;' : ''}"
                            onclick="buyShopItem('${key}')"
                            ${!canAfford ? 'disabled' : ''}>
                            ${canAfford ? 'COMPRA' : 'No monete'}
                        </button>
                    ` : ''}
                `;
                grid.appendChild(card);
            }
        }

        function buyShopItem(itemId) {
            fetch('/api/flappy/shop/buy', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ item_id: itemId })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        playerCoins = data.remaining_coins;
                        unlockedSkins.push(itemId);
                        updateShopCoinsDisplay();
                        updateShopItems();
                        showToast(`🎉 ${data.item_name} acquistato!`);
                        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
                    } else {
                        showToast('❌ ' + (data.error || 'Errore acquisto'));
                    }
                })
                .catch(e => showToast('❌ Errore connessione'));
        }

        function updateStartScreenSkin() {
            const el = document.getElementById('start-screen-skin');
            if (el && selectedSkin && SKINS[selectedSkin]) {
                el.innerText = SKINS[selectedSkin];
            }
        }

        function equipPreviewedSkin() {
            if (!previewingSkin) return;
            if (!unlockedSkins.includes(previewingSkin)) return;
            if (previewingSkin === selectedSkin) return; // Already equipped

            selectedSkin = previewingSkin;
            fetch('/api/flappy/sync', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ selected_skin: selectedSkin })
            });
            updateSkinSelector();
            updateStartScreenSkin();
            triggerVibration(30);
        }

        function updateSkinPreview(skinKey) {
            previewingSkin = skinKey; // Track what we're previewing

            const previewEmoji = document.getElementById('preview-emoji');
            const previewName = document.getElementById('preview-name');
            const unlockInfo = document.getElementById('unlock-info-text');
            const equipBtn = document.getElementById('equip-skin-btn');

            if (previewEmoji) previewEmoji.innerText = SKINS[skinKey] || '🦅';
            if (previewName) previewName.innerText = skinNames[skinKey] || skinKey;

            const isUnlocked = unlockedSkins.includes(skinKey);
            const isEquipped = (skinKey === selectedSkin);

            if (unlockInfo) {
                if (isUnlocked) {
                    if (isEquipped) {
                        unlockInfo.innerHTML = '✅ <span style="color: #4CAF50;">Equipaggiata</span>';
                    } else {
                        unlockInfo.innerHTML = '✅ <span style="color: #87CEEB;">Sbloccata</span>';
                    }
                } else {
                    let progress = '';
                    if (skinKey === 'duck') progress = ` (${gamesOver2000Count}/15)`;
                    if (skinKey === 'pigeon') progress = ` (${gamesOver2000Count}/50)`;
                    if (skinKey === 'chick') progress = ` (${gamesOver2000Count}/100)`;
                    if (skinKey === 'swan') progress = ` (${gamesOver2000Count}/200)`;
                    if (skinKey === 'goose') progress = ` (${gamesOver2000Count}/500)`;
                    if (skinKey === 'hatchling') progress = ` (${gamesOver2000Count}/1000)`;
                    if (skinKey === 'parrot') progress = ` (Record: ${highScore}/7500)`;
                    if (skinKey === 'owl') progress = ` (${nightPlays}/3)`;
                    if (skinKey === 'bat') progress = ` (${nightPlays}/10)`;
                    if (skinKey === 'rooster') progress = ` (${morningPlays}/3)`;
                    if (skinKey === 'hen') progress = ` (${morningPlays}/10)`;
                    if (skinKey === 'dodo') progress = ` (${missionsCompleted}/30)`;
                    if (skinKey === 'bee') progress = ` (${missionsCompleted}/100)`;
                    if (skinKey === 'dragon') progress = ` (${missionsCompleted}/200)`;
                    unlockInfo.innerHTML = `🔒 <span style="color: #f44336;">${skinRequirements[skinKey]}${progress}</span>`;
                }
            }

            // Show/hide equip button
            if (equipBtn) {
                if (isUnlocked && !isEquipped) {
                    equipBtn.style.display = 'inline-block';
                } else {
                    equipBtn.style.display = 'none';
                }
            }
        }

        function updateSkinSelector() {
            updateMissionsUi(); // Update missions too
            const container = document.getElementById('skins-grid');
            if (!container) return;
            container.innerHTML = '';

            for (let key in SKINS) {
                const isUnlocked = unlockedSkins.includes(key);
                const isSelected = selectedSkin === key;

                const btn = document.createElement('div');
                btn.className = 'skin-btn';
                btn.style.cssText = `
                    font-size: 32px; 
                    cursor: pointer; 
                    padding: 12px; 
                    border-radius: 16px; 
                    background: ${isSelected ? '#FFC107' : (isUnlocked ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.5)')};
                    color: ${isSelected ? '#000' : '#fff'};
                    opacity: ${isUnlocked ? 1 : 0.6};
                    border: 3px solid ${isSelected ? '#fff' : '#444'};
                    aspect-ratio: 1;
                    display: flex; align-items: center; justify-content: center;
                    transition: all 0.2s;
                    pointer-events: auto;
                    user-select: none;
                `;

                btn.innerText = isUnlocked ? SKINS[key] : '🔒';

                const handler = (e) => {
                    e.stopPropagation();
                    updateSkinPreview(key);
                    triggerVibration(15);
                };

                btn.onclick = handler;

                container.appendChild(btn);
            }

            // Update preview with currently selected skin
            updateSkinPreview(selectedSkin);
        }

        bindUi();
        initDailyMissions(); // Init missions on load
        syncProfile();

        // Expose functions to window for onclick handlers
        window.showSkinsScreen = showSkinsScreen;
        window.hideSkinsScreen = hideSkinsScreen;

        function updateScoreDisplay() {
            if (currentScoreEl) currentScoreEl.innerText = Math.floor(score);

            const newLevel = Math.floor(pipesSpawned / CONFIG.pipesPerLevel) + 1;
            if (newLevel > currentLevel) {
                currentLevel = newLevel;
                bgColor.h = (210 + currentLevel * 25) % 360;
                updateMissions('level_up', newLevel);
                sfxLevelUp(); // Play level up sound
                // updateMusicIntensity(currentLevel, gameSpeed); // Disabled
            }

            // Aggiorna indicatore livello
            const levelEl = document.getElementById('current-level');
            if (levelEl) levelEl.innerText = currentLevel;
        }

        function getPipeVariation() {
            const v = CONFIG.pipeSpawnVariation;
            return 1 + (Math.random() * v * 2 - v);
        }

        function difficultyAtLevel(level) {
            // Curva di difficoltà bilanciata con cap più morbido
            const speedFactor = clampNumber(1 + (level - 1) * 0.15, 1, 2.1);  // +0.15 per livello, max 2.1x velocità

            // Il gap smette di diminuire dal livello 6
            const gapLevel = Math.min(level, 6);
            const gap = clampNumber(CONFIG.baseGap - (gapLevel - 1) * 11, CONFIG.minGap, CONFIG.baseGap);

            // Spawn rate usa decadimento logaritmico: meno oppressivo nel late game
            const spawnMs = clampNumber(CONFIG.basePipeSpawnMs - 80 * Math.log(level), CONFIG.minPipeSpawnMs, CONFIG.basePipeSpawnMs);
            return { speedFactor, gap, spawnMs };
        }

        // Colori tubi basati sul livello per feedback visivo
        function getPipeColorsForLevel(level) {
            const colors = [
                { base: '#FFC107', light: '#FFE082', dark: '#B88600', highlight: '#D39E00' },  // Livello 1: Giallo
                { base: '#FF9800', light: '#FFCC80', dark: '#E65100', highlight: '#F57C00' },  // Livello 2: Arancione
                { base: '#FF5722', light: '#FF8A65', dark: '#BF360C', highlight: '#D84315' },  // Livello 3: Rosso-arancione
                { base: '#E91E63', light: '#F48FB1', dark: '#880E4F', highlight: '#C2185B' },  // Livello 4: Rosa
                { base: '#9C27B0', light: '#CE93D8', dark: '#4A148C', highlight: '#7B1FA2' },  // Livello 5: Viola
                { base: '#3F51B5', light: '#9FA8DA', dark: '#1A237E', highlight: '#283593' },  // Livello 6: Indaco
                { base: '#2196F3', light: '#90CAF9', dark: '#0D47A1', highlight: '#1565C0' },  // Livello 7: Blu
                { base: '#00BCD4', light: '#80DEEA', dark: '#006064', highlight: '#0097A7' },  // Livello 8: Ciano
            ];
            // Cicla i colori se il livello è superiore a 8
            const index = (level - 1) % colors.length;
            return colors[index];
        }

        function spawnPipe(gap) {
            const minHeight = 80;
            const maxPipeHeight = logicalHeight - gap - minHeight;
            let topHeight = Math.floor(Math.random() * (maxPipeHeight - minHeight + 1) + minHeight);

            // Controllo intelligente: evita salti verticali impossibili tra tubi consecutivi
            if (pipes.length > 0) {
                const lastPipe = pipes[pipes.length - 1];
                const lastGapCenter = lastPipe.topHeight + (lastPipe.bottomY - lastPipe.topHeight) / 2;
                const proposedGapCenter = topHeight + gap / 2;
                const verticalDiff = Math.abs(proposedGapCenter - lastGapCenter);

                // Se la differenza è troppo grande, riposiziona il tubo più vicino al precedente
                if (verticalDiff > CONFIG.maxVerticalJumpBetweenPipes) {
                    const maxOffset = CONFIG.maxVerticalJumpBetweenPipes;
                    if (proposedGapCenter > lastGapCenter) {
                        // Troppo in basso, riporta su
                        topHeight = Math.floor(lastGapCenter - gap / 2 + maxOffset);
                    } else {
                        // Troppo in alto, riporta giù
                        topHeight = Math.floor(lastGapCenter - gap / 2 - maxOffset);
                    }
                    // Clamp per sicurezza
                    topHeight = clampNumber(topHeight, minHeight, maxPipeHeight);
                }
            }

            // Init Segments for hole logic
            // Segments are solid parts.
            // Holes are spaces between segments.
            const pipe = {
                x: logicalWidth,
                topHeight,
                bottomY: topHeight + gap,
                width: CONFIG.pipeWidth,
                passed: false,
                topSegments: [{ y: 0, h: topHeight }], // Start as one solid block at top
                bottomSegments: [{ y: topHeight + gap, h: logicalHeight - (topHeight + gap) }] // Solid block from bottomY to end
            };

            pipes.push(pipe);
            pipesSpawned++;
        }

        function isItemCollidingWithPipe(itemX, itemY, itemR, pipe) {
            // Controlla se l'item (cerchio) collide con il tubo superiore o inferiore
            // Tubo superiore: da y=0 a y=pipe.topHeight
            // Tubo inferiore: da y=pipe.bottomY a y=logicalHeight

            // Margine di sicurezza extra per evitare sovrapposizioni visuali
            const safetyMargin = 30;

            // Overlap orizzontale con margine?
            if (itemX + itemR + safetyMargin < pipe.x || itemX - itemR - safetyMargin > pipe.x + pipe.width) {
                return false; // nessun overlap orizzontale
            }

            // Se c'è overlap orizzontale, controlla se è nel gap o nei tubi (con margini)
            const inGapVertically = (itemY - itemR - safetyMargin > pipe.topHeight) && (itemY + itemR + safetyMargin < pipe.bottomY);
            return !inGapVertically; // collide se NON è nel gap
        }

        function isItemCollidingWithAnyPipe(itemX, itemY, itemR, pipeList) {
            for (const pipe of pipeList) {
                if (isItemCollidingWithPipe(itemX, itemY, itemR, pipe)) {
                    return true;
                }
            }
            return false;
        }

        function findSafeSpawnPosition() {
            // Trova una posizione sicura per spawnare un item
            // Strategia: spawna in una zona tra l'ultimo tubo passato e il prossimo
            const itemR = 18;

            // Trova il tubo più a destra che è ancora sullo schermo
            let referencePipe = null;
            for (let i = pipes.length - 1; i >= 0; i--) {
                if (pipes[i].x > logicalWidth * 0.3 && pipes[i].x < logicalWidth + 100) {
                    referencePipe = pipes[i];
                    break;
                }
            }

            if (!referencePipe) return null;

            // Posiziona l'item a metà strada tra il tubo e il bordo destro, nel gap
            const minX = referencePipe.x + referencePipe.width + 60;
            const maxX = Math.min(logicalWidth + 50, referencePipe.x + referencePipe.width + 300);

            if (maxX <= minX) return null;

            const x = minX + Math.random() * (maxX - minX);

            // Y deve stare nel gap con margini di sicurezza
            const marginY = CONFIG.itemGapMarginY;
            const safeMinY = referencePipe.topHeight + marginY + itemR;
            const safeMaxY = referencePipe.bottomY - marginY - itemR;

            if (safeMaxY <= safeMinY) return null;

            const y = safeMinY + Math.random() * (safeMaxY - safeMinY);

            // Verifica finale: l'item non deve collidere con NESSUN tubo
            if (isItemCollidingWithAnyPipe(x, y, itemR, pipes)) {
                return null;
            }

            return { x, y };
        }

        function spawnItem() {
            const itemR = 14; // Smaller items for more skill

            // Trova una posizione sicura
            const pos = findSafeSpawnPosition();
            if (!pos) return; // Nessuna posizione sicura trovata

            const { x, y } = pos;

            // Distanza minima dall'ultimo item per evitare ammassamenti
            const lastItem = items.length ? items[items.length - 1] : null;
            if (lastItem) {
                const dx = Math.abs(x - lastItem.x);
                const dy = Math.abs(y - lastItem.y);
                if (dx < CONFIG.itemMinDistBetweenItemsX && dy < CONFIG.itemMinDistBetweenItemsY) {
                    return;
                }
            }

            const rand = Math.random();
            let type, icon, points;

            // Distribution with Coins:
            // Powerups (7 types) ~2.5% each -> Total ~17.5%
            // coin: 0.175 - 0.275 (10%)
            // Pizza: 0.275 - 0.525 (25%)
            // Beer:  0.525 - 0.775 (25%)
            // Hazard: 0.775 - 1.00 (22.5%)

            if (rand < 0.025) { type = 'powerup_shield'; icon = '🛡️'; points = 0; }
            else if (rand < 0.05) { type = 'powerup_slow'; icon = '🐌'; points = 0; }
            else if (rand < 0.075) { type = 'powerup_magnet'; icon = '🧲'; points = 0; }
            else if (rand < 0.10) { type = 'powerup_tiny'; icon = '🐜'; points = 0; }
            else if (rand < 0.125) { type = 'powerup_score_mult'; icon = '🎰'; points = 0; }
            else if (rand < 0.15) { type = 'powerup_laser'; icon = '🔫'; points = 0; }
            else if (rand < 0.175) { type = 'powerup_flame'; icon = '🔥'; points = 0; }
            else if (rand < 0.20) { type = 'powerup_ghost'; icon = '👻'; points = 0; }
            else if (rand < 0.205) { type = 'diamond'; icon = '💎'; points = 0; }  // 0.5% - Rarissimo! 50 monete
            else if (rand < 0.305) { type = 'coin'; icon = '🪙'; points = 5; }
            else if (rand < 0.545) { type = 'pizza'; icon = PIZZA_ICON; points = 100; }
            else if (rand < 0.785) { type = 'beer'; icon = BEER_ICON; points = 100; }
            else { type = 'hazard'; icon = X_ICON; points = -100; }

            items.push({ id: nextEmojiId++, x, y, type, icon, points, radius: itemR, collected: false, spawnedAtMs: elapsedMs });
        }

        function spawnDecoration() {
            const icon = DECO_ICONS[Math.floor(Math.random() * DECO_ICONS.length)];
            decorations.push({
                id: nextEmojiId++,
                x: logicalWidth + 100,
                y: Math.random() * (logicalHeight * 0.7) + 50,
                icon,
                speed: (Math.random() * 0.5 + 0.2) * gameSpeed,
                size: Math.random() * 20 + 20
            });
        }

        function startGame() {
            // Controllo requisiti (doppia sicurezza)
            if (!gameAllowed) {
                return;
            }

            if (startScreen) startScreen.classList.add('hidden');
            if (gameOverScreen) gameOverScreen.classList.add('hidden');
            if (leaderboardScreen) leaderboardScreen.classList.add('hidden');
            if (requirementsScreen) requirementsScreen.classList.add('hidden');

            // Show HUD
            const hud = document.getElementById('game-hud');
            if (hud) hud.classList.remove('hidden');

            // Show coin display during gameplay
            const coinDisplay = document.getElementById('coin-display');
            if (coinDisplay) coinDisplay.classList.add('visible');
            updateHudCoins();  // Initialize with current coin count

            isPlaying = true;
            isGameOver = false;
            score = 0;
            currentLevel = 1;
            lastTime = 0;
            elapsedMs = 0;
            pipeTimerMs = 0;
            safeZoneTimerMs = 0;
            itemTimerMs = 400;
            coinsCollectedThisGame = 0; // Reset coins for new game
            decoTimerMs = 5000;
            pipesSpawned = 0;
            gameSpeed = CONFIG.baseSpeed;
            pipes = [];
            items = [];
            decorations = [];
            nextEmojiId = 1;
            if (USE_DOM_EMOJI) clearEmojiLayer();
            currentDensity = 0.50;
            bgColor = { h: 210, s: 15, l: 15 };

            bird.y = logicalHeight / 2;
            bird.velocity = 0;
            bird.rotation = 0;

            // Reset Powerups & Combo
            activePowerups = {
                shield: { active: false, timer: 0, icon: '🛡️' },
                slow: { active: false, timer: 0, icon: '🐌' },
                magnet: { active: false, timer: 0, icon: '🧲' },
                tiny: { active: false, timer: 0, icon: '🐜' },
                score_mult: { active: false, timer: 0, icon: '🎰' },
                laser: { active: false, timer: 0, icon: '🔫' },
                flame: { active: false, timer: 0, icon: '🔥' },
                ghost: { active: false, timer: 0, icon: '👻' }
            };
            combo = { count: 0, timer: 0, maxTime: 2.5, lastType: null, flameFreebieActive: false };
            gameNotifications = [];
            lasers = []; // Reset lasers

            initParallax();
            try {
                initAudio();
                if (audio.ctx && audio.ctx.state === 'suspended') audio.ctx.resume();
                // startBackgroundMusic(); // Disabled - keeping only sound effects
            } catch (_) { }

            updateScoreDisplay();
            updateMissions('game_start', null);
            requestAnimationFrame(loop);
        }

        // Variable for lasers
        let lasers = [];
        let lastLaserTime = 0;

        function resetGame() {
            if (Date.now() - lastDeathTime < 1000) return; // Cooldown 1s
            if (gameOverScreen) gameOverScreen.classList.add('hidden');
            startGame();
        }

        function endGame() {
            if (isGameOver) return; // Prevent multiple calls
            isPlaying = false;
            isGameOver = true;
            lastDeathTime = Date.now();

            // Mantieni il bird visibile su iPhone per mostrare il punto di impatto
            if (USE_DOM_EMOJI) {
                clearEmojiLayerKeepBird();
                // Aggiorna la posizione del bird per mostrarlo nel punto di impatto
                updateDomEmojiLayer(0, 0);
            }

            // stopBackgroundMusic(); // Disabled

            sfxCollision();

            // fetch('/api/save_score'...) REDUNDANT removed

            // Snapshot the collected coins to avoid race condition if player restarts game immediately
            const coinsToSave = coinsCollectedThisGame || 0;

            // Update UI immediately
            let finalScoreEl = document.getElementById('final-score');
            let bestScoreEl = document.getElementById('best-score');
            let finalCoinsEl = document.getElementById('final-coins');
            const finalScore = Math.floor(score);
            
            if (finalScoreEl) finalScoreEl.innerText = finalScore;
            if (bestScoreEl) bestScoreEl.innerText = Math.max(highScore || 0, finalScore);
            if (finalCoinsEl) finalCoinsEl.innerText = coinsToSave;
            
            if (gameOverScreen) gameOverScreen.classList.remove('hidden');

            const persistCoinsFallback = () => {
                if (coinsToSave <= 0) {
                    return Promise.resolve(null);
                }

                return fetch('/api/flappy/save_coins', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ coins: coinsToSave })
                })
                    .then(r => r.json())
                    .then(coinData => {
                        if (coinData && coinData.success && coinData.total_coins !== undefined) {
                            playerCoins = coinData.total_coins;
                            updateHudCoins();
                            showToast(`🪙 +${coinsToSave} monete!`);
                        }
                        return coinData;
                    })
                    .catch(err => {
                        console.error('Error fallback saving coins', err);
                        return null;
                    });
            };

            fetch('/api/flappy/save_progress', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    score: finalScore,
                    level: currentLevel,
                    coins: coinsToSave
                })
            })
                .then(async r => {
                    const data = await r.json();
                    return { ok: r.ok, data };
                })
                .then(data => {
                    const payload = data.data || {};

                    if (payload.high_score !== undefined) {
                        highScore = payload.high_score || 0;
                        if (bestScoreEl) bestScoreEl.innerText = highScore;
                    }

                    const saveProgressFailed = !data.ok || payload.success === false;
                    if (saveProgressFailed) {
                        return persistCoinsFallback();
                    }

                    if (payload.total_coins !== undefined) {
                        playerCoins = payload.total_coins;
                        updateHudCoins();
                    }

                    if (coinsToSave > 0) {
                        showToast(`🪙 +${coinsToSave} monete!`);
                    }

                    if (payload.new_unlock && payload.unlocked_skin_name) {
                        creaNotificaGioco(`🎉 NUOVA SKIN SBLOCCATA: ${payload.unlocked_skin_name}! ${payload.unlocked_skin_icon || ''}`);
                        syncProfile();
                    } else if (payload.new_unlock) {
                        creaNotificaGioco("🎉 NUOVA SKIN SBLOCCATA!");
                        syncProfile();
                    }
                    return null;
                })
                .catch(err => {
                    console.error('Error saving progress', err);
                    persistCoinsFallback();
                });
            updateMissions('game_over', Math.floor(score));

            // Hide HUD
            const hud = document.getElementById('game-hud');
            if (hud) hud.classList.add('hidden');

            // Hide coin display
            const coinDisplay = document.getElementById('coin-display');
            if (coinDisplay) coinDisplay.classList.remove('visible');
        }

        function update(dtMs) {
            const dt = dtMs / 16.6667;
            elapsedMs += dtMs;
            const now = Date.now();

            // --- UPDATES ---

            // 1. Powerups Decays
            for (let key in activePowerups) {
                if (activePowerups[key].active) {
                    activePowerups[key].timer -= dtMs;
                    if (activePowerups[key].timer <= 0) activePowerups[key].active = false;
                }
            }

            // LASER Update
            if (activePowerups.laser.active) {
                if (now - lastLaserTime > 400) { // Shoot every 400ms
                    lasers.push({ x: bird.x + 20, y: bird.y, w: 30, h: 6, hit: false });
                    lastLaserTime = now;
                    // Could add laser sound here
                }
            }

            // Move Lasers
            for (let i = 0; i < lasers.length; i++) {
                lasers[i].x += 15 * dt; // Fast projectile
                if (lasers[i].x > logicalWidth + 100) {
                    lasers.splice(i, 1);
                    i--;
                }
            }

            // 3. Shake
            updateShake(dtMs);
            // 4. Particles
            particleSystem.update(dt);

            // 5. Magnet Effect
            // 5. Magnet Effect (Repel hazards, Attract pizza/beer - smart combo mode when combo >= 2)
            if (activePowerups.magnet.active) {
                items.forEach(item => {
                    if (!item.collected) {
                        const dx = bird.x - item.x;
                        const dy = bird.y - item.y;
                        const dist = Math.sqrt(dx * dx + dy * dy);

                        // Hazard: Always Repel
                        if (item.type === 'hazard') {
                            if (dist < 250) {
                                item.x -= (dx / dist) * 8 * dt; // Push away
                                item.y -= (dy / dist) * 8 * dt;
                            }
                        }
                        // Powerups: Ignore (do not attract)
                        else if (item.type.startsWith('powerup_')) {
                            // Do nothing
                        }
                        // Coins: Always attract
                        else if (item.type === 'coin') {
                            if (dist < 300) {
                                item.x += (dx / dist) * 12 * dt;
                                item.y += (dy / dist) * 12 * dt;
                            }
                        }
                        // Pizza/Beer: Smart attract based on combo
                        else {
                            // If combo >= 2, only attract items that maintain combo
                            const shouldAttract = combo.count >= 2
                                ? (item.type === combo.lastType)
                                : true;

                            if (shouldAttract && dist < 300) {
                                item.x += (dx / dist) * 12 * dt;
                                item.y += (dy / dist) * 12 * dt;
                            }
                        }
                    }
                });
            }

            // Game Speed with Slow Motion
            const speedMult = activePowerups.slow.active ? 0.6 : 1.0;
            const difficulty = difficultyAtLevel(currentLevel);
            gameSpeed = CONFIG.baseSpeed * difficulty.speedFactor * speedMult;

            backgroundOffset = (backgroundOffset + gameSpeed * 0.5 * dt) % 100;

            stars.forEach(s => { s.x -= s.speed * gameSpeed * dt; if (s.x < -10) s.x = logicalWidth + 10; });
            particles.forEach(p => { p.x -= p.speed * gameSpeed * dt; if (p.x < -10) p.x = logicalWidth + 10; });

            // --- BIRD PHYSICS ---
            bird.velocity += CONFIG.gravity * dt;
            bird.y += bird.velocity * dt;
            bird.rotation = clampNumber(bird.velocity * 0.09, -0.55, 0.55);

            if (bird.y + bird.radius >= logicalHeight || bird.y - bird.radius <= 0) {
                endGame();
                return;
            }

            // Safe zone: durante safe zone non spawnare tubi (ok), ma tutto il resto continua.
            if (safeZoneTimerMs > 0) {
                safeZoneTimerMs -= dtMs;
            } else {
                // Pipe timer scales with speed so visual distance stays constant
                pipeTimerMs -= dtMs * speedMult;
                if (pipeTimerMs <= 0) {
                    if (pipesSpawned > 5 && Math.random() < CONFIG.safeZoneChance) {
                        safeZoneTimerMs = CONFIG.safeZoneDurationMs;
                        pipeTimerMs = difficulty.spawnMs;
                    } else {
                        spawnPipe(difficulty.gap);
                        pipeTimerMs = difficulty.spawnMs * getPipeVariation();
                    }
                }
            }

            // Oggetti - spawn rate costante indipendente dalla velocità
            itemTimerMs -= dtMs;
            if (itemTimerMs <= 0) {
                const lastItem = items.length ? items[items.length - 1] : null;
                const cooldownOk = !lastItem || (elapsedMs - (lastItem.spawnedAtMs || 0)) >= CONFIG.itemCooldownMs;

                // Spawn rate costante: sempre 70% di probabilità
                if (cooldownOk && Math.random() < 0.70) {
                    spawnItem();
                }

                if (Math.random() < CONFIG.itemDensityChangeChance) {
                    currentDensity = Math.random() * 0.40 + 0.35;
                }

                // Timer fisso per spawn costante
                itemTimerMs = 800;
            }

            // Decorazioni
            decoTimerMs -= dtMs;
            if (decoTimerMs <= 0) {
                spawnDecoration();
                decoTimerMs = CONFIG.decoSpawnIntervalMs + (Math.random() * 5000 - 2500);
            }

            // update decorazioni
            for (let i = 0; i < decorations.length; i++) {
                decorations[i].x -= decorations[i].speed * dt;
                if (decorations[i].x < -100) { decorations.splice(i, 1); i--; }
            }

            // update pipes + collision + score
            // update pipes + collision + score
            for (let i = 0; i < pipes.length; i++) {
                const p = pipes[i];
                p.x -= gameSpeed * dt;

                // Skip destroyed pipes for collision checks (but still move them for score)
                if (p.destroyed) {
                    // Still allow scoring for passing destroyed pipes
                    if (p.x + p.width < bird.x && !p.passed) {
                        let scoreAdd = 25;
                        if (activePowerups.score_mult.active) scoreAdd *= 2;
                        score += scoreAdd;
                        p.passed = true;
                        updateScoreDisplay();
                    }
                    // Remove offscreen pipes
                    if (p.x + p.width < -100) {
                        pipes.splice(i, 1);
                        i--;
                    }
                    continue;
                }

                // Check Laser Collisions
                for (let j = 0; j < lasers.length; j++) {
                    const l = lasers[j];
                    if (!l.hit) {

                        // Check vs Top Segments
                        if (p.topSegments) {
                            for (let k = 0; k < p.topSegments.length; k++) {
                                const seg = p.topSegments[k];
                                // Hit check: Laser Rect vs Segment Rect (Expanded hitbox slightly)
                                if (l.x + l.w > p.x - 5 && l.x < p.x + p.width + 5 &&
                                    l.y + l.h > seg.y && l.y < seg.y + seg.h) {

                                    // HIT! Create hole.
                                    l.hit = true;
                                    lasers.splice(j, 1);
                                    j--;

                                    const holeSize = 90;
                                    const holeCenter = l.y + l.h / 2;
                                    const holeTop = holeCenter - holeSize / 2;
                                    const holeBottom = holeCenter + holeSize / 2;

                                    const segTop = seg.y;
                                    const segBottom = seg.y + seg.h;

                                    // Remove current segment
                                    p.topSegments.splice(k, 1);

                                    // Add new segments if they exist
                                    if (holeTop > segTop) {
                                        p.topSegments.splice(k, 0, { y: segTop, h: holeTop - segTop });
                                        k++;
                                    }
                                    if (holeBottom < segBottom) {
                                        p.topSegments.splice(k, 0, { y: holeBottom, h: segBottom - holeBottom });
                                    }

                                    particleSystem.emit(p.x + p.width / 2, holeCenter, '#FFF', 15);
                                    break;
                                }
                            }
                        }

                        if (l.hit) continue; // Laser used up

                        // Check vs Bottom Segments
                        if (p.bottomSegments) {
                            for (let k = 0; k < p.bottomSegments.length; k++) {
                                const seg = p.bottomSegments[k];
                                if (l.x + l.w > p.x - 5 && l.x < p.x + p.width + 5 &&
                                    l.y + l.h > seg.y && l.y < seg.y + seg.h) {

                                    l.hit = true;
                                    lasers.splice(j, 1);
                                    j--;

                                    const holeSize = 90;
                                    const holeCenter = l.y + l.h / 2;
                                    const holeTop = holeCenter - holeSize / 2;
                                    const holeBottom = holeCenter + holeSize / 2;

                                    const segTop = seg.y;
                                    const segBottom = seg.y + seg.h;

                                    p.bottomSegments.splice(k, 1);

                                    if (holeTop > segTop) {
                                        p.bottomSegments.splice(k, 0, { y: segTop, h: holeTop - segTop });
                                        k++;
                                    }
                                    if (holeBottom < segBottom) {
                                        p.bottomSegments.splice(k, 0, { y: holeBottom, h: segBottom - holeBottom });
                                    }

                                    particleSystem.emit(p.x + p.width / 2, holeCenter, '#FFF', 15);
                                    break;
                                }
                            }
                        }
                    }
                }

                // iOS Hitbox Fix: More forgiving on iOS
                let isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
                const precision = isIOS ? 15 : 3;
                const collisionRadius = activePowerups.tiny.active ? 9 : bird.radius;

                // Bird Collision Check against Segments
                let collided = false;

                // Check Top Segments
                if (p.topSegments) {
                    for (let seg of p.topSegments) {
                        if (bird.x + collisionRadius - precision > p.x && bird.x - collisionRadius + precision < p.x + p.width &&
                            bird.y - collisionRadius - precision < seg.y + seg.h && bird.y + collisionRadius - precision > seg.y) {
                            collided = true;
                            break;
                        }
                    }
                } else if (!p.destroyed) {
                    // Fallback for old pipes
                    if (bird.x + collisionRadius - precision > p.x && bird.x - collisionRadius + precision < p.x + p.width &&
                        bird.y - collisionRadius - precision < p.topHeight) {
                        collided = true;
                    }
                }

                // Check Bottom Segments
                if (!collided) {
                    if (p.bottomSegments) {
                        for (let seg of p.bottomSegments) {
                            if (bird.x + collisionRadius - precision > p.x && bird.x - collisionRadius + precision < p.x + p.width &&
                                bird.y - collisionRadius - precision < seg.y + seg.h && bird.y + collisionRadius - precision > seg.y) {
                                collided = true;
                                break;
                            }
                        }
                    } else if (!p.destroyed) {
                        if (bird.x + collisionRadius - precision > p.x && bird.x - collisionRadius + precision < p.x + p.width &&
                            bird.y + collisionRadius - precision > p.bottomY) {
                            collided = true;
                        }
                    }
                }

                if (collided) {
                    if (activePowerups.shield.active) {
                        // Shield active: CONSUME IT AND DESTROY PIPE
                        activePowerups.shield.active = false;
                        activePowerups.shield.timer = 0;
                        p.destroyed = true; // Mark pipe as destroyed

                        // Visual Feedback: Shield Break + Pipe Destruction
                        triggerShake(300, 15);
                        // Grey/Brown particles for pipe debris
                        particleSystem.emit(p.x + p.width / 2, bird.y, '#555555', 40, 20, 10);
                        particleSystem.emit(p.x + p.width / 2, bird.y, '#8B4513', 20, 10, 5);

                        // Audio Feedback
                        sfxCollision();

                        // Skip further collision checks for this pipe
                        continue;
                    } else if (activePowerups.ghost && activePowerups.ghost.active) {
                        // Ghost active: PASS THROUGH (Immune to pipes)
                        continue;
                    } else {
                        sfxCollision();
                        endGame();
                        return;
                    }
                }

                // Score for passing pipe
                if (p.x + p.width < bird.x && !p.passed) {
                    let scoreAdd = 25;
                    if (activePowerups.score_mult.active) scoreAdd *= 2;
                    score += scoreAdd;
                    p.passed = true;
                    updateScoreDisplay();
                }

                // Remove offscreen pipes
                if (p.x + p.width < -100) {
                    pipes.splice(i, 1);
                    i--;
                }
            }

            // update items
            for (let i = 0; i < items.length; i++) {
                const b = items[i];
                b.x -= gameSpeed * dt;

                const dx = bird.x - b.x;
                const dy = bird.y - b.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // Use current radius for item collection too (easier/harder?)
                // Usually item collection radius should be generous. Keep original bird radius or fixed range.
                if (distance < bird.radius + (b.radius || 18) && !b.collected) {
                    b.collected = true;

                    // Particle explosion
                    particleSystem.emit(b.x, b.y, b.type === 'hazard' ? '#FF5252' : (b.type === 'diamond' ? '#00FFFF' : '#FFC107'), 15);

                    if (b.type === 'diamond') {
                        // Diamond: 50 coins + epic particle burst
                        coinsCollectedThisGame += 50;
                        particleSystem.emit(b.x, b.y, '#00FFFF', 40, 20, 10);
                        particleSystem.emit(b.x, b.y, '#FF00FF', 30, 15, 8);
                        particleSystem.emit(b.x, b.y, '#FFFFFF', 20, 10, 5);
                        creaNotificaGioco('💎 DIAMANTE! +50 Monete!');
                        sfxPowerup();
                        if (vibrationEnabled) triggerVibration([100, 50, 100, 50, 100]);
                        const hudCoinEl = document.getElementById('hud-coin-count');
                        if (hudCoinEl) hudCoinEl.innerText = (typeof playerCoins !== 'undefined' ? playerCoins : 0) + coinsCollectedThisGame;
                    } else if (b.type === 'hazard' && activePowerups.shield.active) {
                        // Shield blocks hazard? Maybe not, usually blocks death.
                        // Let's say shield ONLY blocks pipes (death). Hazard reduces points.
                        score = Math.max(0, score + b.points); // Hazard points are negative
                        sfxNegative();
                        triggerShake(200, 5);
                        combo.count = 0;
                        updateMissions('hit_hazard', null);
                    } else if (b.type.startsWith('powerup_')) {
                        activatePowerup(b.type.replace('powerup_', ''));
                        updateMissions('collect', b);
                        sfxPowerup(); // Powerup sound
                    } else if (b.type === 'coin') {
                        // Coin collection - increment counter, gold particles
                        coinsCollectedThisGame++;
                        particleSystem.emit(b.x, b.y, '#FFD700', 20, 10, 5); // Gold burst
                        sfxCoinCollect();  // Coin-specific sound
                        score += b.points; // Small score bonus
                        // Update HUD coin counter in real-time
                        const hudCoinEl = document.getElementById('hud-coin-count');
                        if (hudCoinEl) hudCoinEl.innerText = (typeof playerCoins !== 'undefined' ? playerCoins : 0) + coinsCollectedThisGame;
                    } else {
                        if (b.type === 'hazard') {
                            sfxNegative();
                            combo.count = 0;
                            triggerShake(200, 5);
                            updateMissions('hit_hazard', null);
                        } else {
                            sfxPositive();
                            updateMissions('collect', b);
                            updateMissions('collect_safe', null);

                            // Combo Logic with Flame Freebie Support
                            // If flameFreebieActive is true, the first item can be any type
                            // After that, normal combo rules apply (same type only)
                            if (combo.flameFreebieActive) {
                                // Flame freebie: continue combo regardless of type, then lock
                                combo.count++;
                                combo.lastType = b.type; // Lock to this type
                                combo.flameFreebieActive = false; // Disable freebie
                            } else if (combo.lastType === b.type) {
                                combo.count++;
                            } else {
                                combo.count = 1;
                                combo.lastType = b.type;
                            }

                            combo.timer = combo.maxTime;

                            // Enhanced combo multiplier - Makes maintaining streaks worthwhile
                            let mult = 1.0;

                            if (combo.count >= 10) {
                                // Super high combos: massive rewards
                                mult = 3.0 + (combo.count - 10) * 0.3; // 10x=3.0x, 15x=4.5x, 20x=6.0x
                            } else if (combo.count >= 7) {
                                // High combos: great rewards
                                mult = 2.0 + (combo.count - 6) * 0.333; // 7x=2.33x, 8x=2.66x, 9x=3.0x
                            } else if (combo.count >= 4) {
                                // Mid combos: good rewards
                                mult = 1.5 + (combo.count - 3) * 0.25; // 4x=1.75x, 5x=2.0x, 6x=2.25x
                            } else if (combo.count >= 2) {
                                // Small combos: decent bonus
                                mult = 1.0 + (combo.count - 1) * 0.25; // 2x=1.25x, 3x=1.5x
                            }

                            if (combo.count >= 5) {
                                let cText = `${combo.count}x COMBO!`;
                                if (combo.count >= 10) cText = `🔥 ${combo.count}x SUPER COMBO! 🔥`;
                                if (combo.count >= 20) cText = `⚡ ${combo.count}x ULTRA COMBO! ⚡`;
                                creaNotificaGioco(cText);
                                sfxCombo(combo.count); // Combo sound
                                // Reduced particle burst for performance
                                particleSystem.emit(bird.x, bird.y, '#00FFFF', 5, 6, 3);
                            }

                            // Multiplier Powerup Effect on Items
                            let finalPoints = b.points * mult;
                            if (activePowerups.score_mult.active) finalPoints *= 2;

                            score += finalPoints;
                        }
                    }
                    updateScoreDisplay();
                }

                if (b.x < -100 || b.collected) {
                    items.splice(i, 1);
                    i--;
                }
            }

            score += (dtMs / 1000) * 15;
            updateScoreDisplay();

            // Update time-based missions
            const survivedSeconds = Math.floor(elapsedMs / 1000);
            updateMissions('survived', survivedSeconds);
        }

        function roundRectPath(x, y, w, h, r) {
            const radius = clampNumber(r, 0, Math.min(w, h) / 2);
            ctx.beginPath();
            ctx.moveTo(x + radius, y);
            ctx.lineTo(x + w - radius, y);
            ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
            ctx.lineTo(x + w, y + h - radius);
            ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
            ctx.lineTo(x + radius, y + h);
            ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
            ctx.lineTo(x, y + radius);
            ctx.quadraticCurveTo(x, y, x + radius, y);
            ctx.closePath();
        }

        function drawPipe(x, y, w, h, colors) {
            // Usa i colori passati come parametro (cambiano in base al livello)
            const baseGrad = ctx.createLinearGradient(x, 0, x + w, 0);
            baseGrad.addColorStop(0, colors.highlight);
            baseGrad.addColorStop(0.22, colors.base);
            baseGrad.addColorStop(0.78, colors.base);
            baseGrad.addColorStop(1, colors.dark);

            ctx.fillStyle = baseGrad;
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            roundRectPath(x, y, w, h, 10);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = 'rgba(255,255,255,0.16)';
            roundRectPath(x + 6, y + 6, Math.max(10, w * 0.22), Math.max(0, h - 12), 8);
            ctx.fill();

            ctx.fillStyle = 'rgba(0,0,0,0.14)';
            roundRectPath(x + w - 10, y + 6, 4, Math.max(0, h - 12), 6);
            ctx.fill();
        }

        function drawPipeCap(x, y, w, h, colors) {
            // Usa i colori passati come parametro (cambiano in base al livello)
            const capGrad = ctx.createLinearGradient(x, 0, x + w, 0);
            capGrad.addColorStop(0, colors.light);
            capGrad.addColorStop(0.5, colors.base);
            capGrad.addColorStop(1, colors.dark);
            ctx.fillStyle = capGrad;
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            roundRectPath(x, y, w, h, 12);
            ctx.fill();
            ctx.stroke();
        }

        function drawPipeSegment(x, y, w, h, colors) {
            const baseGrad = ctx.createLinearGradient(x, 0, x + w, 0);
            baseGrad.addColorStop(0, colors.highlight);
            baseGrad.addColorStop(0.22, colors.base);
            baseGrad.addColorStop(0.78, colors.base);
            baseGrad.addColorStop(1, colors.dark);

            ctx.fillStyle = baseGrad;
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.rect(x, y, w, h);
            ctx.fill();
            ctx.stroke();

            ctx.fillStyle = 'rgba(255,255,255,0.16)';
            ctx.fillRect(x + 6, y + 2, Math.max(10, w * 0.22), Math.max(0, h - 4));

            ctx.fillStyle = 'rgba(0,0,0,0.14)';
            ctx.fillRect(x + w - 10, y + 2, 4, Math.max(0, h - 4));
        }

        function draw() {
            // Fix trasparenza aquila: reset globale sempre
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.globalAlpha = 1.0;

            // Apply Shake
            let shakeX = 0, shakeY = 0;
            if (shakeTimer > 0) {
                shakeX = (Math.random() - 0.5) * shakeIntensity;
                shakeY = (Math.random() - 0.5) * shakeIntensity;
            }
            ctx.translate(shakeX, shakeY);

            let grad = ctx.createLinearGradient(0, 0, 0, logicalHeight);
            grad.addColorStop(0, `hsl(${bgColor.h}, ${bgColor.s}%, ${bgColor.l}%)`);
            grad.addColorStop(1, '#000000');
            ctx.fillStyle = grad;
            ctx.fillRect(-shakeX, -shakeY, logicalWidth, logicalHeight);

            // Layer Parallasse 1: Stars
            ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
            stars.forEach(s => {
                ctx.beginPath();
                ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
                ctx.fill();
            });

            // Layer Parallasse 2: Particles
            ctx.fillStyle = 'rgba(255, 193, 7, 0.15)';
            particles.forEach(p => {
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
            });

            // Draw Lasers
            ctx.fillStyle = '#00FFFF'; // Cyan lasers
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#00FFFF';
            lasers.forEach(l => {
                ctx.fillRect(l.x, l.y, l.w, l.h);
            });
            ctx.shadowBlur = 0;

            // Layer Decorativo (Cloud/Space objects) - sempre su canvas per stare dietro i tubi
            ctx.font = "30px 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif";
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            decorations.forEach(d => {
                ctx.globalAlpha = 0.3;
                ctx.fillText(d.icon, d.x, d.y);
                ctx.globalAlpha = 1.0;
            });
            // Ensure alpha is reset after decorations loop (even if empty)
            ctx.globalAlpha = 1.0;

            // Draw dynamic grid pattern (Yellow/Black)
            ctx.strokeStyle = 'rgba(255, 193, 7, 0.05)';
            ctx.lineWidth = 1;
            const gridSize = 60;
            const xShift = -backgroundOffset;

            for (let x = xShift; x < logicalWidth; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, logicalHeight);
                ctx.stroke();
            }
            for (let y = 0; y < logicalHeight; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(logicalWidth, y);
                ctx.stroke();
            }

            // Safe Zone Indicator
            if (CONFIG.showSafeZoneOverlay && safeZoneTimerMs > 0) {
                ctx.fillStyle = 'rgba(255, 193, 7, 0.03)';
                ctx.fillRect(0, 0, logicalWidth, logicalHeight);

                ctx.fillStyle = 'rgba(255, 193, 7, 0.4)';
                ctx.font = "bold 20px Oswald";
                ctx.textAlign = "center";
                ctx.fillText("SAFE ZONE", logicalWidth / 2, 40);
            }

            // Ottieni i colori per il livello corrente
            const pipeColors = getPipeColorsForLevel(currentLevel);

            for (let p of pipes) {
                // Skip destroyed pipes entirely
                if (p.destroyed) continue;

                // Draw Top Segments
                if (p.topSegments) {
                    p.topSegments.forEach(seg => {
                        drawPipeSegment(p.x, seg.y, p.width, seg.h, pipeColors);
                    });
                } else if (!p.destroyed) {
                    // Fallback
                    drawPipe(p.x, 0, p.width, p.topHeight, pipeColors);
                    drawPipeCap(p.x - 4, p.topHeight - 22, p.width + 8, 22, pipeColors);
                }

                // Draw Bottom Segments
                if (p.bottomSegments) {
                    p.bottomSegments.forEach(seg => {
                        drawPipeSegment(p.x, seg.y, p.width, seg.h, pipeColors);
                    });
                } else if (!p.destroyed) {
                    // Fallback
                    drawPipe(p.x, p.bottomY, p.width, logicalHeight - p.bottomY, pipeColors);
                    drawPipeCap(p.x - 4, p.bottomY, p.width + 8, 22, pipeColors);
                }

                // Draw Caps (Simple logic: if segment ends near pipe 'mouth', draw cap)
                // Caps are: Bottom of Top Pipe, Top of Bottom Pipe.
                if (p.topSegments) {
                    const lastTopSeg = p.topSegments.find(s => Math.abs((s.y + s.h) - p.topHeight) < 5);
                    if (lastTopSeg) {
                        drawPipeCap(p.x - 4, lastTopSeg.y + lastTopSeg.h - 22, p.width + 8, 22, pipeColors);
                    }
                } else if (!p.destroyed) {
                    // Already drawn in fallback
                }

                if (p.bottomSegments) {
                    const firstBotSeg = p.bottomSegments.find(s => Math.abs(s.y - p.bottomY) < 5);
                    if (firstBotSeg) {
                        drawPipeCap(p.x - 4, firstBotSeg.y, p.width + 8, 22, pipeColors);
                    }
                } else if (!p.destroyed) {
                    // Already drawn in fallback
                }


                if (CONFIG.debug) {
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 1;
                    if (p.topSegments) {
                        p.topSegments.forEach(s => ctx.strokeRect(p.x, s.y, p.width, s.h));
                        p.bottomSegments.forEach(s => ctx.strokeRect(p.x, s.y, p.width, s.h));
                    } else if (!p.destroyed) {
                        ctx.strokeRect(p.x + 4, 0, p.width - 8, p.topHeight - 4);
                        ctx.strokeRect(p.x + 4, p.bottomY + 4, p.width - 8, logicalHeight - p.bottomY - 4);
                    }
                }
            }

            if (!USE_DOM_EMOJI) {
                ctx.font = "32px 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                for (let b of items) {
                    if (!b.collected) {
                        ctx.save();
                        ctx.shadowBlur = 15;
                        ctx.shadowColor = b.type === 'hazard' ? 'rgba(255,0,0,0.5)' : 'rgba(255,193,7,0.5)';
                        ctx.fillText(b.icon, b.x, b.y);

                        if (CONFIG.debug) {
                            ctx.beginPath();
                            ctx.arc(b.x, b.y, (b.radius || 18), 0, Math.PI * 2);
                            ctx.strokeStyle = 'cyan';
                            ctx.stroke();
                        }
                        ctx.restore();
                    }
                }
            }

            // Draw Particles
            particleSystem.draw(ctx);

            // Ghost transparency: bird at 0.7 opacity when ghost is active (less transparent)
            // Note: Shield does NOT modify this, so shield keeps it 1.0 unless ghost is also active
            ctx.globalAlpha = (activePowerups.ghost && activePowerups.ghost.active) ? 0.7 : 1.0;
            ctx.save();
            ctx.translate(bird.x, bird.y);

            // Tiny Mode Scaling
            if (activePowerups.tiny.active) {
                ctx.scale(0.5, 0.5); // 50% size
            }

            ctx.rotate(bird.rotation);
            ctx.scale(-1, 1);

            // Shield Aura
            if (activePowerups.shield.active) {
                ctx.beginPath();
                ctx.arc(0, 0, bird.radius + 15, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(0, 255, 255, ${0.5 + Math.sin(Date.now() / 100) * 0.3})`;
                ctx.lineWidth = 4;
                ctx.stroke();
                ctx.fillStyle = `rgba(0, 255, 255, 0.1)`;
                ctx.fill();
            }

            // Ghost Aura
            if (activePowerups.ghost && activePowerups.ghost.active) {
                // Ghost aura less transparent
                ctx.globalAlpha = 0.7;
                ctx.beginPath();
                ctx.arc(0, 0, bird.radius + 12, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(138, 43, 226, ${0.7 + Math.sin(Date.now() / 150) * 0.3})`;
                ctx.lineWidth = 3;
                ctx.stroke();
                ctx.fillStyle = `rgba(138, 43, 226, 0.2)`;
                ctx.fill();
            }

            if (!USE_DOM_EMOJI) {
                ctx.font = "42px 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif";
                ctx.shadowColor = "rgba(0,0,0,0.6)";
                ctx.shadowBlur = 12;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(SKINS[selectedSkin] || EAGLE_ICON, 0, 0);
            }

            if (CONFIG.debug) {
                ctx.beginPath();
                ctx.arc(0, 0, bird.radius, 0, Math.PI * 2);
                ctx.strokeStyle = 'lime';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
            ctx.restore();

            // DOM emoji overlay (iOS canvas emoji workaround)
            updateDomEmojiLayer(shakeX, shakeY);

            // Draw Notifications
            gameNotifications.forEach((n, i) => {
                n.life -= 0.016;
                n.y -= 0.5;
                ctx.globalAlpha = Math.min(1, n.life);
                ctx.fillStyle = '#FFC107';
                ctx.font = 'bold 24px Oswald';
                ctx.fillText(n.text, logicalWidth / 2, n.y);
                ctx.globalAlpha = 1.0;
                if (n.life <= 0) gameNotifications.splice(i, 1);
            });

            // Draw Active Powerups (HUD) - Left side below score
            // Position further down to avoid overlap with score/level on iPhone
            let powerupHudY = 170 + (typeof safeAreaTop !== 'undefined' ? safeAreaTop : 0);
            ctx.textAlign = 'left';
            for (let key in activePowerups) {
                if (activePowerups[key].active) {
                    const secs = activePowerups[key].timer / 1000;
                    const timeStr = secs >= 1 ? Math.ceil(secs) + 's' : secs.toFixed(1) + 's';
                    ctx.fillStyle = '#fff';
                    ctx.font = "bold 16px Oswald";
                    ctx.fillText(`${activePowerups[key].icon} ${timeStr}`, 20, powerupHudY);
                    powerupHudY += 22;
                }
            }

            if (combo.count > 1) {
                const comboX = logicalWidth - 20;
                const comboY = 175;

                // Simplified pulse effect (no expensive Date.now calls per frame)
                const comboScale = combo.count >= 10 ? 1.15 : (combo.count >= 5 ? 1.08 : 1.0);

                ctx.save();
                // Glow effect (reduced blur for performance)
                ctx.shadowBlur = combo.count >= 5 ? 12 : 6;
                ctx.shadowColor = combo.count >= 10 ? '#FF0000' : (combo.count >= 5 ? '#FF6600' : '#FF5252');

                // Streak Item Icon (pizza or beer)
                const streakIcon = combo.lastType === 'pizza' ? '🍕' : (combo.lastType === 'beer' ? '🍺' : '');

                // Background pill
                const pillWidth = 110;
                const pillHeight = 38;
                const pillX = comboX - pillWidth;
                const pillY = comboY - 26;
                const pillCenterX = pillX + pillWidth / 2;
                const pillCenterY = pillY + pillHeight / 2;

                ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
                ctx.beginPath();
                ctx.roundRect(pillX, pillY, pillWidth, pillHeight, 19);
                ctx.fill();

                // Color based on combo level
                if (combo.count >= 20) {
                    ctx.fillStyle = '#FFD700'; // Gold
                } else if (combo.count >= 10) {
                    ctx.fillStyle = '#FF4444'; // Bright red
                } else if (combo.count >= 5) {
                    ctx.fillStyle = '#FF8800'; // Orange
                } else {
                    ctx.fillStyle = '#FF5252'; // Default red
                }

                // Draw content centered in pill: [emoji] [Nx]
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                // Streak icon on left side of center
                if (streakIcon) {
                    ctx.font = '22px sans-serif';
                    ctx.fillText(streakIcon, pillCenterX - 25, pillCenterY);
                }

                // Combo number on right side of center
                ctx.font = `bold ${Math.floor(24 * comboScale)}px Oswald`;
                ctx.fillText(`${combo.count}x`, pillCenterX + 20, pillCenterY);

                ctx.restore();
            }

            // Debug Stats
            if (CONFIG.debug) {
                ctx.fillStyle = 'lime';
                ctx.font = '12px monospace';
                ctx.textAlign = 'left';
                ctx.fillText(`LEVEL: ${currentLevel}`, 20, 80);
                ctx.fillText(`SPEED: ${gameSpeed.toFixed(2)}`, 20, 100);
                ctx.fillText(`ELAPSED: ${(elapsedMs / 1000).toFixed(1)}s`, 20, 120);
                ctx.fillText(`SAFE: ${safeZoneTimerMs > 0 ? (safeZoneTimerMs / 1000).toFixed(1) : 'OFF'}`, 20, 140);
                ctx.fillText(`PIPES: ${pipesSpawned}`, 20, 160);
            }
        }

        function loop(timestamp) {
            if (!isPlaying) return;
            if (!lastTime) lastTime = timestamp;
            const dtMs = Math.min(35, timestamp - lastTime);
            lastTime = timestamp;
            update(dtMs);
            draw();
            requestAnimationFrame(loop);
        }

        // EXPOSE - Esponi funzioni al window per onclick inline
        window.startGameEngine = startGame;
        window.resetGameEngine = resetGame;

        // === SKIN UNLOCK CELEBRATION ===
        function showSkinUnlock(skinEmoji, skinName) {
            // Crea container particelle
            const particleContainer = document.createElement('div');
            particleContainer.className = 'particle-container';
            document.body.appendChild(particleContainer);

            // Genera confetti
            const colors = ['#FFC107', '#FF5722', '#4CAF50', '#2196F3', '#9C27B0', '#E91E63'];
            for (let i = 0; i < 50; i++) {
                const confetti = document.createElement('div');
                confetti.className = 'confetti';
                confetti.style.left = Math.random() * 100 + '%';
                confetti.style.top = '-20px';
                confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.animationDelay = Math.random() * 0.5 + 's';
                confetti.style.animationDuration = (1.5 + Math.random()) + 's';
                particleContainer.appendChild(confetti);
            }

            // Genera particelle circolari
            for (let i = 0; i < 30; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = (40 + Math.random() * 20) + '%';
                particle.style.top = (40 + Math.random() * 20) + '%';
                particle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                particle.style.animationDelay = Math.random() * 0.3 + 's';
                particleContainer.appendChild(particle);
            }

            // Crea overlay celebrazione
            const overlay = document.createElement('div');
            overlay.className = 'skin-unlock-overlay';
            overlay.innerHTML = `
                <div class="unlock-emoji">${skinEmoji}</div>
                <div class="unlock-text">🎉 ${skinName} SBLOCCATA! 🎉</div>
            `;
            document.body.appendChild(overlay);

            // Vibrazione (se supportata)
            if (navigator.vibrate) {
                navigator.vibrate([100, 50, 100, 50, 200]);
            }

            // Rimuovi dopo 2.5 secondi
            setTimeout(() => {
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 0.5s';
                setTimeout(() => {
                    overlay.remove();
                    particleContainer.remove();
                }, 500);
            }, 2500);
        }

        // Esponi funzione per uso globale
        window.showSkinUnlock = showSkinUnlock;

    

        // EXPORTS AUTOMATICI - esponi tutte le funzioni per onclick HTML
        window.activatePowerup = activatePowerup;
        window.bindUi = bindUi;
        window.buyShopItem = buyShopItem;
        window.checkRequirements = checkRequirements;
        window.clampNumber = clampNumber;
        window.cleanOldMissionKeys = cleanOldMissionKeys;
        window.creaNotificaGioco = creaNotificaGioco;
        window.difficultyAtLevel = difficultyAtLevel;
        window.drawPipe = drawPipe;
        window.drawPipeCap = drawPipeCap;
        window.drawPipeSegment = drawPipeSegment;
        window.endGame = endGame;
        window.equipPreviewedSkin = equipPreviewedSkin;
        window.findSafeSpawnPosition = findSafeSpawnPosition;
        window.getPipeColorsForLevel = getPipeColorsForLevel;
        window.getPipeVariation = getPipeVariation;
        window.hideInfoScreen = hideInfoScreen;
        window.hideLeaderboard = hideLeaderboard;
        window.hideShopScreen = hideShopScreen;
        window.hideSkinsScreen = hideSkinsScreen;
        window.initAudio = initAudio;
        window.initDailyMissions = initDailyMissions;
        window.initParallax = initParallax;
        window.isItemCollidingWithAnyPipe = isItemCollidingWithAnyPipe;
        window.isItemCollidingWithPipe = isItemCollidingWithPipe;
        window.isStartScreenVisible = isStartScreenVisible;
        window.isUiInteractiveTarget = isUiInteractiveTarget;
        window.jump = jump;
        window.playTone = playTone;
        window.resetGameEngine = resetGame;
        window.resizeCanvas = resizeCanvas;
        window.roundRectPath = roundRectPath;
        window.sfxCoinCollect = sfxCoinCollect;
        window.sfxCollision = sfxCollision;
        window.sfxCombo = sfxCombo;
        window.sfxJump = sfxJump;
        window.sfxLevelUp = sfxLevelUp;
        window.sfxNegative = sfxNegative;
        window.sfxPositive = sfxPositive;
        window.sfxPowerup = sfxPowerup;
        window.showInfoScreen = showInfoScreen;
        window.showInfoTab = showInfoTab;
        window.showLeaderboard = showLeaderboard;
        window.showShopScreen = showShopScreen;
        window.showSkinUnlock = showSkinUnlock;
        window.showSkinsScreen = showSkinsScreen;
        window.showStartScreen = showStartScreen;
        window.showToast = showToast;
        window.spawnDecoration = spawnDecoration;
        window.spawnItem = spawnItem;
        window.spawnPipe = spawnPipe;
        window.startBackgroundMusic = startBackgroundMusic;
        window.startGameEngine = startGame;
        window.stopBackgroundMusic = stopBackgroundMusic;
        window.syncProfile = syncProfile;
        window.toggleMute = toggleMute;
        window.toggleVibration = toggleVibration;
        window.triggerShake = triggerShake;
        window.triggerVibration = triggerVibration;
        window.updateHudCoins = updateHudCoins;
        window.updateMissions = updateMissions;
        window.updateMissionsUi = updateMissionsUi;
        window.updateMusicIntensity = updateMusicIntensity;
        window.updateRankChanges = updateRankChanges;
        window.updateScoreDisplay = updateScoreDisplay;
        window.updateShake = updateShake;
        window.updateShopCoinsDisplay = updateShopCoinsDisplay;
        window.updateShopItems = updateShopItems;
        window.updateSkinPreview = updateSkinPreview;
        window.updateSkinSelector = updateSkinSelector;
        window.updateStartScreenSkin = updateStartScreenSkin;
        window.updateVibrationUi = updateVibrationUi;

    // Chiama al primo avvio per DOM
    if (typeof window._updateGameDomRefs === 'function') {
        window._updateGameDomRefs(isAdminValue);
    }
};

window.onload = function() {
    var canvas = document.getElementById('gameCanvas');
    if (canvas) {
        window.currentUserId = canvas.getAttribute('data-user-id');
    }
};
