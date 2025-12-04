# ---------------------------------------------
# app.py — Flask con Inicio público, Login y Panel Admin
# ---------------------------------------------

# Importamos las librerías que se necesitan
import sqlite3   # Para manejar la base de datos SQLite
import os        # Para manejar rutas de archivos y carpetas

# Importamos funciones esenciales de Flask
from flask import Flask, render_template, request, redirect, url_for, g, session

# Para guardar archivos de forma segura (evita nombres peligrosos)
from werkzeug.utils import secure_filename

# ------------------------------------------------------
# CONFIGURACIÓN INICIAL DE LA APLICACIÓN
# ------------------------------------------------------

app = Flask(__name__)           # Crea la aplicación Flask
app.secret_key = "superclave"   # Llave secreta para manejar sesiones
DATABASE = "usuarios.db"        # Nombre del archivo de la base de datos

# Carpeta donde se guardarán las imágenes subidas
app.config['UPLOAD_FOLDER'] = "static/uploads"

# Crea la carpeta si no existe, para evitar errores
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ------------------------------------------------------
# FUNCIÓN PARA CONECTARSE A LA BASE DE DATOS
# ------------------------------------------------------

def get_db():
    # Busca si ya existe una conexión almacenada en 'g'
    db = getattr(g, '_database', None)

    # Si no existe, se crea una nueva conexión
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return db

# Cierra la conexión con la base de datos cuando Flask termine
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ------------------------------------------------------
# CREACIÓN E INICIALIZACIÓN DE LAS TABLAS
# ------------------------------------------------------

def init_db():
    # Abre la conexión a la base de datos
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Tabla de usuarios administradores
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT,
                        telefono TEXT,
                        direccion TEXT,
                        correo TEXT,
                        usuario TEXT UNIQUE,
                        clave TEXT
                    )''')

        # Tabla de hospedajes
        c.execute('''CREATE TABLE IF NOT EXISTS hospedajes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre_hotel TEXT,
                        ubicacion TEXT,
                        contacto TEXT,
                        precio TEXT,
                        tipo TEXT,
                        imagen TEXT,
                        mapa TEXT
                    )''')

        # Crea un usuario administrador por defecto si no existe
        c.execute("SELECT * FROM usuarios WHERE usuario = 'admin'")
        if not c.fetchone():
            c.execute("""INSERT INTO usuarios 
                         (nombre, telefono, direccion, correo, usuario, clave)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      ("Administrador", "0000000000", "Sin dirección", 
                       "admin@correo.com", "admin", "1234"))

        conn.commit()

# ------------------------------------------------------
# RUTA PÚBLICA — INICIO DEL SITIO (LISTAR HOSPEDAJES)
# ------------------------------------------------------

@app.route("/")
def index():
    db = get_db()
    hospedajes = db.execute("SELECT * FROM hospedajes").fetchall()
    # Se muestra la página con los hospedajes disponibles
    return render_template("index.html", hospedajes=hospedajes)

# ------------------------------------------------------
# LOGIN DEL ADMINISTRADOR
# ------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    # Si el usuario envió el formulario
    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]

        db = get_db()
        # Busca un admin con usuario y clave correctos
        admin = db.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND clave = ?",
            (usuario, clave)
        ).fetchone()

        if admin:
            # Guardamos sesión del administrador
            session["admin"] = True
            session["usuario"] = admin["usuario"]
            return redirect(url_for("panel"))

        # Si no coincide, muestra mensaje de error
        return render_template("login.html", error="Usuario o clave incorrecta")

    # Si es GET, solo muestra la página
    return render_template("login.html")

# ------------------------------------------------------
# PANEL DEL ADMINISTRADOR — REQUIERE SESIÓN
# ------------------------------------------------------

@app.route("/panel")
def panel():
    if "admin" not in session:      # Si no está logueado, lo manda al login
        return redirect(url_for("login"))

    db = get_db()
    hospedajes = db.execute("SELECT * FROM hospedajes").fetchall()
    return render_template("panel.html", hospedajes=hospedajes)

# ------------------------------------------------------
# CREAR NUEVO HOSPEDAJE
# ------------------------------------------------------

@app.route("/nuevo", methods=["GET", "POST"])
def nuevo():

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Obtiene los datos del formulario
        nombre = request.form["nombre"]
        ubicacion = request.form["ubicacion"]
        contacto = request.form["contacto"]
        precio = request.form["precio"]
        tipo = request.form["tipo"]
        mapa = request.form["mapa"]

        # Manejo de imagen subida
        imagen_file = request.files["imagen"]
        filename = None

        if imagen_file and imagen_file.filename != "":
            filename = secure_filename(imagen_file.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen_file.save(ruta)

        # Se guarda el hospedaje en la base de datos
        db = get_db()
        db.execute("""
            INSERT INTO hospedajes (nombre_hotel, ubicacion, contacto, precio, tipo, imagen, mapa)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nombre, ubicacion, contacto, precio, tipo, filename, mapa))
        db.commit()

        return redirect(url_for("panel"))

    return render_template("nuevo.html")

# ------------------------------------------------------
# EDITAR UN HOSPEDAJE EXISTENTE
# ------------------------------------------------------

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db()

    # Busca el hospedaje a editar
    hospedaje = db.execute("SELECT * FROM hospedajes WHERE id = ?", (id,)).fetchone()

    if not hospedaje:
        return "Hospedaje no encontrado", 404

    if request.method == "POST":
        # Actualiza valores
        nombre = request.form["nombre"]
        ubicacion = request.form["ubicacion"]
        contacto = request.form["contacto"]
        precio = request.form["precio"]
        tipo = request.form["tipo"]
        mapa = request.form["mapa"]

        # Manejo de imagen nueva opcional
        imagen_file = request.files["imagen"]
        filename = hospedaje["imagen"]  # Mantiene la imagen si no se sube una nueva

        if imagen_file and imagen_file.filename != "":
            filename = secure_filename(imagen_file.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen_file.save(ruta)

        # Actualiza el registro en la base de datos
        db.execute("""
            UPDATE hospedajes 
            SET nombre_hotel=?, ubicacion=?, contacto=?, precio=?, tipo=?, imagen=?, mapa=?
            WHERE id=?
        """, (nombre, ubicacion, contacto, precio, tipo, filename, mapa, id))
        db.commit()

        return redirect(url_for("panel"))

    return render_template("editar.html", h=hospedaje)

# ------------------------------------------------------
# ELIMINAR UN HOSPEDAJE
# ------------------------------------------------------

@app.route("/eliminar/<int:id>")
def eliminar(id):

    if "admin" not in session:
        return redirect(url_for("login"))

    db = get_db()

    # Buscar imagen para eliminarla físicamente
    hospedaje = db.execute("SELECT imagen FROM hospedajes WHERE id = ?", (id,)).fetchone()

    if hospedaje and hospedaje["imagen"]:
        ruta_img = os.path.join(app.config['UPLOAD_FOLDER'], hospedaje["imagen"])

        if os.path.exists(ruta_img):
            os.remove(ruta_img)  # Borra la imagen del servidor

    # Borra el registro de la BD
    db.execute("DELETE FROM hospedajes WHERE id = ?", (id,))
    db.commit()

    return redirect(url_for("panel"))

# ------------------------------------------------------
# CERRAR SESIÓN
# ------------------------------------------------------

@app.route("/logout")
def logout():
    session.clear()  # Limpia la sesión del admin
    return redirect(url_for("index"))

# ------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ------------------------------------------------------

if __name__ == "__main__":
    init_db()          # Crea las tablas si no existen
    app.run(debug=True)  # Inicia el servidor Flask
