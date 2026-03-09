window.initAntiDoubleSubmit = function () {
    'use strict';

    // Seleziona tutti i form nella pagina
    const forms = document.querySelectorAll('form');

    forms.forEach(function (form) {
        // Rimuovi listener precedentemente attaccato
        const newForm = form.cloneNode(true);
        form.parentNode.replaceChild(newForm, form);

        newForm.addEventListener('submit', function (event) {
            // Trova il bottone di submit (può essere button[type="submit"] o input[type="submit"])
            const submitBtn = newForm.querySelector('button[type="submit"], input[type="submit"]');

            if (submitBtn && !submitBtn.disabled) {
                // Salva la larghezza originale per evitare layout shift
                const originalWidth = submitBtn.offsetWidth;
                submitBtn.style.minWidth = originalWidth + 'px';

                // Disabilita il pulsante per prevenire click multipli
                submitBtn.disabled = true;

                // Salva il contenuto originale per poterlo ripristinare in caso di errore client-side
                const originalContent = submitBtn.innerHTML;
                submitBtn.dataset.originalContent = originalContent;

                // Mostra spinner animato e testo "Attendere..."
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    <span>Attendere...</span>
                `;

                // Aggiungi una classe per stile aggiuntivo (opzionale)
                submitBtn.classList.add('submitting');

                // Ripristina il pulsante dopo un timeout (fallback per errori imprevisti)
                // Solo se la pagina non viene ricaricata (submit va a buon fine)
                setTimeout(function () {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = submitBtn.dataset.originalContent || originalContent;
                        submitBtn.classList.remove('submitting');
                    }
                }, 10000); // 10 secondi di timeout
            }
        });
    });
};
