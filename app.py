from flask import Flask, render_template, request, redirect, url_for, session, flash
import oracledb

app = Flask(__name__)
app.secret_key = "connect4_secret"


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
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        identificacion = request.form['identificacion']
        nombre = request.form['nombre']

        cursor.execute("""
            INSERT INTO Jugadores (Identificacion, Nombre)
            VALUES (:1, :2)
        """, (identificacion, nombre))
        conn.commit()
        flash("Jugador creado correctamente", "success")
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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM Partidas 
        WHERE GanadorId = :jugador_id
    """, {"jugador_id": jugador_id})
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
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        jugador1_id = request.form['jugador1']
        jugador2_id = request.form['jugador2']

        # ❌ Mismo jugador seleccionado
        if jugador1_id == jugador2_id:
            flash("❌ No es permitido escoger el mismo jugador. Un jugador no puede jugar contra sí mismo.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('crear_partida'))

        try:
            # ✅ Validar que ambos jugadores existen
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

            # ✅ Crear la partida
            cursor.execute("""
                INSERT INTO Partidas (Jugador1Id, Jugador2Id)
                VALUES (:1, :2)
            """, (jugador1_id, jugador2_id))
            conn.commit()

            # Obtener el ID de la partida recién creada
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

    # GET: mostrar formulario
    cursor.execute("SELECT JugadorId, Nombre FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('crear_partida.html', jugadores=jugadores)

######################################################
@app.route('/cargar-partida')
def cargar_partida():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.PartidaId, 
               j1.Nombre AS jugador1, 
               j2.Nombre AS jugador2, 
               TO_CHAR(p.FechaInicio, 'YYYY-MM-DD HH24:MI') AS fecha,
               p.Estado
        FROM Partidas p
        JOIN Jugadores j1 ON p.Jugador1Id = j1.JugadorId
        JOIN Jugadores j2 ON p.Jugador2Id = j2.JugadorId
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
            'estado': row[4]
        })

    cursor.close()
    conn.close()
    return render_template('cargar_partida.html', partidas=partidas)

##################################################
@app.route('/escalafon')
def escalafon():
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
@app.route('/jugar/<int:partida_id>', methods=['GET', 'POST'])
def jugar(partida_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Obtener la partida
    cursor.execute("SELECT * FROM Partidas WHERE PartidaId = :1", (partida_id,))
    partida = cursor.fetchone()
    if not partida:
        flash("Partida no encontrada", "danger")
        return redirect(url_for('index'))

    jugador1_id = partida[1]
    jugador2_id = partida[2]
    estado = partida[4]
    ganador_id = partida[5]

    # Obtener nombres
    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador1_id,))
    jugador1_nombre = cursor.fetchone()[0]
    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador2_id,))
    jugador2_nombre = cursor.fetchone()[0]

    # Obtener movimientos
    cursor.execute("SELECT Columna, Fila, JugadorId FROM Movimientos WHERE PartidaId = :1", (partida_id,))
    movimientos = cursor.fetchall()
    ultima_jugada = movimientos[-1] if movimientos else None

    # Crear matriz del tablero
    tablero = [['' for _ in range(7)] for _ in range(6)]
    for col, fila, jugador in movimientos:
        col_idx = 'ABCDEFG'.index(col)
        tablero[fila][col_idx] = jugador

    # Turno actual
    turno = len(movimientos)
    turno_actual = jugador1_id if turno % 2 == 0 else jugador2_id
    nombre_turno = jugador1_nombre if turno_actual == jugador1_id else jugador2_nombre

    # Si ya está finalizada, no aceptar más jugadas
    if estado == 'FINALIZADA':
        cursor.close()
        conn.close()
        return render_template('jugar.html',
            partida_id=partida_id,
            jugador1=jugador1_nombre,
            jugador2=jugador2_nombre,
            turno_actual="Partida finalizada",
            jugador1_id=jugador1_id,
            jugador2_id=jugador2_id,
            movimientos=movimientos,
            ultima_jugada=ultima_jugada,
            filas=list(reversed(range(6)))
        )

    # POST: jugador hace jugada
    if request.method == 'POST':
        columna = request.form['columna'].upper()
        if columna not in 'ABCDEFG':
            flash("Columna inválida", "danger")
        else:
            col_idx = 'ABCDEFG'.index(columna)
            # Verificar fila disponible en columna
            fila_disponible = None
            for f in range(6):
                if tablero[f][col_idx] == '':
                    fila_disponible = f
                    break
            if fila_disponible is None:
                flash("Columna llena", "warning")
            else:
                # Insertar jugada
                cursor.execute("""
                    INSERT INTO Movimientos (PartidaId, JugadorId, Columna, Fila, Turno)
                    VALUES (:1, :2, :3, :4, :5)
                """, (partida_id, turno_actual, columna, fila_disponible, turno + 1))
                conn.commit()

                # Actualizar tablero en memoria
                tablero[fila_disponible][col_idx] = turno_actual

                # Verificar victoria
                def verificar_4_en_linea(tablero, jugador):
                    for f in range(6):
                        for c in range(7):
                            if c + 3 < 7 and all(tablero[f][c+i] == jugador for i in range(4)):
                                return True
                            if f + 3 < 6 and all(tablero[f+i][c] == jugador for i in range(4)):
                                return True
                            if f + 3 < 6 and c + 3 < 7 and all(tablero[f+i][c+i] == jugador for i in range(4)):
                                return True
                            if f + 3 < 6 and c - 3 >= 0 and all(tablero[f+i][c-i] == jugador for i in range(4)):
                                return True
                    return False

                if verificar_4_en_linea(tablero, turno_actual):
                    cursor.execute("""
                        UPDATE Partidas SET Estado = 'FINALIZADA', GanadorId = :1
                        WHERE PartidaId = :2
                    """, (turno_actual, partida_id))
                    conn.commit()
                    flash("🎉 ¡Victoria de {}!".format(nombre_turno), "success")
                elif turno + 1 == 42:
                    cursor.execute("""
                        UPDATE Partidas SET Estado = 'FINALIZADA', GanadorId = NULL
                        WHERE PartidaId = :1
                    """, (partida_id,))
                    conn.commit()
                    flash("🤝 ¡Empate!", "info")
                return redirect(url_for('jugar', partida_id=partida_id))

    cursor.close()
    conn.close()

    return render_template('jugar.html',
        partida_id=partida_id,
        jugador1=jugador1_nombre,
        jugador2=jugador2_nombre,
        turno_actual=nombre_turno,
        jugador1_id=jugador1_id,
        jugador2_id=jugador2_id,
        movimientos=movimientos,
        ultima_jugada=ultima_jugada,
        filas=list(reversed(range(6)))
    )

##########################################################
@app.route('/reiniciar/<int:jugador1>/<int:jugador2>')
def crear_partida_mismos(jugador1, jugador2):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Partidas (Jugador1Id, Jugador2Id)
        VALUES (:1, :2)
    """, (jugador1, jugador2))
    conn.commit()

    cursor.execute("""
        SELECT PartidaId FROM Partidas
        WHERE Jugador1Id = :1 AND Jugador2Id = :2
        ORDER BY PartidaId DESC FETCH FIRST 1 ROWS ONLY
    """, (jugador1, jugador2))
    nueva_partida = cursor.fetchone()

    cursor.close()
    conn.close()
    flash("🔁 Nueva partida creada con los mismos jugadores", "info")
    return redirect(url_for('jugar', partida_id=nueva_partida[0]))

##########################################
if __name__ == '__main__':
    app.run(debug=True, port=5001)