// ========================================
// 🚀 ANIMAZIONI INTERATTIVE AVANZATE
// ========================================

window.initAnimations = function () {

    // === SCROLL-BASED FADE IN ANIMATION ===
    const observerOptions = {
        threshold: 0.15,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                // Unobserve dopo l'animazione per performance
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Applica animazione fade-in solo agli elementi visibili nella pagina.
    // Gli elementi dentro i modal partono nascosti e con l'observer resterebbero a opacity: 0.
    document.querySelectorAll('.card, .list-group-item').forEach((el, index) => {
        if (el.closest('.modal')) {
            el.classList.remove('fade-in-up');
            el.classList.add('visible');
            el.style.transitionDelay = '0s';
            return;
        }

        el.classList.add('fade-in-up');
        // Delay ridotto: massimo 0.4s anche con 40+ elementi
        el.style.transitionDelay = `${Math.min(index * 0.01, 0.4)}s`;
        observer.observe(el);
    });

    // === HEART LIKE ANIMATION ===
    document.addEventListener('click', (e) => {
        const likeBtn = e.target.closest('.btn-like, .like-button, [data-action="like"]');
        if (likeBtn) {
            const icon = likeBtn.querySelector('.bi-heart-fill, .bi-heart');
            if (icon) {
                icon.classList.add('heart-liked');
                setTimeout(() => icon.classList.remove('heart-liked'), 400);
            }
        }
    });

    // === RIPPLE EFFECT ON BUTTONS ===
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function (e) {
            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');

            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255, 255, 255, 0.5)';
            ripple.style.pointerEvents = 'none';
            ripple.style.animation = 'ripple-animation 0.6s ease-out';

            this.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        });
    });

    // === LAZY IMAGE LOADING WITH FADE ===
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.classList.add('loading');

                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }

                img.addEventListener('load', () => {
                    img.classList.remove('loading');
                    img.classList.add('loaded');
                });

                imageObserver.unobserve(img);
            }
        });
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });

    // === SMOOTH COUNTER ANIMATION ===
    const animateCounter = (element, target, duration = 1000) => {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const updateCounter = () => {
            current += increment;
            if (current < target) {
                element.textContent = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = target;
            }
        };

        updateCounter();
    };

    // Applica counter animation a elementi con classe .counter
    document.querySelectorAll('.counter[data-target]').forEach(counter => {
        const target = parseInt(counter.dataset.target);
        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(counter, target);
                    counterObserver.unobserve(counter);
                }
            });
        });
        counterObserver.observe(counter);
    });

    // === ENHANCED DROPDOWN ANIMATIONS ===
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const menu = toggle.nextElementSibling;
            if (menu && menu.classList.contains('dropdown-menu')) {
                menu.style.transformOrigin = 'top center';
            }
        });
    });

    // === TOAST NOTIFICATION ENHANCEMENT ===
    const showToast = (message, type = 'info', duration = 3000) => {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">${message}</div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                    </div>
                `;

        const container = document.getElementById('toast-container') || document.body;
        container.appendChild(toast);

        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    };

    // Esponi showToast globalmente
    window.showToast = showToast;

    // === PROGRESS BAR ANIMATION ===
    const progressBars = document.querySelectorAll('.progress-bar');
    const progressObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const bar = entry.target;
                const width = bar.getAttribute('aria-valuenow') || bar.style.width;
                bar.style.width = '0%';

                setTimeout(() => {
                    bar.style.width = width + (width.includes('%') ? '' : '%');
                }, 100);

                progressObserver.unobserve(bar);
            }
        });
    });

    progressBars.forEach(bar => progressObserver.observe(bar));

    // === STAGGER ANIMATION FOR LISTS ===
    document.querySelectorAll('.stagger-container').forEach(container => {
        const items = container.children;
        Array.from(items).forEach((item, index) => {
            item.classList.add('stagger-item');
            item.style.animationDelay = `${index * 0.05}s`;
        });
    });

    // === FLOATING ELEMENTS ===
    document.querySelectorAll('[data-float]').forEach(el => {
        el.classList.add('floating');
    });

    // === SMOOTH SCROLL TO TOP ===
    const scrollToTop = () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    };

    // Aggiungi pulsante scroll to top se scorri oltre 300px
    let scrollTopBtn = document.querySelector('.scroll-to-top-btn');
    if (!scrollTopBtn) {
        scrollTopBtn = document.createElement('button');
        scrollTopBtn.className = 'btn btn-warning rounded-circle position-fixed scroll-to-top-btn';
        scrollTopBtn.style.cssText = 'bottom: 90px; right: 20px; width: 50px; height: 50px; display: none; z-index: 1000; box-shadow: 0 4px 12px rgba(255,193,7,0.4);';
        scrollTopBtn.innerHTML = '<i class="bi bi-arrow-up-short fs-4"></i>';
        scrollTopBtn.onclick = scrollToTop;
        document.body.appendChild(scrollTopBtn);
    }

    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            scrollTopBtn.style.display = 'block';
            scrollTopBtn.style.animation = 'fade-in-up 0.3s ease-out';
        } else {
            scrollTopBtn.style.display = 'none';
        }
    });

    // === PARALLAX EFFECT (subtle) ===
    window.addEventListener('scroll', () => {
        const parallaxElements = document.querySelectorAll('[data-parallax]');
        parallaxElements.forEach(el => {
            const speed = el.dataset.parallax || 0.5;
            const yPos = -(window.scrollY * speed);
            el.style.transform = `translateY(${yPos}px)`;
        });
    });

    // === ENHANCED MODAL ANIMATIONS ===
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('show.bs.modal', function () {
            this.querySelector('.modal-dialog').style.transform = 'scale(0.8) translateY(-50px)';
        });

        modal.addEventListener('shown.bs.modal', function () {
            this.querySelector('.modal-dialog').style.transform = 'scale(1) translateY(0)';
        });
    });

    // === CONSOLE EASTER EGG ===
    console.log(
        '%c🦅 GS ARTIGLIO APP',
        'font-size: 24px; font-weight: bold; color: #FFC107; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'
    );
    console.log(
        '%cUI Enhanced ✨',
        'font-size: 14px; color: #4CAF50; font-weight: bold;'
    );

};

// === CSS ANIMATION KEYFRAMES INJECTION ===
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple-animation {
        from {
            transform: scale(0);
            opacity: 1;
        }
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
