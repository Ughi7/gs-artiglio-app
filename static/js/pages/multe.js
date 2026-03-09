window.initMulte = function () {

    document.querySelectorAll('.confirm-submit').forEach((form) => {
        if (form.dataset.spaBound) return;
        form.dataset.spaBound = 'true';
        form.addEventListener('submit', function (event) {
            const message = this.dataset.confirmMessage || 'Confermi l\'operazione?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll('.confirm-click').forEach((element) => {
        if (element.dataset.spaBound) return;
        element.dataset.spaBound = 'true';
        element.addEventListener('click', function (event) {
            const message = this.dataset.confirmMessage || 'Confermi l\'operazione?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    function navigateMulteWithFilters() {
        const personFilter = document.getElementById('personFilter');
        if (!personFilter) return;

        const urlParams = new URLSearchParams(window.location.search);
        const currentMonth = urlParams.get('month') || 'all';
        const personId = personFilter.value;
        const newUrl = `/multe?month=${currentMonth}&person=${personId}`;

        if (typeof window.navigateTo === 'function') {
            window.navigateTo(newUrl);
        } else {
            window.location.href = newUrl;
        }
    }

    function toggleHiddenItems(items, btn, label) {
        if (!items.length) return;

        const isHidden = items[0].classList.contains('d-none');
        items.forEach(el => el.classList.toggle('d-none', !isHidden));

        btn.innerHTML = isHidden
            ? '<i class="bi bi-chevron-up me-1"></i><span>Nascondi</span>'
            : `<i class="bi bi-chevron-down me-1"></i><span>${label}</span>`;
    }

    // === SETUP MODAL PAGA MULTA ===
    const payFineModal = document.getElementById('payFineModal');
    if (payFineModal && !payFineModal.dataset.spaBound) {
        payFineModal.dataset.spaBound = 'true';
        payFineModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const fineId = button.getAttribute('data-id');
            const playerName = button.getAttribute('data-giocatore');

            document.getElementById('payGiocatoreDisplay').textContent = playerName;
            document.getElementById('payFormContanti').action = '/paga_multa/' + fineId;
            document.getElementById('payFormPaypal').action = '/paga_multa/' + fineId;
        });
    }

    // === SETUP MODAL MODIFICA MULTA ===
    const editFineModal = document.getElementById('editFineModal');
    const editPaidCheckbox = document.getElementById('editPaid');
    const editPaymentMethodSection = document.getElementById('editPaymentMethodSection');
    const editMethodCash = document.getElementById('editMethodCash');
    const editMethodPaypal = document.getElementById('editMethodPaypal');

    function togglePaymentMethod() {
        if (editPaidCheckbox && editPaymentMethodSection) {
            editPaymentMethodSection.style.display = editPaidCheckbox.checked ? 'block' : 'none';
        }
    }

    if (editPaidCheckbox && !editPaidCheckbox.dataset.spaBound) {
        editPaidCheckbox.dataset.spaBound = 'true';
        editPaidCheckbox.addEventListener('change', togglePaymentMethod);
    }

    if (editFineModal && !editFineModal.dataset.spaBound) {
        editFineModal.dataset.spaBound = 'true';
        editFineModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;

            document.getElementById('editFineId').value = button.getAttribute('data-id');
            document.getElementById('editGiocatoreDisplay').textContent = button.getAttribute('data-giocatore');
            document.getElementById('editAmount').value = button.getAttribute('data-amount');
            document.getElementById('editReason').value = button.getAttribute('data-reason');

            const isPaid = button.getAttribute('data-paid') === 'true';
            if (editPaidCheckbox) editPaidCheckbox.checked = isPaid;

            const paymentMethod = button.getAttribute('data-payment-method');
            if (paymentMethod === 'paypal' && editMethodPaypal) {
                editMethodPaypal.checked = true;
            } else if (editMethodCash) {
                editMethodCash.checked = true;
            }

            togglePaymentMethod();
        });
    }

    // === SETUP MODAL TRANSAZIONI (ENTRATA/USCITA) ===
    const addTransactionModal = document.getElementById('addTransactionModal');
    if (addTransactionModal && !addTransactionModal.dataset.spaBound) {
        addTransactionModal.dataset.spaBound = 'true';
        addTransactionModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            const type = button.getAttribute('data-type') || 'uscita';

            const modalContent = document.getElementById('transactionModalContent');
            const modalIcon = document.getElementById('transactionModalIcon');
            const modalTitle = document.getElementById('transactionModalTitleText');
            const typeInput = document.getElementById('transactionTypeInput');
            const submitBtn = document.getElementById('transactionSubmitBtn');
            const descPlaceholder = document.getElementById('transactionDescriptionPlaceholder');

            if (type === 'entrata') {
                modalContent.className = 'modal-content bg-dark text-white border-success';
                modalIcon.className = 'bi bi-plus-circle me-2';
                modalTitle.textContent = 'Registra Entrata';
                modalTitle.className = 'text-success';
                typeInput.value = 'entrata';
                submitBtn.className = 'btn btn-success';
                submitBtn.textContent = 'Registra Entrata';
                descPlaceholder.placeholder = 'Es: Sponsorizzazione, Donazione';
            } else {
                modalContent.className = 'modal-content bg-dark text-white border-danger';
                modalIcon.className = 'bi bi-dash-circle me-2';
                modalTitle.textContent = 'Registra Uscita';
                modalTitle.className = 'text-danger';
                typeInput.value = 'uscita';
                submitBtn.className = 'btn btn-danger';
                submitBtn.textContent = 'Registra Uscita';
                descPlaceholder.placeholder = 'Es: Acquisto palloni';
            }
        });
    }

    // === TOGGLE CLASSIFICA STORICO ===
    const btnMostraSanzioni = document.getElementById('btnMostraSanzioni');
    if (btnMostraSanzioni && !btnMostraSanzioni.dataset.spaBound) {
        btnMostraSanzioni.dataset.spaBound = 'true';
        btnMostraSanzioni.addEventListener('click', function () {
            const total = this.dataset.total || '0';
            toggleHiddenItems(document.querySelectorAll('.sanzione-hidden'), this, `Mostra tutte (${total})`);
        });
    }

    const btnMostraRegistro = document.getElementById('btnMostraRegistro');
    if (btnMostraRegistro && !btnMostraRegistro.dataset.spaBound) {
        btnMostraRegistro.dataset.spaBound = 'true';
        btnMostraRegistro.addEventListener('click', function () {
            const total = this.dataset.total || '0';
            toggleHiddenItems(document.querySelectorAll('.registro-hidden'), this, `Mostra tutte (${total})`);
        });
    }

    document.querySelectorAll('.classifica-toggle-btn').forEach(button => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            const listId = this.dataset.targetList;
            const total = this.dataset.total || '0';
            const list = document.getElementById(listId);
            if (!list) return;

            toggleHiddenItems(list.querySelectorAll('.classifica-hidden'), this, `Mostra tutti (${total})`);
        });
    });

    // === FILTRO PER PERSONA ===
    const personFilterSelect = document.getElementById('personFilter');
    if (personFilterSelect && !personFilterSelect.dataset.spaBound) {
        personFilterSelect.dataset.spaBound = 'true';
        personFilterSelect.addEventListener('change', function () {
            navigateMulteWithFilters();
        });
    }

    // === ANIMAZIONE CONTATORE SALDO ===
    const saldoCounter = document.getElementById('total-cash-display');
    if (saldoCounter && !saldoCounter.dataset.animated) {
        saldoCounter.dataset.animated = 'true';
        const targetStr = saldoCounter.getAttribute('data-target');
        const target = parseFloat(targetStr) || 0;

        const duration = 1800;
        const startTime = performance.now();

        function animateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const ease = 1 - Math.pow(1 - progress, 3);
            const current = target * ease;

            saldoCounter.innerText = current.toFixed(2);

            if (progress < 1) {
                requestAnimationFrame(animateCounter);
            } else {
                saldoCounter.innerText = target.toFixed(2);
            }
        }

        requestAnimationFrame(animateCounter);
    }

};
