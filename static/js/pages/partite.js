window.initPartite = function () {
    const deleteButtons = document.querySelectorAll('.confirm-delete-match');
    deleteButtons.forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function (event) {
            const message = this.dataset.confirmMessage || 'Confermi l\'eliminazione?';
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // --- Gestione dinamica del selector Indirizzo/Trasferta ---
    const locSelector = document.getElementById('locationSelector');
    if (locSelector && !locSelector.dataset.spaBound) {
        locSelector.dataset.spaBound = 'true';
        locSelector.addEventListener('change', function () {
            const isTrasferta = this.value === 'trasferta';
            document.getElementById('addressDiv').style.display = isTrasferta ? 'block' : 'none';
        });
    }

    // --- Inizializzazione modale modifica ---
    const editModal = document.getElementById('editMatchModal');
    if (editModal && !editModal.dataset.spaBound) {
        editModal.dataset.spaBound = 'true';
        editModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            document.getElementById('editId').value = button.getAttribute('data-id');
            document.getElementById('editOpponent').value = button.getAttribute('data-opponent');
            document.getElementById('editLocation').value = button.getAttribute('data-location');
            document.getElementById('editHome').value = button.getAttribute('data-home');
            document.getElementById('editDate').value = button.getAttribute('data-date');
            document.getElementById('editTime').value = button.getAttribute('data-time');

            const isFriendly = button.getAttribute('data-friendly') === 'true';
            document.getElementById('editFriendlySwitch').checked = isFriendly;
        });
    }
};
