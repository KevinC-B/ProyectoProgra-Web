document.addEventListener('DOMContentLoaded', function() {
    // Seleccionar todos los botones de columna
    const dropColumnButtons = document.querySelectorAll('.drop-column-btn');
    const turnoActualElement = document.getElementById('turno-actual');
    
    //Referencias a los elementos del overlay
    const gameOverOverlay = document.getElementById('game-over-overlay');
    const gameOverMessageText = document.getElementById('game-over-message-text');
    const mainMenuBtn = document.getElementById('main-menu-btn');
    const restartGameBtn = document.getElementById('restart-game-btn');

    //Asegurarse de que las variables globales desde Flask estén definidas
    if (typeof CURRENT_PARTIDA_ID === 'undefined' || 
        typeof JUGADOR1_ID === 'undefined' || 
        typeof JUGADOR2_ID === 'undefined') {
        console.error("Variables de configuración del juego (IDs de partida/jugadores) no definidas.");
        alert("Error de configuración del juego. Recarga la página.");
        return; //Detener la ejecución si las variables críticas faltan
    }

    //Añadir un event listener a cada botón de columna
    dropColumnButtons.forEach(button => {
        button.addEventListener('click', function() {
            const column = this.dataset.column; //Obtiene el valor de 'data-column'
            makeMove(column);
        });
    });

    //Event listeners para los nuevos botones
    mainMenuBtn.addEventListener('click', function() {
        window.location.href = '/'; //Redirige al menú principal
    });

    restartGameBtn.addEventListener('click', function() {
        //Construye la URL para reiniciar la partida con los mismos jugadores
        window.location.href = `/reiniciar/${JUGADOR1_ID}/${JUGADOR2_ID}`;
    });

    /**
     * Envía la solicitud de movimiento al servidor y actualiza el tablero.
     * @param {string} column El índice de la columna seleccionada (0-6).
     */
    function makeMove(column) {
        //Deshabilitar los botones mientras se procesa el movimiento para evitar clics múltiples
        dropColumnButtons.forEach(btn => btn.disabled = true);

        //Construir la URL dinámicamente usando el ID de la partida
        const url = `/jugar/${CURRENT_PARTIDA_ID}`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ column: column })
        })
        .then(response => {
            //Verificar si la respuesta fue exitosa (200)
            if (!response.ok) {
                //Si no fue exitosa, intentar parsear el mensaje de error del servidor
                return response.json().then(err => {
                    //Si el servidor envía un JSON con 'message', usarlo. Si no, un mensaje genérico.
                    throw new Error(err.message || `Error del servidor: ${response.status} ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                //El servidor nos dice dónde cayó la ficha y de qué jugador
                const row = data.row;
                const col = data.column;
                //Usamos los IDs de jugador que vienen del servidor para asignar la clase correcta
                const playerColorClass = data.player_color == data.jugador1_id ? 'jugador1-ficha' : 'jugador2-ficha';

                //Encontrar la celda donde la ficha debe aparecer
                const targetCell = document.getElementById(`celda-${row}-${col}`);

                if (targetCell) {
                    //Crear un nuevo elemento div para la ficha
                    const newFicha = document.createElement('div');
                    newFicha.classList.add('ficha', playerColorClass);

                    //Añadir la animación de caída después de un pequeño retraso
                    setTimeout(() => {
                        newFicha.classList.add('caer-animacion');
                    }, 10); //Retraso (10ms)

                    //Añadir la ficha a la celda
                    targetCell.appendChild(newFicha);
                    
                    //Actualizar el turno actual en la interfaz
                    if (turnoActualElement) {
                        turnoActualElement.textContent = data.next_player_name;
                    }

                    //Manejar fin de juego o mensajes de victoria/empate
                    if (data.game_over) {
                        //Mostrar el overlay de fin de juego
                        gameOverMessageText.textContent = data.message;
                        gameOverOverlay.classList.remove('hidden'); //Mostrar el overlay
                        
                        //Deshabilitar todos los botones de columna permanentemente
                        dropColumnButtons.forEach(btn => btn.disabled = true);
                    } else {
                        //Si el juego no ha terminado, re-habilitar los botones
                        dropColumnButtons.forEach(btn => btn.disabled = false);
                    }
                } else {
                    console.error('Error: Celda no encontrada para actualizar.', `celda-${row}-${col}`);
                    alert('Error interno: No se pudo encontrar la celda para actualizar visualmente.');
                    dropColumnButtons.forEach(btn => btn.disabled = false); //Re-habilitar botones en caso de error
                }
            } else {
                //Mostrar mensaje de error del servidor ("Columna llena")
                alert(data.message); 
                dropColumnButtons.forEach(btn => btn.disabled = false); //Re-habilitar botones en caso de error
            }
        })
        .catch(error => {
            //Catch para atrapar errores de red o errores lanzados desde el .then(response => ...)
            console.error('Error en la solicitud Fetch:', error);
            alert(`Hubo un error al comunicarse con el servidor: ${error.message}. Intenta de nuevo.`);
            dropColumnButtons.forEach(btn => btn.disabled = false); //Re-habilitar botones en caso de error
        });
    }
});