document.addEventListener('DOMContentLoaded', function () {
    const dropColumnButtons = document.querySelectorAll('.drop-column-btn');
    const turnoActualElement = document.getElementById('turno-actual');
    const gameOverOverlay = document.getElementById('game-over-overlay');
    const gameOverMessageText = document.getElementById('game-over-message-text');
    const mainMenuBtn = document.getElementById('main-menu-btn');
    const restartGameBtn = document.getElementById('restart-game-btn');

    if (typeof CURRENT_PARTIDA_ID === 'undefined' ||
        typeof JUGADOR1_ID === 'undefined' ||
        typeof JUGADOR2_ID === 'undefined') {
        console.error("IDs de partida/jugadores no definidos");
        mostrarBurbuja("Error de configuración del juego. Recarga la página.");
        return;
    }

    dropColumnButtons.forEach(button => {
        button.addEventListener('click', function () {
            const column = this.dataset.column;
            makeMove(column);
        });
    });

    mainMenuBtn.addEventListener('click', function () {
        window.location.href = '/';
    });

    restartGameBtn.addEventListener('click', function () {
        window.location.href = `/reiniciar/${JUGADOR1_ID}/${JUGADOR2_ID}`;
    });

    function makeMove(column) {
        dropColumnButtons.forEach(btn => btn.disabled = true);
        const url = `/jugar/${CURRENT_PARTIDA_ID}`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ column: column })
        })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.message || `Error del servidor: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    const row = data.row;
                    const col = data.column;
                    const playerColorClass = data.player_color == data.jugador1_id ? 'jugador1-ficha' : 'jugador2-ficha';
                    const targetCell = document.getElementById(`celda-${row}-${col}`);

                    if (targetCell) {
                        const newFicha = document.createElement('div');
                        newFicha.classList.add('ficha', playerColorClass);
                        setTimeout(() => {
                            newFicha.classList.add('caer-animacion');
                        }, 10);
                        targetCell.appendChild(newFicha);

                        if (turnoActualElement) {
                            turnoActualElement.textContent = data.next_player_name;
                        }

                        if (data.game_over) {
                            gameOverMessageText.textContent = data.message;
                            gameOverOverlay.classList.remove('hidden');
                            dropColumnButtons.forEach(btn => btn.disabled = true);
                        } else {
                            dropColumnButtons.forEach(btn => btn.disabled = false);
                        }
                    } else {
                        console.error(`Celda no encontrada: celda-${row}-${col}`);
                        mostrarBurbuja('Error interno al mostrar ficha');
                        dropColumnButtons.forEach(btn => btn.disabled = false);
                    }
                } else {
                    mostrarBurbuja(data.message);
                    dropColumnButtons.forEach(btn => btn.disabled = false);
                }
            })
            .catch(error => {
                console.error('Error en la solicitud Fetch:', error);
                mostrarBurbuja(`Error al comunicar con el servidor: ${error.message}`);
                dropColumnButtons.forEach(btn => btn.disabled = false);
            });
    }

    function mostrarBurbuja(mensaje) {
        const burbuja = document.getElementById('bubble-message');
        const texto = document.getElementById('bubble-text');
        texto.textContent = mensaje;
        burbuja.classList.remove('d-none');
        setTimeout(() => {
            burbuja.classList.add('d-none');
        }, 3000);
    }
});
