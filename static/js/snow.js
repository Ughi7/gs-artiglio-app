(function () {
    const now = new Date();
    const month = now.getMonth() + 1; // 1-12
    // Neve attiva da Dicembre a Febbraio
    const showSnow = (month === 12 || month === 1 || month === 2);

    if (!showSnow) return;

    // Controllo performance: disabilita su dispositivi con poca RAM o in battery saver
    const isLowPerf = navigator.deviceMemory && navigator.deviceMemory < 4;
    const preferReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (isLowPerf || preferReducedMotion) {
        console.log('[NEVE] Disabilitata per performance/accessibilità');
        return;
    }

    const snowCanvas = document.createElement('canvas');
    snowCanvas.id = 'snow-overlay';
    // GPU acceleration con will-change e transform
    snowCanvas.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 9999; will-change: transform; transform: translateZ(0);';
    document.body.appendChild(snowCanvas);

    const canvas = document.getElementById('snow-overlay');
    const ctx = canvas.getContext('2d', { alpha: true });
    let width, height;
    let snowflakes = [];
    let animationId = null;
    let lastFrameTime = 0;
    const targetFPS = 30; // Throttle a 30fps invece di 60fps (risparmio ~50% CPU)
    const frameInterval = 1000 / targetFPS;

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }

    function initSnowflakes() {
        // Ridotto da 30 a 18 fiocchi (ancora visivamente gradevole, molto più leggero)
        const count = 18;
        snowflakes = [];
        for (let i = 0; i < count; i++) {
            snowflakes.push({
                x: Math.random() * width,
                y: Math.random() * height,
                r: Math.random() * 2.5 + 1, // Leggermente più grandi per compensare
                d: Math.random() * count,
                speed: 0.3 + Math.random() * 0.3 // Velocità variabile per naturalezza
            });
        }
    }

    let angle = 0;
    function draw(timestamp) {
        // Throttling a 30fps
        const elapsed = timestamp - lastFrameTime;
        if (elapsed < frameInterval) {
            animationId = requestAnimationFrame(draw);
            return;
        }
        lastFrameTime = timestamp - (elapsed % frameInterval);

        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = "rgba(255, 255, 255, 0.7)";
        ctx.beginPath();

        angle += 0.01;
        for (let i = 0; i < snowflakes.length; i++) {
            const f = snowflakes[i];
            ctx.moveTo(f.x, f.y);
            ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2, true);

            // Movimento integrato per evitare loop separato
            f.y += f.speed + (f.r * 0.1);
            f.x += Math.sin(angle + f.d) * 0.4;

            // Reset quando esce dallo schermo
            if (f.y > height) {
                f.x = Math.random() * width;
                f.y = -10;
            }
            if (f.x > width + 5) f.x = -5;
            if (f.x < -5) f.x = width + 5;
        }
        ctx.fill();

        animationId = requestAnimationFrame(draw);
    }

    // Pausa quando tab non visibile (risparmio batteria)
    function handleVisibilityChange() {
        if (document.hidden) {
            if (animationId) {
                cancelAnimationFrame(animationId);
                animationId = null;
            }
            console.log('[NEVE] Pausa (tab nascosto)');
        } else {
            if (!animationId) {
                lastFrameTime = performance.now();
                animationId = requestAnimationFrame(draw);
                console.log('[NEVE] Ripresa');
            }
        }
    }

    window.addEventListener('resize', resize);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    resize();
    initSnowflakes();
    animationId = requestAnimationFrame(draw);
    console.log('[NEVE] ❄️ Animazione neve ottimizzata attiva (18 fiocchi @ 30fps)');
})();
