window.initCalendario = function () {
    // === SETUP MODAL GESTIONE TURNO ===
    const manageModal = document.getElementById('manageTurnoModal');
    let lastModalTrigger = null;

    if (manageModal && !manageModal.dataset.spaBound) {
        manageModal.dataset.spaBound = 'true';

        manageModal.addEventListener('show.bs.modal', function (event) {
            lastModalTrigger = event.relatedTarget || lastModalTrigger;
            const button = event.relatedTarget;
            if (!button) return;

            const dateStr = button.getAttribute('data-date');
            const typeSuggestion = button.getAttribute('data-type');
            const weekday = parseInt(button.getAttribute('data-weekday'), 10);

            const hasPizza = button.getAttribute('data-has-pizza') === 'true';
            const hasBirra = button.getAttribute('data-has-birra') === 'true';
            const pizzaAssignedStr = button.getAttribute('data-pizza-assigned');
            const birraAssignedStr = button.getAttribute('data-birra-assigned');

            document.getElementById('modalDateInput').value = dateStr;
            const dateDisplay = document.getElementById('modalDateDisplay');
            if (dateDisplay) dateDisplay.textContent = dateStr;

            const select = document.getElementById('modalTypeSelect');
            if (select) {
                // Imposta il tipo suggerito
                if (typeSuggestion && select.querySelector(`option[value="${typeSuggestion}"]`)) {
                    select.value = typeSuggestion;
                } else {
                    // Se non c'è un tipo suggerito, default in base al giorno
                    if (weekday === 1 && select.querySelector('option[value="birra"]')) {
                        select.value = 'birra';
                    } else if (weekday === 2 && select.querySelector('option[value="pizza"]')) {
                        select.value = 'pizza';
                    } else {
                        select.selectedIndex = 0;
                    }
                }

                // Funzione per aggiornare i checkbox in base al tipo selezionato
                const updateCheckboxes = function () {
                    const selectedType = select.value;
                    const checkboxes = document.querySelectorAll('input[name="user_ids"]');
                    checkboxes.forEach(cb => cb.checked = false);

                    let assignedStr = '';
                    if (selectedType === 'pizza' && hasPizza) {
                        assignedStr = pizzaAssignedStr || '';
                    } else if (selectedType === 'birra' && hasBirra) {
                        assignedStr = birraAssignedStr || '';
                    }

                    if (assignedStr && assignedStr.trim() !== '') {
                        const ids = assignedStr.split(',').filter(id => id && id.trim() !== '');
                        ids.forEach(id => {
                            if (id) {
                                const cb = document.getElementById('chk_' + id.trim());
                                if (cb) cb.checked = true;
                            }
                        });
                    }
                };

                // Aggiorna checkbox al caricamento e quando cambia il tipo (ma attacchiamo l'evento una volta sola)
                updateCheckboxes();
                if (!select.dataset.listenerBound) {
                    select.dataset.listenerBound = 'true';
                    select.addEventListener('change', updateCheckboxes);
                }
            }
        });

        // Quando il modal si chiude, riporta il focus al trigger (evita warning aria-hidden).
        manageModal.addEventListener('hide.bs.modal', function () {
            try {
                const active = document.activeElement;
                if (active && manageModal.contains(active) && typeof active.blur === 'function') {
                    active.blur();
                }
            } catch (e) { }
        });

        manageModal.addEventListener('hidden.bs.modal', function () {
            try {
                if (lastModalTrigger && typeof lastModalTrigger.focus === 'function') {
                    lastModalTrigger.focus();
                } else {
                    if (document.activeElement && document.activeElement.blur) {
                        document.activeElement.blur();
                    }
                }
            } catch (e) { }
        });

        // Se il form viene inviato senza click su un bottone (es. tasto Enter), default 'assign'
        const turnoForm = document.querySelector('#manageTurnoModal form');
        if (turnoForm && !turnoForm.dataset.listenerBound) {
            turnoForm.dataset.listenerBound = 'true';
            turnoForm.addEventListener('submit', function (e) {
                if (e.submitter && e.submitter.name === 'action') return;
                if (turnoForm.querySelector('input[name="action"]')) return;

                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'action';
                hidden.value = 'assign';
                turnoForm.appendChild(hidden);
            });
        }
    }
};
