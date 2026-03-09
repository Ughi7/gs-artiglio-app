window.initAggiornamenti = function () {
    function renderFilePreview(input) {
        const previewId = input.dataset.previewTarget;
        const preview = previewId ? document.getElementById(previewId) : null;
        const uploadAreaId = input.dataset.uploadAreaId;
        const uploadArea = uploadAreaId ? document.getElementById(uploadAreaId) : null;
        const file = input.files && input.files[0] ? input.files[0] : null;

        if (!preview || !uploadArea) return;

        preview.innerHTML = '';

        const label = uploadArea.querySelector('[data-upload-label]');
        if (label) {
            label.textContent = file ? file.name : (uploadArea.dataset.defaultLabel || 'Clicca o trascina un file');
        }

        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (event) {
            if (file.type.startsWith('image/')) {
                preview.innerHTML = `<img src="${event.target.result}" class="file-preview">`;
            } else if (file.type.startsWith('video/')) {
                preview.innerHTML = `<video src="${event.target.result}" class="file-preview" controls></video>`;
            }
        };
        reader.readAsDataURL(file);
    }

    document.querySelectorAll('.file-upload-area[data-file-input-id]').forEach((area) => {
        if (!area.dataset.spaBound) {
            area.dataset.spaBound = 'true';

            area.addEventListener('click', function () {
                const inputId = this.dataset.fileInputId;
                const input = inputId ? document.getElementById(inputId) : null;
                if (input) input.click();
            });

            area.addEventListener('dragover', function (event) {
                event.preventDefault();
                this.classList.add('dragover');
            });

            area.addEventListener('dragleave', function () {
                this.classList.remove('dragover');
            });

            area.addEventListener('drop', function (event) {
                event.preventDefault();
                this.classList.remove('dragover');

                const inputId = this.dataset.fileInputId;
                const input = inputId ? document.getElementById(inputId) : null;
                if (!input || !event.dataTransfer.files.length) return;

                input.files = event.dataTransfer.files;
                renderFilePreview(input);
            });
        }
    });

    document.querySelectorAll('input[type="file"][data-preview-target]').forEach((input) => {
        if (input.dataset.spaBound) return;
        input.dataset.spaBound = 'true';
        input.addEventListener('change', function () {
            renderFilePreview(this);
        });
    });

    document.querySelectorAll('.edit-release-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', function (event) {
            event.preventDefault();

            const modalEl = document.getElementById('editReleaseModal');
            if (!modalEl || typeof bootstrap === 'undefined') return;

            document.getElementById('editReleaseId').value = this.dataset.id || '';
            document.getElementById('editVersion').value = this.dataset.version || '';
            document.getElementById('editTitle').value = this.dataset.title || '';
            document.getElementById('editNotes').value = this.dataset.notes || '';
            document.getElementById('editIsMajor').checked = this.dataset.major === 'true';

            bootstrap.Modal.getOrCreateInstance(modalEl).show();
        });
    });

    document.querySelectorAll('.delete-release-btn').forEach((button) => {
        if (button.dataset.spaBound) return;
        button.dataset.spaBound = 'true';
        button.addEventListener('click', async function (event) {
            event.preventDefault();

            const releaseId = this.dataset.releaseId;
            const version = this.dataset.releaseVersion || '';
            if (!releaseId) return;

            if (!window.confirm(`Eliminare l'aggiornamento v${version}?`)) return;

            const response = await fetch(`/admin/aggiornamenti/${releaseId}/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();
            if (result.success) {
                window.location.reload();
                return;
            }

            window.alert(`Errore: ${result.error || 'Sconosciuto'}`);
        });
    });

    const saveReleaseBtn = document.getElementById('saveReleaseBtn');
    if (saveReleaseBtn && !saveReleaseBtn.dataset.spaBound) {
        saveReleaseBtn.dataset.spaBound = 'true';
        saveReleaseBtn.addEventListener('click', async function () {
            if (!window.confirm('Salvare le modifiche?')) return;

            const releaseId = document.getElementById('editReleaseId').value;
            const payload = {
                version: document.getElementById('editVersion').value,
                title: document.getElementById('editTitle').value,
                notes: document.getElementById('editNotes').value,
                is_major: document.getElementById('editIsMajor').checked
            };

            const response = await fetch(`/admin/aggiornamenti/${releaseId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (result.success) {
                window.location.reload();
                return;
            }

            window.alert(`Errore: ${result.error || 'Sconosciuto'}`);
        });
    }
};