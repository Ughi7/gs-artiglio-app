window.initRosa = function () {

    // --- SETUP MODAL EDIT GIOCATORE ---
    const editPlayerModal = document.getElementById('editPlayerModal');
    if (editPlayerModal && !editPlayerModal.dataset.spaBound) {
        editPlayerModal.dataset.spaBound = 'true';
        editPlayerModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;

            document.getElementById('editUserId').value = button.getAttribute('data-id');
            document.getElementById('editNome').value = button.getAttribute('data-nome');
            document.getElementById('editSoprannome').value = button.getAttribute('data-soprannome');
            document.getElementById('editNumero').value = button.getAttribute('data-numero');
            document.getElementById('editRuoloVolley').value = button.getAttribute('data-ruolo-volley');

            // Checkbox Booleani
            document.getElementById('editIsAdmin').checked = (button.getAttribute('data-admin') === 'True');
            document.getElementById('editIsNotaio').checked = (button.getAttribute('data-notaio') === 'True');
            document.getElementById('editIsCapitano').checked = (button.getAttribute('data-capitano') === 'True');
            document.getElementById('editIsPizza').checked = (button.getAttribute('data-pizza') === 'True');
            document.getElementById('editIsBirra').checked = (button.getAttribute('data-birra') === 'True');
            document.getElementById('editIsSmm').checked = (button.getAttribute('data-smm') === 'True');
            document.getElementById('editIsPreparatore').checked = (button.getAttribute('data-preparatore') === 'True');

            // Nuovi Ruoli
            document.getElementById('editIsConvenzioni').checked = (button.getAttribute('data-convenzioni') === 'True');
            document.getElementById('editIsAbbigliamento').checked = (button.getAttribute('data-abbigliamento') === 'True');
            document.getElementById('editIsSponsor').checked = (button.getAttribute('data-sponsor') === 'True');
            document.getElementById('editIsPensionato').checked = (button.getAttribute('data-pensionato') === 'True');
            document.getElementById('editIsGemellaggi').checked = (button.getAttribute('data-gemellaggi') === 'True');
            document.getElementById('editIsCoach').checked = (button.getAttribute('data-coach') === 'True');
            document.getElementById('editIsCatering').checked = (button.getAttribute('data-catering') === 'True');
            document.getElementById('editIsScout').checked = (button.getAttribute('data-scout') === 'True');
            document.getElementById('editIsPresidente').checked = (button.getAttribute('data-presidente') === 'True');
        });
    }

    // --- ORDINAMENTO GIOCATORI ---
    const roleOrder = {
        'Palleggiatore': 1,
        'Opposto': 2,
        'Libero': 3,
        'Schiacciatore': 4,
        'Centrale': 5,
        'Jolly': 6,
        'Allenatore': 7,
        'Dirigente': 8
    };

    function sortPlayers(sortBy) {
        const container = document.getElementById('players-container');
        if (!container) return;
        const cards = Array.from(container.querySelectorAll('.player-card'));

        cards.sort((a, b) => {
            if (sortBy === 'role') {
                const roleA = roleOrder[a.dataset.ruolo] || 99;
                const roleB = roleOrder[b.dataset.ruolo] || 99;
                return roleA - roleB;
            } else if (sortBy === 'number') {
                const numA = parseInt(a.dataset.numero) || 999;
                const numB = parseInt(b.dataset.numero) || 999;
                // Senza numero (999) va all'inizio
                if (numA === 999 && numB !== 999) return -1;
                if (numB === 999 && numA !== 999) return 1;
                return numA - numB;
            }
            return 0;
        });

        // Rimuovi e riaggiungi in ordine
        cards.forEach(card => container.appendChild(card));
    }

    const sortByRoleBtn = document.getElementById('sortByRole');
    const sortByNumberBtn = document.getElementById('sortByNumber');

    // Aggiungo flag per non attaccare doppi listener nei cambi pagina
    if (sortByRoleBtn && !sortByRoleBtn.dataset.spaBound) {
        sortByRoleBtn.dataset.spaBound = 'true';
        sortByRoleBtn.addEventListener('click', function () {
            sortPlayers('role');
            this.classList.add('active', 'btn-warning');
            this.classList.remove('btn-outline-secondary');
            if (sortByNumberBtn) {
                sortByNumberBtn.classList.remove('active', 'btn-warning');
                sortByNumberBtn.classList.add('btn-outline-secondary');
            }
        });
    }

    if (sortByNumberBtn && !sortByNumberBtn.dataset.spaBound) {
        sortByNumberBtn.dataset.spaBound = 'true';
        sortByNumberBtn.addEventListener('click', function () {
            sortPlayers('number');
            this.classList.add('active', 'btn-warning');
            this.classList.remove('btn-outline-secondary');
            if (sortByRoleBtn) {
                sortByRoleBtn.classList.remove('active', 'btn-warning');
                sortByRoleBtn.classList.add('btn-outline-secondary');
            }
        });
    }

    // --- MODAL AZIONI GIOCATORE E DENUNCIA ---
    const playerActionModal = document.getElementById('playerActionModal');
    if (playerActionModal && !playerActionModal.dataset.spaBound) {
        playerActionModal.dataset.spaBound = 'true';
        playerActionModal.addEventListener('show.bs.modal', function (event) {
            const card = event.relatedTarget;
            const playerId = card.getAttribute('data-player-id');
            const playerNome = card.getAttribute('data-player-nome');
            const playerSoprannome = card.getAttribute('data-player-soprannome');

            const displayName = playerSoprannome ? playerSoprannome : playerNome;
            document.getElementById('actionPlayerName').textContent = displayName;
            document.getElementById('viewProfileBtn').href = '/profilo/' + playerId;
            document.getElementById('denunciaPlayerId').value = playerId;
            document.getElementById('denunciaPlayerName').textContent = displayName;
        });
    }

    const openDenunciaBtn = document.getElementById('openDenunciaModal');
    if (openDenunciaBtn && !openDenunciaBtn.dataset.spaBound) {
        openDenunciaBtn.dataset.spaBound = 'true';
        openDenunciaBtn.addEventListener('click', function () {
            const playerActionModalEl = bootstrap.Modal.getInstance(playerActionModal);
            if (playerActionModalEl) playerActionModalEl.hide();
            const denunciaModal = new bootstrap.Modal(document.getElementById('denunciaModal'));
            denunciaModal.show();
        });
    }


    // --- SEARCHBAR ROSA ---
    const searchInput = document.getElementById('searchPlayer');
    const clearBtn = document.getElementById('clearSearch');
    const resultsText = document.getElementById('searchResults');
    const playerCards = document.querySelectorAll('.player-card');

    if (searchInput && playerCards.length > 0 && !searchInput.dataset.spaBound) {
        searchInput.dataset.spaBound = 'true';

        searchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase().trim();
            let visibleCount = 0;

            // Mostra/nascondi pulsante clear
            if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

            playerCards.forEach(card => {
                const nome = card.querySelector('h6')?.textContent?.toLowerCase() || '';
                const soprannome = card.querySelector('.text-artiglio.fst-italic')?.textContent?.toLowerCase() || '';
                const ruolo = card.querySelector('.text-muted')?.textContent?.toLowerCase() || '';
                const numero = card.dataset.numero || '';

                const matches = nome.includes(query) ||
                    soprannome.includes(query) ||
                    ruolo.includes(query) ||
                    numero.includes(query);

                if (matches || !query) {
                    card.style.display = '';
                    card.style.opacity = '1';
                    card.style.transform = 'scale(1)';
                    card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                    visibleCount++;
                } else {
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.8)';
                    card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                    setTimeout(() => {
                        if (card.style.opacity === '0') {
                            card.style.display = 'none';
                        }
                    }, 300);
                }
            });

            // Mostra contatore risultati
            if (resultsText) {
                if (query) {
                    resultsText.textContent = `${visibleCount} giocator${visibleCount === 1 ? 'e' : 'i'} trovat${visibleCount === 1 ? 'o' : 'i'}`;
                    resultsText.classList.remove('d-none');
                } else {
                    resultsText.classList.add('d-none');
                }
            }
        });

        // Pulsante clear
        if (clearBtn && !clearBtn.dataset.spaBound) {
            clearBtn.dataset.spaBound = 'true';
            clearBtn.addEventListener('click', function () {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
                searchInput.focus();
            });
        }
    }
};
