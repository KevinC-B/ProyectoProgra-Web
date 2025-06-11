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
###########################################################
@app.route('/jugadores', methods=['GET', 'POST'])
def jugadores():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        identificacion = request.form['identificacion']
        nombre = request.form['nombre']
        cursor.execute("INSERT INTO Jugadores (Identificacion, Nombre) VALUES (:1, :2)",
                       (identificacion, nombre))
        conn.commit()
        flash("Jugador creado correctamente")
        return redirect(url_for('jugadores'))

    cursor.execute("SELECT JugadorId, Identificacion, Nombre, Marcador FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('jugadores.html', jugadores=jugadores)
#############################################################
@app.route('/partida/nueva', methods=['GET', 'POST'])
def crear_partida():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        jugador1_id = request.form['jugador1']
        jugador2_id = request.form['jugador2']
        if jugador1_id == jugador2_id:
            flash("No se puede seleccionar el mismo jugador dos veces", "danger")
            return redirect(url_for('crear_partida'))

        cursor.execute("""
            INSERT INTO Partidas (Jugador1Id, Jugador2Id) VALUES (:1, :2)
        """, (jugador1_id, jugador2_id))
        conn.commit()
        flash("Partida creada")
        return redirect(url_for('index'))

    cursor.execute("SELECT JugadorId, Nombre FROM Jugadores")
    jugadores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('crear_partida.html', jugadores=jugadores)
