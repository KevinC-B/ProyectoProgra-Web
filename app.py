from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import oracledb

app = Flask(__name__)
app.secret_key = "connect4_secret"

#Conexión a la base de datos Oracle
def get_db_connection():
    return oracledb.connect(
        user="PROYECTOPROGRA",
        password="PROYECTOPROGRA",
        dsn="localhost:1521/orcl"
    )

@app.route('/')
def index():
    return render_template('index.html')

###################################################

@app.route('/jugadores', methods=['GET', 'POST'])
def jugadores():
    
    """
    Maneja la creación de nuevos jugadores y muestra la lista de jugadores
    con sus marcadores actualizados.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        identificacion = request.form['identificacion']
        nombre = request.form['nombre']

        try:
            cursor.execute("""
                INSERT INTO Jugadores (Identificacion, Nombre)
                VALUES (:1, :2)
            """, (identificacion, nombre))
            conn.commit() #Guardar jugador si cumple con los requisitos
            flash("Jugador creado correctamente", "success")
        except oracledb.Error as e: 
            conn.rollback() #Deshacer cambios si hay un error
            error_obj, = e.args
            if error_obj.code == 1: #Código de error para violación de restricción PK
                flash(f"❌ La identificación {identificacion} ya está registrada. Intenta con otra.", "danger")

            else:
                flash(f"Error al crear jugador: {error_obj.message}", "danger")
            print(f"Error al insertar jugador: {e}")
        finally:
            cursor.close()
            conn.close()
            return redirect(url_for('jugadores'))

    # Obtener todos los jugadores y actualizar marcador individualmente
    cursor.execute("SELECT JugadorId FROM Jugadores")
    ids = cursor.fetchall()

    for (jugador_id,) in ids: 
        actualizar_marcador(jugador_id)

    # Obtener jugadores con marcador actualizado
    cursor.execute("""
        SELECT JugadorId, Identificacion, Nombre, Marcador 
        FROM Jugadores ORDER BY Marcador DESC
    """)
    jugadores = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('jugadores.html', jugadores=jugadores)

def actualizar_marcador(jugador_id):

    """
    Actualiza el marcador de un jugador específico basándose en sus partidas ganadas y perdidas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM Partidas 
        WHERE GanadorId = :jugador_id
    """, {"jugador_id": jugador_id}) #
    ganadas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM Partidas
        WHERE Estado = 'FINALIZADA'
        AND GanadorId IS NOT NULL
        AND (Jugador1Id = :jugador_id OR Jugador2Id = :jugador_id)
        AND GanadorId != :jugador_id
    """, {"jugador_id": jugador_id})
    perdidas = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM Partidas
        WHERE Estado = 'FINALIZADA' 
        AND GanadorId IS NULL
        AND (Jugador1Id = :jugador_id OR Jugador2Id = :jugador_id)
    """, {"jugador_id": jugador_id})
    empatadas = cursor.fetchone()[0]

    marcador = ganadas - perdidas

    cursor.execute("""
        UPDATE Jugadores 
        SET Marcador = :marcador 
        WHERE JugadorId = :jugador_id
    """, {
        "marcador": marcador,
        "jugador_id": jugador_id
    })

    conn.commit()
    cursor.close()
    conn.close()

####################################################

@app.route('/partida/nueva', methods=['GET', 'POST'])
def crear_partida():

    """
    Maneja la creación de una nueva partida entre dos jugadores.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        jugador1_id = request.form['jugador1']
        jugador2_id = request.form['jugador2']

        #Mismo jugador seleccionado
        if jugador1_id == jugador2_id:
            flash("❌ No es permitido escoger el mismo jugador. Un jugador no puede jugar contra sí mismo.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('crear_partida'))

        try:
            #Validar que ambos jugadores existen
            cursor.execute("""
                SELECT COUNT(*) FROM Jugadores 
                WHERE JugadorId IN (:1, :2)
            """, (jugador1_id, jugador2_id))
            cantidad = cursor.fetchone()[0]
            if cantidad != 2:
                flash("❌ Uno o ambos jugadores no existen en la base de datos.", "danger")
                cursor.close()
                conn.close()
                return redirect(url_for('crear_partida'))

            #Crear la partida
            cursor.execute("""
                INSERT INTO Partidas (Jugador1Id, Jugador2Id)
                VALUES (:1, :2)
            """, (jugador1_id, jugador2_id))
            conn.commit()

            #Obtener el ID de la partida recién creada
            cursor.execute("""
                SELECT PartidaId 
                FROM Partidas 
                WHERE Jugador1Id = :1 AND Jugador2Id = :2 
                ORDER BY PartidaId DESC FETCH FIRST 1 ROWS ONLY
            """, (jugador1_id, jugador2_id))
            partida_creada = cursor.fetchone()

            flash("✅ Partida creada correctamente. ¡A jugar!", "success")
            return redirect(url_for('jugar', partida_id=partida_creada[0]))

        except Exception as e:
            conn.rollback()
            flash("❌ Ocurrió un error al crear la partida. Intentalo nuevamente.", "danger")
            print(f"Error al crear partida: {e}")

        finally:
            cursor.close()
            conn.close()

    #GET: mostrar formulario
    cursor.execute("SELECT JugadorId, Nombre FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('crear_partida.html', jugadores=jugadores)

######################################################

@app.route('/cargar-partida')
def cargar_partida():

    """Muestra una lista de partidas existentes que pueden ser cargadas."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT p.PartidaId, 
           j1.Nombre AS jugador1, 
           j2.Nombre AS jugador2, 
           TO_CHAR(p.FechaInicio, 'YYYY-MM-DD HH24:MI') AS fecha,
           p.Estado,
           p.GanadorId,
           jg.Nombre AS ganador_nombre
    FROM Partidas p
    JOIN Jugadores j1 ON p.Jugador1Id = j1.JugadorId
    JOIN Jugadores j2 ON p.Jugador2Id = j2.JugadorId
    LEFT JOIN Jugadores jg ON p.GanadorId = jg.JugadorId
    ORDER BY p.FechaInicio DESC
""")

    datos = cursor.fetchall()

    partidas = []
    for row in datos:
        partidas.append({
    'id': row[0],
    'jugador1': row[1],
    'jugador2': row[2],
    'fecha': row[3],
    'estado': row[4],
    'ganador': row[6]  # Puede ser None
})


    cursor.close()
    conn.close()
    return render_template('cargar_partida.html', partidas=partidas)

##################################################

@app.route('/escalafon')
def escalafon():

    """Muestra el escalafón de jugadores basado en sus marcadores."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
        j.Identificacion,
        j.Nombre,
        j.Marcador,
        (SELECT COUNT(*) FROM Partidas WHERE GanadorId = j.JugadorId) AS Ganadas,
        (SELECT COUNT(*) FROM Partidas 
         WHERE Estado = 'FINALIZADA' AND GanadorId IS NOT NULL 
         AND (Jugador1Id = j.JugadorId OR Jugador2Id = j.JugadorId) 
         AND GanadorId != j.JugadorId) AS Perdidas,
        (SELECT COUNT(*) FROM Partidas 
         WHERE Estado = 'FINALIZADA' AND GanadorId IS NULL 
         AND (Jugador1Id = j.JugadorId OR Jugador2Id = j.JugadorId)) AS Empatadas
    FROM Jugadores j
    ORDER BY j.Marcador DESC
    """)

    datos = cursor.fetchall()
    ranking = [
        {
            'identificacion': row[0],
            'nombre': row[1],
            'marcador': row[2],
            'ganadas': row[3],
            'perdidas': row[4],
            'empatadas': row[5],
        }
        for row in datos
    ]

    cursor.close()
    conn.close()

    return render_template('escalafon.html', ranking=ranking)

##################################################

# Función para verificar 4 en línea (se mueve fuera de la ruta para ser reutilizable)
def verificar_4_en_linea(tablero, jugador_id):

    """
    Verifica si un jugador ha logrado 4 fichas en línea en el tablero.
    """
    # Verificar horizontal
    for f in range(6):
        for c in range(4): # Solo hasta la columna 3 para verificar 4 en línea
            if all(tablero[f][c+i] == jugador_id for i in range(4)):
                return True
    # Verificar vertical
    for f in range(3): # Solo hasta la fila 2 para verificar 4 en línea
        for c in range(7):
            if all(tablero[f+i][c] == jugador_id for i in range(4)):
                return True
    # Verificar diagonal (ascendente)
    for f in range(3):
        for c in range(4):
            if all(tablero[f+i][c+i] == jugador_id for i in range(4)):
                return True
    # Verificar diagonal (descendente)
    for f in range(3):
        for c in range(3, 7): # Desde columna 3 hasta 6
            if all(tablero[f+i][c-i] == jugador_id for i in range(4)):
                return True
    return False

@app.route('/jugar/<int:partida_id>', methods=['GET', 'POST'])
def jugar(partida_id):

    """
    Maneja la lógica del juego Connect4 para una partida específica.
    Acepta solicitudes GET para cargar el tablero y POST (AJAX) para realizar movimientos.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    #Obtener la partida
    cursor.execute("SELECT PartidaId, Jugador1Id, Jugador2Id, Estado, GanadorId FROM Partidas WHERE PartidaId = :1", (partida_id,))
    partida = cursor.fetchone()
    if not partida:
        flash("Partida no encontrada", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for('index'))

    partida_id, jugador1_id, jugador2_id, estado, ganador_id = partida

    #Obtener nombres de los jugadores
    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador1_id,))
    jugador1_nombre = cursor.fetchone()[0]
    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador2_id,))
    jugador2_nombre = cursor.fetchone()[0]

    #Definir el diccionario player_names aquí
    player_names = {
        jugador1_id: jugador1_nombre,
        jugador2_id: jugador2_nombre
    }

    #Obtener movimientos existentes
    cursor.execute("SELECT Columna, Fila, JugadorId FROM Movimientos WHERE PartidaId = :1 ORDER BY Turno ASC", (partida_id,))
    movimientos_db = cursor.fetchall()

    #Crear matriz del tablero en memoria
    tablero = [['empty' for _ in range(7)] for _ in range(6)]
    for col_char, fila, jugador_id_mov in movimientos_db:
        col_idx = 'ABCDEFG'.index(col_char)
        tablero[fila][col_idx] = jugador_id_mov # Almacenar el ID del jugador en la celda

    #Determinar turno actual
    turno_numero = len(movimientos_db)
    turno_actual_id = jugador1_id if turno_numero % 2 == 0 else jugador2_id
    nombre_turno_actual = player_names[turno_actual_id] # Usar player_names aquí

    #Si la partida ya está finalizada, no permitir movimientos
    if estado == 'FINALIZADA':
        cursor.close()
        conn.close()
        #Para GET, renderiza la plantilla con el estado final
        if request.method == 'GET':
            #Ahora player_names está definido
            flash(f"Partida finalizada. Ganador: {player_names.get(ganador_id, 'Empate')}", "info")
            return render_template('jugar.html',
                partida_id=partida_id,
                jugador1_nombre=jugador1_nombre,
                jugador2_nombre=jugador2_nombre,
                turno_actual="Partida finalizada",
                jugador1_id=jugador1_id,
                jugador2_id=jugador2_id,
                tablero=tablero #Pasar el tablero ya construido
            )
        #Para POST (AJAX), devuelve un JSON indicando que la partida ha terminado
        else: 
            return jsonify({
                'success': False,
                'message': f"Partida finalizada. Ganador: {player_names.get(ganador_id, 'Empate')}",
                'game_over': True,
                'winner_id': ganador_id
            })

    #Manejar solicitudes POST (movimientos AJAX)
    if request.method == 'POST':
        data = request.get_json()
        if not data or 'column' not in data:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Datos de columna no recibidos.'}), 400

        try:
            #La columna viene como índice numérico (0-6) desde JS
            col_idx = int(data['column'])
            columna_char = 'ABCDEFG'[col_idx] #Convertir a letra para la base de datos
        except (ValueError, IndexError):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Columna inválida.'}), 400

        #Validar que la columna esté dentro de los límites
        if not (0 <= col_idx < 7):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Columna fuera de rango.'}), 400

        #Verificar fila disponible en columna (desde abajo hacia arriba)
        fila_disponible = None
        for f in range(6): # Filas 0 a 5
            if tablero[f][col_idx] == 'empty':
                fila_disponible = f
                break
        
        if fila_disponible is None:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Columna llena, elige otra!'})

        try:
            #Insertar jugada en la base de datos
            cursor.execute("""
                INSERT INTO Movimientos (PartidaId, JugadorId, Columna, Fila, Turno)
                VALUES (:1, :2, :3, :4, :5)
            """, (partida_id, turno_actual_id, columna_char, fila_disponible, turno_numero + 1))
            conn.commit()

            #Actualizar tablero en memoria para la verificación de victoria
            tablero[fila_disponible][col_idx] = turno_actual_id

            game_over = False
            message = "Movimiento exitoso!"
            winner_id = None

            #Verificar victoria
            if verificar_4_en_linea(tablero, turno_actual_id):
                game_over = True
                winner_id = turno_actual_id
                message = f"🎉 ¡Victoria de {player_names[turno_actual_id]}!"
                cursor.execute("""
                    UPDATE Partidas SET Estado = 'FINALIZADA', GanadorId = :1
                    WHERE PartidaId = :2
                """, (winner_id, partida_id))
                conn.commit()
                #Actualizar marcador del ganador
                actualizar_marcador(winner_id)
                #Actualizar marcador del perdedor
                loser_id = jugador1_id if winner_id == jugador2_id else jugador2_id
                actualizar_marcador(loser_id)

            #Verificar empate (tablero lleno sin ganador)
            elif (turno_numero + 1) == 42: #Si es el último movimiento posible
                #Asegurarse de que no haya un ganador antes de declarar empate
                if not verificar_4_en_linea(tablero, jugador1_id) and \
                   not verificar_4_en_linea(tablero, jugador2_id):
                    game_over = True
                    message = "🤝 ¡Empate!"
                    cursor.execute("""
                        UPDATE Partidas SET Estado = 'FINALIZADA', GanadorId = NULL
                        WHERE PartidaId = :1
                    """, (partida_id,))
                    conn.commit()
                    #Actualizar marcadores de ambos jugadores por empate
                    actualizar_marcador(jugador1_id)
                    actualizar_marcador(jugador2_id)

            #Determinar el siguiente jugador y su nombre
            next_player_id = jugador2_id if turno_actual_id == jugador1_id else jugador1_id
            next_player_name = player_names[next_player_id]

            cursor.close()
            conn.close()

            #Devolver respuesta JSON al frontend
            return jsonify({
                'success': True,
                'row': fila_disponible,
                'column': col_idx,
                'player_color': turno_actual_id, #ID del jugador que acaba de mover
                'jugador1_id': jugador1_id,
                'jugador2_id': jugador2_id,
                'next_player_name': next_player_name,
                'game_over': game_over,
                'message': message,
                'winner_id': winner_id #ID del ganador si lo hay
            })

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            print(f"Error al procesar movimiento: {e}")
            return jsonify({'success': False, 'message': 'Ocurrió un error al procesar el movimiento.'}), 500

    #Manejar solicitudes GET (carga inicial de la página de juego)
    #Aquí se renderiza la plantilla con el estado actual del tablero
    cursor.close()
    conn.close()

    return render_template('jugar.html',
        partida_id=partida_id,
        jugador1_nombre=jugador1_nombre,
        jugador2_nombre=jugador2_nombre,
        turno_actual=nombre_turno_actual,
        jugador1_id=jugador1_id,
        jugador2_id=jugador2_id,
        tablero=tablero #Pasar la matriz del tablero al template
    )

##########################################################

@app.route('/reiniciar/<int:partida_id>')
def reiniciar_misma_partida(partida_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM Movimientos WHERE PartidaId = :1", (partida_id,))
        cursor.execute("""
            UPDATE Partidas 
            SET Estado = 'EN_CURSO', GanadorId = NULL 
            WHERE PartidaId = :1
        """, (partida_id,))
        conn.commit()

        flash("🔄 La partida se ha reiniciado exitosamente.", "info")
        return redirect(url_for('jugar', partida_id=partida_id))
    except Exception as e:
        conn.rollback()
        flash(f"Error al reiniciar la partida: {e}", "danger")
        print(f"Error al reiniciar partida: {e}")
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()


##########################################
if __name__ == '__main__':
    app.run(debug=True, port=5001)