# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTIÓN DE VUELOS - VERSIÓN COMPLETA PARA RENDER
"""

import os
from flask import Flask, request, redirect, url_for, flash, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
import psycopg2.extras
from datetime import datetime
import bcrypt
import json
import random
import string
from functools import wraps
from dotenv import load_dotenv

# Configuración para Render - AGREGAR ESTO
import os
if 'RENDER' in os.environ:
    # En Render, usar la URL de la base de datos
    DATABASE_URL = "postgresql://yova:j0smlHpbZTp1qgZsruJUHI9XW7Gv9gtt@dpg-d4u0hcfgi27c73a9b4rg-a.virginia-postgres.render.com/sistema_2tdl"
else:
    # En desarrollo local
    DATABASE_URL = "postgresql://localhost/sistema_vuelos"

# Reemplazar la función get_db_connection con esta versión:
def get_db_connection():
    try:
        if 'RENDER' in os.environ:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        else:
            conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        raise
# ==================== CONFIGURACIÓN INICIAL ====================

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración desde variables de entorno
app.secret_key = os.environ.get('SECRET_KEY', 'clave-temporal-cambiar-en-produccion')

# Configurar Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página'
login_manager.login_message_category = 'warning'

# ==================== CONEXIÓN A BASE DE DATOS ====================

def get_db_connection():
    """Establece conexión segura a la base de datos"""
    try:
        # Conexión para Render (con SSL)
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            port=os.environ.get('DB_PORT', 5432),
            sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        raise

# ==================== MODELOS ====================

class User(UserMixin):
    def __init__(self, id, username, nombre, rol):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    """Cargar usuario desde la base de datos"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT id, username, nombre, rol FROM usuarios WHERE id = %s AND activo = TRUE', (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            return User(user['id'], user['username'], user['nombre'], user['rol'])
        return None
    except:
        return None

# ==================== DECORADORES Y FUNCIONES ====================

def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.rol not in roles:
                flash('No tienes permisos para acceder a esta página.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def registrar_log(accion, tabla=None, registro_id=None, detalles=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        detalles_json = json.dumps(detalles, ensure_ascii=False, default=str) if detalles else None
        cur.execute('''
            INSERT INTO logs_auditoria (usuario_id, accion, tabla_afectada, registro_id, detalles, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id if current_user.is_authenticated else None, accion, tabla, registro_id, detalles_json, request.remote_addr))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error en log: {e}")

def get_flashed_messages_html():
    messages = get_flashed_messages(with_categories=True)
    if not messages:
        return ''
    html_parts = []
    for category, message in messages:
        alert_class = {'success':'alert-success','danger':'alert-danger','warning':'alert-warning','info':'alert-info'}.get(category,'alert-info')
        html_parts.append(f'<div class="alert {alert_class} alert-dismissible fade show" role="alert">{message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>')
    return '\n'.join(html_parts)

# ==================== RUTAS PRINCIPALES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute('SELECT id, username, nombre, rol, password_hash FROM usuarios WHERE username = %s AND activo = TRUE', (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user_obj = User(user['id'], user['username'], user['nombre'], user['rol'])
                login_user(user_obj, remember=True)
                registrar_log('LOGIN', detalles={'username': username, 'rol': user['rol']})
                flash(f'¡Bienvenido, {user["nombre"]}!', 'success')
                return redirect(url_for('dashboard'))
            
            flash('Usuario o contraseña incorrectos.', 'danger')
        except Exception as e:
            flash('Error al iniciar sesión.', 'danger')
            print(f"Login error: {e}")
    
    return f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Sistema Vuelos</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        <style>
            body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; align-items: center; }}
            .login-box {{ max-width: 400px; margin: auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="login-box">
                <h2 class="text-center mb-4"><i class="bi bi-airplane"></i> Sistema Vuelos</h2>
                {get_flashed_messages_html()}
                <form method="POST">
                    <div class="mb-3">
                        <label class="form-label">Usuario</label>
                        <input type="text" class="form-control" name="username" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Contraseña</label>
                        <input type="password" class="form-control" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Ingresar</button>
                </form>
                <hr>
                <div class="text-center small text-muted">
                    Usuarios demo:<br>
                    admin / admin123<br>
                    responsable / responsable123<br>
                    empleado / empleado123<br>
                    consulta / consulta123
                </div>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    registrar_log('LOGOUT', detalles={'username': username})
    flash('Sesión cerrada', 'info')
    return redirect('/login')

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        hoy = datetime.now().date()
        
        # Estadísticas
        cur.execute("SELECT COUNT(*) FROM vuelos WHERE DATE(fecha_salida) = %s", (hoy,))
        vuelos_hoy = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COUNT(*) FROM reservas WHERE DATE(fecha_reserva) = %s", (hoy,))
        reservas_hoy = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COUNT(*) FROM aerolineas WHERE activa = TRUE")
        aerolineas_activas = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COUNT(DISTINCT p.id) FROM pasajeros p JOIN reservas r ON p.id = r.pasajero_id JOIN vuelos v ON r.vuelo_id = v.id WHERE DATE(v.fecha_salida) = %s", (hoy,))
        pasajeros_hoy = cur.fetchone()[0] or 0
        
        # Próximos vuelos
        cur.execute("SELECT v.*, a.nombre as aerolinea_nombre, a.codigo as aerolinea_codigo FROM vuelos v JOIN aerolineas a ON v.aerolinea_id = a.id WHERE v.fecha_salida >= NOW() ORDER BY v.fecha_salida LIMIT 5")
        proximos_vuelos = cur.fetchall()
        
        cur.close()
        conn.close()
        
        stats_html = f'''
        <div class="row mb-4">
            <div class="col-md-3"><div class="card text-white bg-primary h-100"><div class="card-body"><h6>Vuelos Hoy</h6><h2>{vuelos_hoy}</h2></div></div></div>
            <div class="col-md-3"><div class="card text-white bg-success h-100"><div class="card-body"><h6>Pasajeros Hoy</h6><h2>{pasajeros_hoy}</h2></div></div></div>
            <div class="col-md-3"><div class="card text-white bg-info h-100"><div class="card-body"><h6>Aerolíneas Activas</h6><h2>{aerolineas_activas}</h2></div></div></div>
            <div class="col-md-3"><div class="card text-white bg-warning h-100"><div class="card-body"><h6>Reservas Hoy</h6><h2>{reservas_hoy}</h2></div></div></div>
        </div>
        '''
        
        vuelos_html = ''
        if proximos_vuelos:
            for vuelo in proximos_vuelos:
                estado_color = {'programado':'success','en_vuelo':'warning','aterrizado':'info','cancelado':'danger'}.get(vuelo['estado'],'secondary')
                vuelos_html += f'''
                <tr>
                    <td><strong>{vuelo["numero_vuelo"]}</strong></td>
                    <td>{vuelo["aerolinea_codigo"]}</td>
                    <td>{vuelo["origen"]}</td>
                    <td>{vuelo["destino"]}</td>
                    <td>{vuelo["fecha_salida"].strftime('%d/%m %H:%M')}</td>
                    <td><span class="badge bg-{estado_color}">{vuelo["estado"]}</span></td>
                    <td>{vuelo["asientos_disponibles"]}/{vuelo["capacidad"]}</td>
                </tr>
                '''
        else:
            vuelos_html = '<tr><td colspan="7" class="text-center">No hay vuelos programados</td></tr>'
        
        # Accesos según rol
        accesos_html = '<div class="d-grid gap-2">'
        if current_user.rol in ['admin','responsable','empleado']:
            accesos_html += '''
            <a href="/vuelos" class="btn btn-outline-primary">Vuelos</a>
            <a href="/pasajeros" class="btn btn-outline-success">Pasajeros</a>
            <a href="/reservas" class="btn btn-outline-warning">Reservas</a>
            '''
        if current_user.rol in ['admin','responsable']:
            accesos_html += '''
            <a href="/aerolineas" class="btn btn-outline-info">Aerolíneas</a>
            <a href="/logs" class="btn btn-outline-secondary">Logs</a>
            '''
        if current_user.rol == 'admin':
            accesos_html += '<a href="/usuarios" class="btn btn-outline-dark">Usuarios</a>'
        accesos_html += '</div>'
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        </head>
        <body>
            <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
                <div class="container">
                    <a class="navbar-brand" href="/dashboard"><i class="bi bi-airplane"></i> Sistema Vuelos</a>
                    <div class="navbar-nav ms-auto">
                        <span class="navbar-text text-light me-3">
                            <i class="bi bi-person-circle"></i> {current_user.nombre} <span class="badge bg-light text-dark">{current_user.rol}</span>
                        </span>
                        <a href="/logout" class="btn btn-outline-light">Salir</a>
                    </div>
                </div>
            </nav>
            <div class="container">
                {get_flashed_messages_html()}
                <h1 class="mb-4"><i class="bi bi-speedometer2"></i> Dashboard</h1>
                {stats_html}
                <div class="row">
                    <div class="col-md-8">
                        <div class="card mb-4">
                            <div class="card-header"><h5 class="mb-0"><i class="bi bi-airplane-engines"></i> Próximos Vuelos</h5></div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-hover">
                                        <thead><tr><th>Vuelo</th><th>Aerolínea</th><th>Origen</th><th>Destino</th><th>Salida</th><th>Estado</th><th>Asientos</th></tr></thead>
                                        <tbody>{vuelos_html}</tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header"><h5 class="mb-0"><i class="bi bi-lightning-charge"></i> Accesos Rápidos</h5></div>
                            <div class="card-body">{accesos_html}</div>
                        </div>
                    </div>
                </div>
            </div>
            <footer class="mt-5 py-3 bg-light border-top text-center">
                <span class="text-muted">Sistema de Gestión de Vuelos &copy; {datetime.now().year}</span>
            </footer>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect('/login')

# ==================== CRUD VUELOS ====================

@app.route('/vuelos')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_vuelos():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('''
            SELECT v.*, a.nombre as aerolinea_nombre, a.codigo as aerolinea_codigo
            FROM vuelos v JOIN aerolineas a ON v.aerolinea_id = a.id
            ORDER BY v.fecha_salida
        ''')
        vuelos = cur.fetchall()
        cur.close()
        conn.close()
        
        vuelos_html = ''
        for vuelo in vuelos:
            estado_color = {'programado':'success','en_vuelo':'warning','aterrizado':'info','cancelado':'danger'}.get(vuelo['estado'],'secondary')
            vuelos_html += f'''
            <tr>
                <td><strong>{vuelo["numero_vuelo"]}</strong></td>
                <td>{vuelo["aerolinea_codigo"]}</td>
                <td>{vuelo["origen"]}</td>
                <td>{vuelo["destino"]}</td>
                <td>{vuelo["fecha_salida"].strftime('%d/%m %H:%M')}</td>
                <td>{vuelo["fecha_llegada"].strftime('%d/%m %H:%M')}</td>
                <td><span class="badge bg-{estado_color}">{vuelo["estado"]}</span></td>
                <td>{vuelo["asientos_disponibles"]}/{vuelo["capacidad"]}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <a href="/vuelos/{vuelo["id"]}/pasajeros" class="btn btn-info"><i class="bi bi-people"></i></a>
            '''
            if current_user.rol in ['admin','responsable']:
                vuelos_html += f'<a href="/vuelos/editar/{vuelo["id"]}" class="btn btn-warning"><i class="bi bi-pencil"></i></a>'
            if current_user.rol == 'admin':
                vuelos_html += f'''
                <form method="POST" action="/vuelos/eliminar/{vuelo["id"]}" class="d-inline">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('¿Eliminar vuelo?')"><i class="bi bi-trash"></i></button>
                </form>
                '''
            vuelos_html += '</div></td></tr>'
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Vuelos</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        </head>
        <body>
            <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard"><i class="bi bi-airplane"></i> Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
            <div class="container">
                {get_flashed_messages_html()}
                <div class="d-flex justify-content-between mb-4">
                    <h1><i class="bi bi-airplane"></i> Vuelos</h1>
                    <a href="/vuelos/nuevo" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nuevo Vuelo</a>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr><th>Vuelo</th><th>Aerolínea</th><th>Origen</th><th>Destino</th><th>Salida</th><th>Llegada</th><th>Estado</th><th>Asientos</th><th>Acciones</th></tr>
                        </thead>
                        <tbody>{vuelos_html}</tbody>
                    </table>
                </div>
            </div>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect('/dashboard')

@app.route('/vuelos/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def nuevo_vuelo():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO vuelos (numero_vuelo, aerolinea_id, origen, destino, fecha_salida, fecha_llegada, capacidad, asientos_disponibles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                request.form['numero_vuelo'],
                request.form['aerolinea_id'],
                request.form['origen'],
                request.form['destino'],
                request.form['fecha_salida'],
                request.form['fecha_llegada'],
                request.form['capacidad'],
                request.form['capacidad']
            ))
            conn.commit()
            flash('Vuelo creado', 'success')
            cur.close()
            conn.close()
            return redirect('/vuelos')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, codigo, nombre FROM aerolineas WHERE activa = TRUE")
    aerolineas = cur.fetchall()
    cur.close()
    conn.close()
    
    aerolineas_options = ''.join([f'<option value="{a["id"]}">{a["codigo"]} - {a["nombre"]}</option>' for a in aerolineas])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Nuevo Vuelo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/vuelos" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Nuevo Vuelo</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Número Vuelo</label><input type="text" class="form-control" name="numero_vuelo" required></div>
                            <div class="col-md-6"><label>Aerolínea</label><select class="form-select" name="aerolinea_id" required><option value="">Seleccionar...</option>{aerolineas_options}</select></div>
                            <div class="col-md-6"><label>Origen</label><input type="text" class="form-control" name="origen" required></div>
                            <div class="col-md-6"><label>Destino</label><input type="text" class="form-control" name="destino" required></div>
                            <div class="col-md-6"><label>Fecha Salida</label><input type="datetime-local" class="form-control" name="fecha_salida" required></div>
                            <div class="col-md-6"><label>Fecha Llegada</label><input type="datetime-local" class="form-control" name="fecha_llegada" required></div>
                            <div class="col-md-12"><label>Capacidad</label><input type="number" class="form-control" name="capacidad" value="150" required></div>
                        </div>
                        <div class="mt-4">
                            <a href="/vuelos" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Crear Vuelo</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/vuelos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_vuelo(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cur.execute('''
                UPDATE vuelos SET numero_vuelo=%s, aerolinea_id=%s, origen=%s, destino=%s, fecha_salida=%s, fecha_llegada=%s, capacidad=%s, asientos_disponibles=%s, estado=%s
                WHERE id=%s
            ''', (
                request.form['numero_vuelo'], request.form['aerolinea_id'], request.form['origen'], request.form['destino'],
                request.form['fecha_salida'], request.form['fecha_llegada'], request.form['capacidad'],
                request.form['asientos_disponibles'], request.form['estado'], id
            ))
            conn.commit()
            flash('Vuelo actualizado', 'success')
            cur.close()
            conn.close()
            return redirect('/vuelos')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    cur.execute('SELECT * FROM vuelos WHERE id = %s', (id,))
    vuelo = cur.fetchone()
    
    cur.execute("SELECT id, codigo, nombre FROM aerolineas")
    aerolineas = cur.fetchall()
    
    aerolineas_options = ''.join([f'<option value="{a["id"]}" {"selected" if a["id"] == vuelo["aerolinea_id"] else ""}>{a["codigo"]} - {a["nombre"]}</option>' for a in aerolineas])
    
    estados = ['programado','en_vuelo','aterrizado','cancelado']
    estado_options = ''.join([f'<option value="{e}" {"selected" if e == vuelo["estado"] else ""}>{e}</option>' for e in estados])
    
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Editar Vuelo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/vuelos" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Editar Vuelo {vuelo["numero_vuelo"]}</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Número Vuelo</label><input type="text" class="form-control" name="numero_vuelo" value="{vuelo["numero_vuelo"]}" required></div>
                            <div class="col-md-6"><label>Aerolínea</label><select class="form-select" name="aerolinea_id" required>{aerolineas_options}</select></div>
                            <div class="col-md-6"><label>Origen</label><input type="text" class="form-control" name="origen" value="{vuelo["origen"]}" required></div>
                            <div class="col-md-6"><label>Destino</label><input type="text" class="form-control" name="destino" value="{vuelo["destino"]}" required></div>
                            <div class="col-md-6"><label>Fecha Salida</label><input type="datetime-local" class="form-control" name="fecha_salida" value="{vuelo["fecha_salida"].strftime('%Y-%m-%dT%H:%M')}" required></div>
                            <div class="col-md-6"><label>Fecha Llegada</label><input type="datetime-local" class="form-control" name="fecha_llegada" value="{vuelo["fecha_llegada"].strftime('%Y-%m-%dT%H:%M')}" required></div>
                            <div class="col-md-6"><label>Capacidad</label><input type="number" class="form-control" name="capacidad" value="{vuelo["capacidad"]}" required></div>
                            <div class="col-md-6"><label>Asientos Disponibles</label><input type="number" class="form-control" name="asientos_disponibles" value="{vuelo["asientos_disponibles"]}" required></div>
                            <div class="col-md-12"><label>Estado</label><select class="form-select" name="estado">{estado_options}</select></div>
                        </div>
                        <div class="mt-4">
                            <a href="/vuelos" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Actualizar</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/vuelos/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_vuelo(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM vuelos WHERE id = %s", (id,))
        conn.commit()
        flash('Vuelo eliminado', 'success')
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/vuelos')

@app.route('/vuelos/<int:id>/pasajeros')
@login_required
def ver_pasajeros_vuelo(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT p.*, r.asiento, r.clase, r.codigo_reserva
        FROM pasajeros p JOIN reservas r ON p.id = r.pasajero_id
        WHERE r.vuelo_id = %s AND r.estado = 'confirmada'
    ''', (id,))
    pasajeros = cur.fetchall()
    cur.execute('SELECT numero_vuelo FROM vuelos WHERE id = %s', (id,))
    vuelo = cur.fetchone()
    cur.close()
    conn.close()
    
    pasajeros_html = ''.join([f'<tr><td>{p["pasaporte"]}</td><td>{p["nombre"]} {p["apellido"]}</td><td>{p["nacionalidad"] or "N/A"}</td><td>{p["asiento"] or "N/A"}</td><td>{p["clase"]}</td><td>{p["codigo_reserva"]}</td></tr>' for p in pasajeros])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Pasajeros</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/vuelos" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            <h1 class="mb-4">Pasajeros - Vuelo {vuelo["numero_vuelo"]}</h1>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Pasaporte</th><th>Nombre</th><th>Nacionalidad</th><th>Asiento</th><th>Clase</th><th>Código Reserva</th></tr></thead>
                    <tbody>{pasajeros_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

# ==================== CRUD PASAJEROS ====================

@app.route('/pasajeros')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_pasajeros():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM pasajeros ORDER BY apellido, nombre')
    pasajeros = cur.fetchall()
    cur.close()
    conn.close()
    
    pasajeros_html = ''
    for p in pasajeros:
        pasajeros_html += f'''
        <tr>
            <td>{p["pasaporte"]}</td>
            <td>{p["nombre"]} {p["apellido"]}</td>
            <td>{p["nacionalidad"] or "N/A"}</td>
            <td>{p["email"] or "N/A"}</td>
            <td>{p["telefono"] or "N/A"}</td>
            <td>
                <a href="/pasajeros/editar/{p["id"]}" class="btn btn-warning btn-sm"><i class="bi bi-pencil"></i></a>
                <form method="POST" action="/pasajeros/eliminar/{p["id"]}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar pasajero?')"><i class="bi bi-trash"></i></button>
                </form>
            </td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Pasajeros</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <div class="d-flex justify-content-between mb-4">
                <h1><i class="bi bi-people"></i> Pasajeros</h1>
                <a href="/pasajeros/nuevo" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nuevo Pasajero</a>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Pasaporte</th><th>Nombre</th><th>Nacionalidad</th><th>Email</th><th>Teléfono</th><th>Acciones</th></tr></thead>
                    <tbody>{pasajeros_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/pasajeros/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def nuevo_pasajero():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO pasajeros (pasaporte, nombre, apellido, nacionalidad, fecha_nacimiento, telefono, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                request.form['pasaporte'], request.form['nombre'], request.form['apellido'],
                request.form['nacionalidad'], request.form['fecha_nacimiento'] or None,
                request.form['telefono'], request.form['email']
            ))
            conn.commit()
            flash('Pasajero creado', 'success')
            cur.close()
            conn.close()
            return redirect('/pasajeros')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Nuevo Pasajero</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/pasajeros" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Nuevo Pasajero</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Pasaporte</label><input type="text" class="form-control" name="pasaporte" required></div>
                            <div class="col-md-6"><label>Nacionalidad</label><input type="text" class="form-control" name="nacionalidad"></div>
                            <div class="col-md-6"><label>Nombre</label><input type="text" class="form-control" name="nombre" required></div>
                            <div class="col-md-6"><label>Apellido</label><input type="text" class="form-control" name="apellido" required></div>
                            <div class="col-md-6"><label>Fecha Nacimiento</label><input type="date" class="form-control" name="fecha_nacimiento"></div>
                            <div class="col-md-6"><label>Teléfono</label><input type="text" class="form-control" name="telefono"></div>
                            <div class="col-md-12"><label>Email</label><input type="email" class="form-control" name="email"></div>
                        </div>
                        <div class="mt-4">
                            <a href="/pasajeros" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Crear Pasajero</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/pasajeros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def editar_pasajero(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cur.execute('''
                UPDATE pasajeros SET pasaporte=%s, nombre=%s, apellido=%s, nacionalidad=%s, fecha_nacimiento=%s, telefono=%s, email=%s
                WHERE id=%s
            ''', (
                request.form['pasaporte'], request.form['nombre'], request.form['apellido'],
                request.form['nacionalidad'], request.form['fecha_nacimiento'] or None,
                request.form['telefono'], request.form['email'], id
            ))
            conn.commit()
            flash('Pasajero actualizado', 'success')
            cur.close()
            conn.close()
            return redirect('/pasajeros')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    cur.execute('SELECT * FROM pasajeros WHERE id = %s', (id,))
    pasajero = cur.fetchone()
    cur.close()
    conn.close()
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Editar Pasajero</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/pasajeros" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Editar Pasajero</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Pasaporte</label><input type="text" class="form-control" name="pasaporte" value="{pasajero["pasaporte"]}" required></div>
                            <div class="col-md-6"><label>Nacionalidad</label><input type="text" class="form-control" name="nacionalidad" value="{pasajero["nacionalidad"] or ""}"></div>
                            <div class="col-md-6"><label>Nombre</label><input type="text" class="form-control" name="nombre" value="{pasajero["nombre"]}" required></div>
                            <div class="col-md-6"><label>Apellido</label><input type="text" class="form-control" name="apellido" value="{pasajero["apellido"]}" required></div>
                            <div class="col-md-6"><label>Fecha Nacimiento</label><input type="date" class="form-control" name="fecha_nacimiento" value="{pasajero["fecha_nacimiento"].strftime("%Y-%m-%d") if pasajero["fecha_nacimiento"] else ""}"></div>
                            <div class="col-md-6"><label>Teléfono</label><input type="text" class="form-control" name="telefono" value="{pasajero["telefono"] or ""}"></div>
                            <div class="col-md-12"><label>Email</label><input type="email" class="form-control" name="email" value="{pasajero["email"] or ""}"></div>
                        </div>
                        <div class="mt-4">
                            <a href="/pasajeros" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Actualizar</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/pasajeros/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_pasajero(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM pasajeros WHERE id = %s", (id,))
        conn.commit()
        flash('Pasajero eliminado', 'success')
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/pasajeros')

# ==================== CRUD AEROLINEAS ====================

@app.route('/aerolineas')
@login_required
@role_required('admin', 'responsable')
def listar_aerolineas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM aerolineas ORDER BY nombre')
    aerolineas = cur.fetchall()
    cur.close()
    conn.close()
    
    aerolineas_html = ''
    for a in aerolineas:
        aerolineas_html += f'''
        <tr>
            <td><strong>{a["codigo"]}</strong></td>
            <td>{a["nombre"]}</td>
            <td>{a["pais_origen"] or "N/A"}</td>
            <td><span class="badge bg-{"success" if a["activa"] else "danger"}">{"Activa" if a["activa"] else "Inactiva"}</span></td>
            <td>
                <a href="/aerolineas/editar/{a["id"]}" class="btn btn-warning btn-sm"><i class="bi bi-pencil"></i></a>
                <form method="POST" action="/aerolineas/eliminar/{a["id"]}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar aerolínea?')"><i class="bi bi-trash"></i></button>
                </form>
            </td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Aerolíneas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <div class="d-flex justify-content-between mb-4">
                <h1><i class="bi bi-building"></i> Aerolíneas</h1>
                <a href="/aerolineas/nuevo" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nueva Aerolínea</a>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Código</th><th>Nombre</th><th>País Origen</th><th>Estado</th><th>Acciones</th></tr></thead>
                    <tbody>{aerolineas_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/aerolineas/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def nueva_aerolinea():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO aerolineas (codigo, nombre, pais_origen, fecha_fundacion)
                VALUES (%s, %s, %s, %s)
            ''', (
                request.form['codigo'], request.form['nombre'],
                request.form['pais_origen'], request.form['fecha_fundacion'] or None
            ))
            conn.commit()
            flash('Aerolínea creada', 'success')
            cur.close()
            conn.close()
            return redirect('/aerolineas')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Nueva Aerolínea</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/aerolineas" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Nueva Aerolínea</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Código IATA</label><input type="text" class="form-control" name="codigo" maxlength="3" required></div>
                            <div class="col-md-6"><label>Nombre</label><input type="text" class="form-control" name="nombre" required></div>
                            <div class="col-md-6"><label>País Origen</label><input type="text" class="form-control" name="pais_origen"></div>
                            <div class="col-md-6"><label>Fecha Fundación</label><input type="date" class="form-control" name="fecha_fundacion"></div>
                        </div>
                        <div class="mt-4">
                            <a href="/aerolineas" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Crear Aerolínea</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/aerolineas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_aerolinea(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            activa = 'activa' in request.form
            cur.execute('''
                UPDATE aerolineas SET codigo=%s, nombre=%s, pais_origen=%s, fecha_fundacion=%s, activa=%s
                WHERE id=%s
            ''', (
                request.form['codigo'], request.form['nombre'], request.form['pais_origen'],
                request.form['fecha_fundacion'] or None, activa, id
            ))
            conn.commit()
            flash('Aerolínea actualizada', 'success')
            cur.close()
            conn.close()
            return redirect('/aerolineas')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    cur.execute('SELECT * FROM aerolineas WHERE id = %s', (id,))
    aerolinea = cur.fetchone()
    cur.close()
    conn.close()
    
    checked = 'checked' if aerolinea['activa'] else ''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Editar Aerolínea</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/aerolineas" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Editar Aerolínea</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Código IATA</label><input type="text" class="form-control" name="codigo" value="{aerolinea["codigo"]}" required></div>
                            <div class="col-md-6"><label>Nombre</label><input type="text" class="form-control" name="nombre" value="{aerolinea["nombre"]}" required></div>
                            <div class="col-md-6"><label>País Origen</label><input type="text" class="form-control" name="pais_origen" value="{aerolinea["pais_origen"] or ""}"></div>
                            <div class="col-md-6"><label>Fecha Fundación</label><input type="date" class="form-control" name="fecha_fundacion" value="{aerolinea["fecha_fundacion"].strftime("%Y-%m-%d") if aerolinea["fecha_fundacion"] else ""}"></div>
                            <div class="col-md-12">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" name="activa" {checked}>
                                    <label class="form-check-label">Aerolínea Activa</label>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <a href="/aerolineas" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Actualizar</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/aerolineas/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_aerolinea(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM aerolineas WHERE id = %s", (id,))
        conn.commit()
        flash('Aerolínea eliminada', 'success')
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/aerolineas')

# ==================== CRUD RESERVAS ====================

@app.route('/reservas')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_reservas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT r.*, v.numero_vuelo, v.origen, v.destino, p.nombre as pasajero_nombre, p.apellido as pasajero_apellido
        FROM reservas r
        JOIN vuelos v ON r.vuelo_id = v.id
        JOIN pasajeros p ON r.pasajero_id = p.id
        ORDER BY r.fecha_reserva DESC
    ''')
    reservas = cur.fetchall()
    cur.close()
    conn.close()
    
    reservas_html = ''
    for r in reservas:
        estado_color = 'success' if r['estado'] == 'confirmada' else 'danger' if r['estado'] == 'cancelada' else 'warning'
        reservas_html += f'''
        <tr>
            <td><code>{r["codigo_reserva"]}</code></td>
            <td>{r["numero_vuelo"]} ({r["origen"]} → {r["destino"]})</td>
            <td>{r["pasajero_nombre"]} {r["pasajero_apellido"]}</td>
            <td>{r["asiento"] or "N/A"}</td>
            <td>{r["clase"]}</td>
            <td>${r["precio"] or 0:.2f}</td>
            <td><span class="badge bg-{estado_color}">{r["estado"]}</span></td>
            <td>
        '''
        if r['estado'] == 'confirmada':
            reservas_html += f'''
                <form method="POST" action="/reservas/cancelar/{r["id"]}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('¿Cancelar reserva?')"><i class="bi bi-x-circle"></i></button>
                </form>
            '''
        reservas_html += '</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Reservas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <div class="d-flex justify-content-between mb-4">
                <h1><i class="bi bi-ticket-perforated"></i> Reservas</h1>
                <a href="/reservas/nueva" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nueva Reserva</a>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Código</th><th>Vuelo</th><th>Pasajero</th><th>Asiento</th><th>Clase</th><th>Precio</th><th>Estado</th><th>Acciones</th></tr></thead>
                    <tbody>{reservas_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/reservas/nueva', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def nueva_reserva():
    if request.method == 'POST':
        try:
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO reservas (codigo_reserva, vuelo_id, pasajero_id, asiento, clase, precio)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                codigo, request.form['vuelo_id'], request.form['pasajero_id'],
                request.form['asiento'], request.form['clase'], request.form['precio']
            ))
            cur.execute('UPDATE vuelos SET asientos_disponibles = asientos_disponibles - 1 WHERE id = %s', (request.form['vuelo_id'],))
            conn.commit()
            flash(f'Reserva creada. Código: {codigo}', 'success')
            cur.close()
            conn.close()
            return redirect('/reservas')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, numero_vuelo, origen, destino, asientos_disponibles FROM vuelos WHERE asientos_disponibles > 0")
    vuelos = cur.fetchall()
    cur.execute("SELECT id, nombre, apellido, pasaporte FROM pasajeros")
    pasajeros = cur.fetchall()
    cur.close()
    conn.close()
    
    vuelos_options = ''.join([f'<option value="{v["id"]}">{v["numero_vuelo"]} ({v["origen"]}→{v["destino"]}) - {v["asientos_disponibles"]} asientos</option>' for v in vuelos])
    pasajeros_options = ''.join([f'<option value="{p["id"]}">{p["nombre"]} {p["apellido"]} - {p["pasaporte"]}</option>' for p in pasajeros])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Nueva Reserva</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/reservas" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Nueva Reserva</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Vuelo</label><select class="form-select" name="vuelo_id" required><option value="">Seleccionar...</option>{vuelos_options}</select></div>
                            <div class="col-md-6"><label>Pasajero</label><select class="form-select" name="pasajero_id" required><option value="">Seleccionar...</option>{pasajeros_options}</select></div>
                            <div class="col-md-4"><label>Asiento</label><input type="text" class="form-control" name="asiento" placeholder="Ej: 12A"></div>
                            <div class="col-md-4"><label>Clase</label><select class="form-select" name="clase"><option value="economica">Económica</option><option value="ejecutiva">Ejecutiva</option><option value="primera">Primera Clase</option></select></div>
                            <div class="col-md-4"><label>Precio ($)</label><input type="number" class="form-control" name="precio" step="0.01" value="250.00"></div>
                        </div>
                        <div class="mt-4">
                            <a href="/reservas" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Crear Reserva</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/reservas/cancelar/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def cancelar_reserva(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT vuelo_id FROM reservas WHERE id = %s', (id,))
        reserva = cur.fetchone()
        cur.execute('UPDATE reservas SET estado = "cancelada" WHERE id = %s', (id,))
        if reserva:
            cur.execute('UPDATE vuelos SET asientos_disponibles = asientos_disponibles + 1 WHERE id = %s', (reserva['vuelo_id'],))
        conn.commit()
        flash('Reserva cancelada', 'success')
        cur.close()
        conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/reservas')

# ==================== LOGS ====================

@app.route('/logs')
@login_required
@role_required('admin', 'responsable')
def ver_logs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT l.*, u.username FROM logs_auditoria l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        ORDER BY l.fecha_hora DESC LIMIT 100
    ''')
    logs = cur.fetchall()
    cur.close()
    conn.close()
    
    logs_html = ''
    for log in logs:
        accion_color = {'LOGIN':'success','CREAR':'primary','ACTUALIZAR':'warning','ELIMINAR':'danger','CANCELAR':'danger'}.get(log['accion'],'info')
        logs_html += f'''
        <tr>
            <td>{log["fecha_hora"].strftime("%d/%m %H:%M")}</td>
            <td>{log["username"] or "N/A"}</td>
            <td><span class="badge bg-{accion_color}">{log["accion"]}</span></td>
            <td>{log["tabla_afectada"] or "N/A"}</td>
            <td>{log["registro_id"] or "N/A"}</td>
        </tr>
        '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Logs</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            <h1 class="mb-4"><i class="bi bi-clock-history"></i> Logs del Sistema</h1>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Fecha/Hora</th><th>Usuario</th><th>Acción</th><th>Tabla</th><th>Registro ID</th></tr></thead>
                    <tbody>{logs_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

# ==================== USUARIOS ====================

@app.route('/usuarios')
@login_required
@role_required('admin')
def listar_usuarios():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM usuarios ORDER BY fecha_creacion DESC')
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    
    usuarios_html = ''
    for u in usuarios:
        rol_color = {'admin':'danger','responsable':'warning','empleado':'info','consulta':'secondary'}.get(u['rol'],'secondary')
        estado_badge = 'success' if u['activo'] else 'danger'
        usuarios_html += f'''
        <tr>
            <td>{u["username"]}</td>
            <td>{u["nombre"]}</td>
            <td>{u["email"] or "N/A"}</td>
            <td><span class="badge bg-{rol_color}">{u["rol"]}</span></td>
            <td><span class="badge bg-{estado_badge}">{'Activo' if u['activo'] else 'Inactivo'}</span></td>
            <td>
        '''
        if u['id'] != current_user.id:
            usuarios_html += f'''
                <form method="POST" action="/usuarios/eliminar/{u["id"]}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('¿Eliminar usuario?')"><i class="bi bi-trash"></i></button>
                </form>
            '''
        usuarios_html += '</td></tr>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Usuarios</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/dashboard" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <div class="d-flex justify-content-between mb-4">
                <h1><i class="bi bi-people-fill"></i> Usuarios</h1>
                <a href="/usuarios/nuevo" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nuevo Usuario</a>
            </div>
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead><tr><th>Usuario</th><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
                    <tbody>{usuarios_html}</tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def nuevo_usuario():
    if request.method == 'POST':
        try:
            password_hash = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO usuarios (username, password_hash, nombre, email, rol)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                request.form['username'], password_hash, request.form['nombre'],
                request.form['email'], request.form['rol']
            ))
            conn.commit()
            flash('Usuario creado', 'success')
            cur.close()
            conn.close()
            return redirect('/usuarios')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Nuevo Usuario</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-dark bg-primary mb-4"><div class="container"><a class="navbar-brand" href="/dashboard">Sistema Vuelos</a><a href="/usuarios" class="btn btn-outline-light">Volver</a></div></nav>
        <div class="container">
            {get_flashed_messages_html()}
            <h1 class="mb-4">Nuevo Usuario</h1>
            <div class="card">
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6"><label>Usuario</label><input type="text" class="form-control" name="username" required></div>
                            <div class="col-md-6"><label>Contraseña</label><input type="password" class="form-control" name="password" required></div>
                            <div class="col-md-6"><label>Nombre</label><input type="text" class="form-control" name="nombre" required></div>
                            <div class="col-md-6"><label>Email</label><input type="email" class="form-control" name="email"></div>
                            <div class="col-md-12"><label>Rol</label><select class="form-select" name="rol" required>
                                <option value="admin">Administrador</option>
                                <option value="responsable">Responsable</option>
                                <option value="empleado">Empleado</option>
                                <option value="consulta">Consulta</option>
                            </select></div>
                        </div>
                        <div class="mt-4">
                            <a href="/usuarios" class="btn btn-secondary">Cancelar</a>
                            <button type="submit" class="btn btn-success">Crear Usuario</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_usuario(id):
    try:
        if id == current_user.id:
            flash('No puedes eliminar tu propio usuario', 'danger')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
            conn.commit()
            flash('Usuario eliminado', 'success')
            cur.close()
            conn.close()
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/usuarios')

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return '''
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6 text-center">
                <h1 class="display-1">404</h1>
                <p class="lead">Página no encontrada</p>
                <a href="/dashboard" class="btn btn-primary">Volver al Dashboard</a>
            </div>
        </div>
    </div>
    ''', 404

@app.errorhandler(500)
def internal_server_error(e):
    return '''
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6 text-center">
                <h1 class="display-1">500</h1>
                <p class="lead">Error interno del servidor</p>
                <a href="/dashboard" class="btn btn-primary">Volver al Dashboard</a>
            </div>
        </div>
    </div>
    ''', 500

# ==================== EJECUCIÓN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
