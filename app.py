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

    cursor.execute("SELECT JugadorId, Identificacion, Nombre, Marcador FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('jugadores.html', jugadores=jugadores)
####################################################
# Crear nueva partida
@app.route('/partida/nueva', methods=['GET', 'POST'])
def crear_partida():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        jugador1_id = request.form['jugador1']
        jugador2_id = request.form['jugador2']

        if jugador1_id == jugador2_id:
            flash("⚠️ No se puede seleccionar el mismo jugador dos veces.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for('crear_partida'))

        try:
            # Verificar que ambos jugadores existen
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

            cursor.execute("""
                INSERT INTO Partidas (Jugador1Id, Jugador2Id)
                VALUES (:1, :2)
            """, (jugador1_id, jugador2_id))
            conn.commit()

            cursor.execute("""
                SELECT PartidaId 
                FROM Partidas 
                WHERE Jugador1Id = :1 AND Jugador2Id = :2 
                ORDER BY PartidaId DESC FETCH FIRST 1 ROWS ONLY
            """, (jugador1_id, jugador2_id))
            partida_creada = cursor.fetchone()

            flash("✅ Partida creada correctamente", "success")
            return redirect(url_for('jugar', partida_id=partida_creada[0]))

        except Exception as e:
            conn.rollback()
            flash(f"❌ Error al crear la partida: {e}", "danger")
            print(f"ERROR en crear_partida: {e}")

        finally:
            cursor.close()
            conn.close()


    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT JugadorId, Nombre FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('crear_partida.html', jugadores=jugadores)

######################################################
@app.route('/cargar-partida')
def cargar_partida():
    # Esto es solo una vista temporal de prueba
    return render_template('cargar_partida.html')
##################################################
@app.route('/escalafon')
def escalafon():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Nombre, Marcador 
        FROM Jugadores 
        ORDER BY Marcador DESC
    """)
    ranking = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('escalafon.html', ranking=ranking)
##################################################
@app.route('/jugar/<int:partida_id>', methods=['GET', 'POST'])
def jugar(partida_id):
    conn = get_db_connection()
    cursor = conn.cursor()

   
    cursor.execute("""
        SELECT PartidaId, Jugador1Id, Jugador2Id, Estado
        FROM Partidas WHERE PartidaId = :1
    """, (partida_id,))
    partida = cursor.fetchone()

    if not partida:
        flash("Partida no encontrada", "danger")
        return redirect(url_for('index'))

    jugador1_id, jugador2_id = partida[1], partida[2]

   
    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador1_id,))
    jugador1_nombre = cursor.fetchone()[0]

    cursor.execute("SELECT Nombre FROM Jugadores WHERE JugadorId = :1", (jugador2_id,))
    jugador2_nombre = cursor.fetchone()[0]

  
    cursor.execute("""
        SELECT Columna, Fila, JugadorId 
        FROM Movimientos WHERE PartidaId = :1
    """, (partida_id,))
    movimientos = cursor.fetchall()

   
    cursor.execute("SELECT COUNT(*) FROM Movimientos WHERE PartidaId = :1", (partida_id,))
    turno = cursor.fetchone()[0]
    turno_actual = jugador1_id if turno % 2 == 0 else jugador2_id
    nombre_turno = jugador1_nombre if turno_actual == jugador1_id else jugador2_nombre

    if request.method == 'POST':
        columna = request.form['columna']
      
        cursor.execute("""
            SELECT Fila FROM Movimientos 
            WHERE PartidaId = :1 AND Columna = :2 
            ORDER BY Fila DESC FETCH FIRST 1 ROWS ONLY
        """, (partida_id, columna))
        fila_ocupada = cursor.fetchone()
        fila = fila_ocupada[0] + 1 if fila_ocupada else 0

        if fila >= 6:
            flash("La columna está llena", "warning")
        else:
            cursor.execute("""
                INSERT INTO Movimientos (PartidaId, JugadorId, Columna, Fila, Turno)
                VALUES (:1, :2, :3, :4, :5)
            """, (partida_id, turno_actual, columna, fila, turno + 1))
            conn.commit()
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
                           movimientos=movimientos)

##########################################
if __name__ == '__main__':
    app.run(debug=True, port=5001)