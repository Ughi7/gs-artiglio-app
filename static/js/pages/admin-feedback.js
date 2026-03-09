window.initAdminFeedback = function () {
    let currentFeedbackId = null;

    function getReplyModal() {
        const modalEl = document.getElementById('replyModal');
        if (!modalEl || typeof bootstrap === 'undefined') return null;
        return bootstrap.Modal.getOrCreateInstance(modalEl);
    }

    document.querySelectorAll('.feedback-filter-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            const filterType = this.dataset.filterType || 'all';

            document.querySelectorAll('.feedback-item').forEach((item) => {
                item.style.display = filterType === 'all' || item.dataset.type === filterType ? 'block' : 'none';
            });

            document.querySelectorAll('.feedback-filter-btn').forEach((filterButton) => {
                filterButton.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    document.querySelectorAll('.feedback-status-select').forEach((select) => {
        if (select.dataset.spaBound) return;
        select.dataset.spaBound = 'true';
        select.addEventListener('change', async function () {
            const feedbackId = this.dataset.feedbackId;
            if (!feedbackId) return;

            const response = await fetch(`/admin/feedback/${feedbackId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: this.value })
            });
            const result = await response.json();

            if (result.success) {
                if (typeof window.showToast === 'function') {
                    window.showToast('Stato aggiornato!', 'success');
                }
                return;
            }

            window.alert(`Errore: ${result.error || 'Sconosciuto'}`);
        });
    });

    document.querySelectorAll('.reply-feedback-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function () {
            currentFeedbackId = this.dataset.feedbackId || null;

            const replyField = document.getElementById('replyText');
            if (replyField) {
                replyField.value = this.dataset.currentReply || '';
            }

            const modal = getReplyModal();
            if (modal) {
                modal.show();
            }
        });
    });

    const submitReplyBtn = document.getElementById('submitReplyBtn');
    if (submitReplyBtn && !submitReplyBtn.dataset.spaBound) {
        submitReplyBtn.dataset.spaBound = 'true';
        submitReplyBtn.addEventListener('click', async function () {
            if (!currentFeedbackId) return;

            const replyField = document.getElementById('replyText');
            const reply = replyField ? replyField.value : '';

            const response = await fetch(`/admin/feedback/${currentFeedbackId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ admin_response: reply })
            });
            const result = await response.json();

            if (result.success) {
                const modal = getReplyModal();
                if (modal) modal.hide();

                if (typeof window.showToast === 'function') {
                    window.showToast('Risposta salvata!', 'success');
                }

                window.setTimeout(() => window.location.reload(), 1000);
                return;
            }

            window.alert(`Errore: ${result.error || 'Sconosciuto'}`);
        });
    }

    document.querySelectorAll('.delete-feedback-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', async function () {
            const feedbackId = this.dataset.feedbackId;
            if (!feedbackId) return;

            if (!window.confirm('Sei sicuro di voler eliminare questo feedback? L\'azione è irreversibile.')) {
                return;
            }

            const response = await fetch(`/admin/feedback/${feedbackId}/delete`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                if (typeof window.showToast === 'function') {
                    window.showToast('Feedback eliminato!', 'success');
                }

                window.setTimeout(() => window.location.reload(), 500);
                return;
            }

            window.alert(`Errore eliminazione: ${result.error || 'Sconosciuto'}`);
        });
    });
};