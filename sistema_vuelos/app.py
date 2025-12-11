# -*- coding: utf-8 -*-
"""
SISTEMA COMPLETO DE GESTION DE VUELOS
Version 2.0 - TODAS las funcionalidades implementadas
"""

from flask import Flask, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import bcrypt
import os
import json
import random
import string
from functools import wraps

app = Flask(__name__)
app.secret_key = 'clave-secreta-muy-segura-para-produccion-123'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Conexion a la base de datos
def get_db_connection():
    return psycopg2.connect('postgresql://yova:dt4vax6PavE7pLUXrz80hoZ017Srdx1A@dpg-d4t8guruibrs73cdft8g-a.ohio-postgres.render.com/sistema_gvqe')

class User(UserMixin):
    def __init__(self, id, username, nombre, rol):
        self.id = id
        self.username = username
        self.nombre = nombre
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM usuarios WHERE id = %s AND activo = TRUE', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if user:
        return User(user['id'], user['username'], user['nombre'], user['rol'])
    return None

# Decorador para permisos
def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.rol not in roles:
                flash('No tiene permisos para acceder a esta pagina', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# Funcion para registrar logs
def registrar_log(accion, tabla=None, registro_id=None, detalles=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        ip_address = request.remote_addr if request else '127.0.0.1'
        
        if detalles:
            detalles_str = json.dumps(detalles, ensure_ascii=False)
        else:
            detalles_str = None
        
        cur.execute('''
            INSERT INTO logs_auditoria (usuario_id, accion, tabla_afectada, registro_id, detalles, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id, accion, tabla, registro_id, detalles_str, ip_address))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error registrando log: {e}")

# ==================== FUNCIONES AUXILIARES HTML ====================
def get_flashed_messages_html():
    from flask import get_flashed_messages  # CORREGIDO: Cambié esta línea
    messages = get_flashed_messages(with_categories=True)  # CORREGIDO: Y esta línea
    if not messages:
        return ''
    
    html = ''
    for category, message in messages:
        alert_class = 'alert-' + category if category else 'alert-info'
        html += f'''
        <div class="alert {alert_class} alert-dismissible fade show" role="alert">
            {message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        '''
    return html

def get_navbar_html():
    return f'''
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container-fluid">
            <a class="navbar-brand" href="/dashboard">
                <i class="bi bi-airplane"></i> Sistema Vuelos
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/dashboard">
                            <i class="bi bi-speedometer2"></i> Dashboard
                        </a>
                    </li>
                    {get_menu_items()}
                </ul>
                <ul class="navbar-nav">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                            <i class="bi bi-person-circle"></i> {current_user.nombre}
                            <span class="badge bg-light text-dark ms-1">{current_user.rol}</span>
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/logout">
                                <i class="bi bi-box-arrow-right"></i> Cerrar Sesion
                            </a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    '''

def get_menu_items():
    rol = current_user.rol
    items = ''
    
    if rol in ['admin', 'responsable', 'empleado']:
        items += '''
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                <i class="bi bi-airplane-fill"></i> Operaciones
            </a>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="/vuelos">Vuelos</a></li>
                <li><a class="dropdown-item" href="/pasajeros">Pasajeros</a></li>
                <li><a class="dropdown-item" href="/reservas">Reservas</a></li>
                <li><a class="dropdown-item" href="/aerolineas">Aerolineas</a></li>
            </ul>
        </li>
        '''
    
    if rol in ['admin', 'responsable']:
        items += '''
        <li class="nav-item">
            <a class="nav-link" href="/logs">
                <i class="bi bi-clock-history"></i> Logs
            </a>
        </li>
        '''
    
    if rol == 'admin':
        items += '''
        <li class="nav-item">
            <a class="nav-link" href="/usuarios">
                <i class="bi bi-people-fill"></i> Usuarios
            </a>
        </li>
        '''
    
    return items

def get_footer_html():
    return f'''
    <footer class="footer mt-5 py-3 bg-light border-top">
        <div class="container text-center">
            <span class="text-muted">
                Sistema de Gestion de Vuelos &copy; 2025 | 
                Usuario: {current_user.nombre} | 
                Rol: {current_user.rol}
            </span>
        </div>
    </footer>
    '''

def get_base_html(title, content, extra_js=''):
    return f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - Sistema Vuelos</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        <style>
            body {{ background-color: #f5f5f5; min-height: 100vh; display: flex; flex-direction: column; }}
            .navbar {{ box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
            .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075); margin-bottom: 1.5rem; }}
            .table-hover tbody tr:hover {{ background-color: rgba(0,0,0,0.075); }}
            .stat-card {{ transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); }}
            .container-fluid {{ flex: 1; }}
        </style>
    </head>
    <body>
        {get_navbar_html()}
        
        <div class="container-fluid mt-3">
            {get_flashed_messages_html()}
            {content}
        </div>
        
        {get_footer_html()}
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        {extra_js}
    </body>
    </html>
    '''

# ==================== LOGIN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM usuarios WHERE username = %s AND activo = TRUE', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            user_obj = User(user['id'], user['username'], user['nombre'], user['rol'])
            login_user(user_obj, remember=True)
            registrar_log('LOGIN', detalles={'username': username, 'rol': user['rol']})
            flash(f'¡Bienvenido, {user["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Usuario o contrasena incorrectos', 'danger')
    
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Sistema Vuelos</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
        <style>
            body { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                min-height: 100vh;
                padding-top: 100px;
            }
            .login-card { 
                max-width: 400px; 
                margin: 0 auto;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-6 col-lg-4">
                    <div class="card login-card">
                        <div class="card-header bg-primary text-white text-center py-4">
                            <h4><i class="bi bi-airplane-fill"></i> Sistema de Vuelos</h4>
                            <p class="mb-0 mt-2">Inicio de Sesion</p>
                        </div>
                        <div class="card-body p-4">
                            ''' + get_flashed_messages_html() + '''
                            <form method="POST" action="/login">
                                <div class="mb-3">
                                    <label for="username" class="form-label">Usuario</label>
                                    <input type="text" class="form-control" id="username" name="username" required autofocus>
                                </div>
                                <div class="mb-3">
                                    <label for="password" class="form-label">Contrasena</label>
                                    <input type="password" class="form-control" id="password" name="password" required>
                                </div>
                                <div class="d-grid gap-2">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="bi bi-box-arrow-in-right"></i> Iniciar Sesion
                                    </button>
                                </div>
                            </form>
                            
                            <hr class="my-4">
                            
                            <div class="alert alert-info">
                                <h6><i class="bi bi-info-circle"></i> Usuarios de Prueba:</h6>
                                <small>
                                    <strong>Admin:</strong> admin / admin123<br>
                                    <strong>Responsable:</strong> responsable / responsable123<br>
                                    <strong>Consulta:</strong> consulta / consulta123<br>
                                    <strong>Empleado:</strong> empleado1 / empleado123
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''

# ==================== DASHBOARD ====================
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    hoy = datetime.now().date()
    
    # Estadisticas
    cur.execute("SELECT COUNT(*) FROM vuelos WHERE DATE(fecha_salida) = %s", (hoy,))
    vuelos_hoy = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT p.id) FROM pasajeros p JOIN reservas r ON p.id = r.pasajero_id JOIN vuelos v ON r.vuelo_id = v.id WHERE DATE(v.fecha_salida) = %s", (hoy,))
    pasajeros_hoy = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM aerolineas WHERE activa = TRUE")
    aerolineas_activas = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM reservas WHERE fecha_reserva::date = %s", (hoy,))
    reservas_hoy = cur.fetchone()[0]
    
    # Proximos vuelos
    cur.execute("""
        SELECT v.*, a.nombre as aerolinea_nombre, a.codigo as aerolinea_codigo
        FROM vuelos v
        JOIN aerolineas a ON v.aerolinea_id = a.id
        WHERE v.fecha_salida >= NOW()
        ORDER BY v.fecha_salida
        LIMIT 5
    """)
    proximos_vuelos = cur.fetchall()
    
    cur.close()
    conn.close()
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-speedometer2"></i> Dashboard</h1>
            <p class="lead">Bienvenido, {current_user.nombre}! <span class="badge bg-secondary">{current_user.rol}</span></p>
            <p class="text-muted">Fecha: {hoy.strftime("%d/%m/%Y")}</p>
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-white bg-primary stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title">Vuelos Hoy</h5>
                            <h2 class="card-text">{vuelos_hoy}</h2>
                        </div>
                        <i class="bi bi-airplane fs-1"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-success stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title">Pasajeros Hoy</h5>
                            <h2 class="card-text">{pasajeros_hoy}</h2>
                        </div>
                        <i class="bi bi-people fs-1"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-info stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title">Aerolineas Activas</h5>
                            <h2 class="card-text">{aerolineas_activas}</h2>
                        </div>
                        <i class="bi bi-building fs-1"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-warning stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title">Reservas Hoy</h5>
                            <h2 class="card-text">{reservas_hoy}</h2>
                        </div>
                        <i class="bi bi-ticket-perforated fs-1"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5><i class="bi bi-airplane-engines"></i> Proximos Vuelos</h5>
                </div>
                <div class="card-body">
    '''
    
    if proximos_vuelos:
        content += '''
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Vuelo</th>
                                    <th>Aerolinea</th>
                                    <th>Origen</th>
                                    <th>Destino</th>
                                    <th>Salida</th>
                                    <th>Estado</th>
                                    <th>Asientos</th>
                                </tr>
                            </thead>
                            <tbody>
        '''
        for vuelo in proximos_vuelos:
            estado_color = 'success' if vuelo['estado'] == 'programado' else 'warning' if vuelo['estado'] == 'en_vuelo' else 'info' if vuelo['estado'] == 'aterrizado' else 'danger'
            content += f'''
                                <tr>
                                    <td><strong>{vuelo['numero_vuelo']}</strong></td>
                                    <td>{vuelo['aerolinea_codigo']} - {vuelo['aerolinea_nombre']}</td>
                                    <td>{vuelo['origen']}</td>
                                    <td>{vuelo['destino']}</td>
                                    <td>{vuelo['fecha_salida'].strftime('%d/%m %H:%M')}</td>
                                    <td><span class="badge bg-{estado_color}">{vuelo['estado']}</span></td>
                                    <td>{vuelo['asientos_disponibles']}/{vuelo['capacidad']}</td>
                                </tr>
            '''
        content += '''
                            </tbody>
                        </table>
                    </div>
        '''
    else:
        content += '<p class="text-muted text-center">No hay vuelos programados</p>'
    
    content += '''
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5><i class="bi bi-lightning-charge"></i> Accesos Rapidos</h5>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
    '''
    
    # Accesos rapidos segun rol
    if current_user.rol in ['admin', 'responsable', 'empleado']:
        content += '''
                        <a href="/vuelos" class="btn btn-outline-primary btn-lg mb-2">
                            <i class="bi bi-airplane"></i> Gestionar Vuelos
                        </a>
                        <a href="/pasajeros" class="btn btn-outline-success btn-lg mb-2">
                            <i class="bi bi-people"></i> Gestionar Pasajeros
                        </a>
                        <a href="/reservas" class="btn btn-outline-warning btn-lg mb-2">
                            <i class="bi bi-ticket-perforated"></i> Gestionar Reservas
                        </a>
        '''
    
    if current_user.rol in ['admin', 'responsable']:
        content += '''
                        <a href="/aerolineas" class="btn btn-outline-info btn-lg mb-2">
                            <i class="bi bi-building"></i> Aerolineas
                        </a>
                        <a href="/logs" class="btn btn-outline-secondary btn-lg mb-2">
                            <i class="bi bi-clock-history"></i> Ver Logs
                        </a>
        '''
    
    if current_user.rol == 'admin':
        content += '''
                        <a href="/usuarios" class="btn btn-outline-dark btn-lg">
                            <i class="bi bi-people-fill"></i> Usuarios
                        </a>
        '''
    
    content += '''
                    </div>
                </div>
            </div>
            
            <div class="card mt-3">
                <div class="card-header">
                    <h5><i class="bi bi-info-circle"></i> Informacion del Sistema</h5>
                </div>
                <div class="card-body">
                    <p><strong>Rol actual:</strong> {current_user.rol}</p>
                    <p><strong>Permisos:</strong> 
    '''
    
    if current_user.rol == 'admin':
        content += 'Control total del sistema'
    elif current_user.rol == 'responsable':
        content += 'Gestionar registros (sin borrado masivo)'
    elif current_user.rol == 'empleado':
        content += 'Operaciones de venta y check-in'
    else:
        content += 'Solo consulta'
    
    content += f'''
                    </p>
                    <hr>
                    <small class="text-muted">
                        Sistema de Gestion de Vuelos v2.0<br>
                        Base de datos: PostgreSQL en Render<br>
                        Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}
                    </small>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Dashboard', content)

# ==================== CRUD VUELOS ====================
@app.route('/vuelos')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_vuelos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT v.*, a.nombre as aerolinea_nombre, a.codigo as aerolinea_codigo,
               COUNT(r.id) as reservas_count
        FROM vuelos v
        LEFT JOIN aerolineas a ON v.aerolinea_id = a.id
        LEFT JOIN reservas r ON v.id = r.vuelo_id AND r.estado = 'confirmada'
        GROUP BY v.id, a.id
        ORDER BY v.fecha_salida
    ''')
    
    vuelos = cur.fetchall()
    
    cur.close()
    conn.close()
    
    # Generar HTML de la tabla
    vuelos_html = ''
    for vuelo in vuelos:
        porcentaje = ((vuelo['capacidad'] - vuelo['asientos_disponibles']) / vuelo['capacidad'] * 100) if vuelo['capacidad'] > 0 else 0
        estado_color = 'success' if vuelo['estado'] == 'programado' else 'warning' if vuelo['estado'] == 'en_vuelo' else 'info' if vuelo['estado'] == 'aterrizado' else 'danger'
        ocupacion_color = 'success' if porcentaje < 70 else 'warning' if porcentaje < 90 else 'danger'
        
        vuelos_html += f'''
        <tr>
            <td><strong>{vuelo['numero_vuelo']}</strong></td>
            <td>{vuelo['aerolinea_codigo']} - {vuelo['aerolinea_nombre']}</td>
            <td>{vuelo['origen']}</td>
            <td>{vuelo['destino']}</td>
            <td>{vuelo['fecha_salida'].strftime('%d/%m %H:%M')}</td>
            <td>{vuelo['fecha_llegada'].strftime('%d/%m %H:%M')}</td>
            <td><span class="badge bg-{estado_color}">{vuelo['estado']}</span></td>
            <td>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar bg-{ocupacion_color}" 
                         style="width: {porcentaje:.0f}%">
                        {vuelo['capacidad'] - vuelo['asientos_disponibles']}/{vuelo['capacidad']}
                    </div>
                </div>
            </td>
            <td><span class="badge bg-info">{vuelo['reservas_count']}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <a href="/vuelos/{vuelo['id']}/pasajeros" class="btn btn-info" title="Ver Pasajeros">
                        <i class="bi bi-people"></i>
                    </a>
        '''
        if current_user.rol in ['admin', 'responsable']:
            vuelos_html += f'''
                    <a href="/vuelos/editar/{vuelo['id']}" class="btn btn-warning" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </a>
            '''
        if current_user.rol == 'admin':
            vuelos_html += f'''
                    <form method="POST" action="/vuelos/eliminar/{vuelo['id']}" class="d-inline">
                        <button type="submit" class="btn btn-danger" title="Eliminar"
                                onclick="return confirm('¿Está seguro de eliminar este vuelo?')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </form>
            '''
        vuelos_html += '''
                </div>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-airplane"></i> Gestionar Vuelos</h1>
        </div>
        <div class="col-md-4 text-end">
            {('<a href="/vuelos/nuevo" class="btn btn-success"><i class="bi bi-plus-circle"></i> Nuevo Vuelo</a>' 
              if current_user.rol in ['admin', 'responsable'] else '')}
            <a href="/dashboard" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if vuelos:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Vuelo</th>
                            <th>Aerolinea</th>
                            <th>Origen</th>
                            <th>Destino</th>
                            <th>Salida</th>
                            <th>Llegada</th>
                            <th>Estado</th>
                            <th>Asientos</th>
                            <th>Reservas</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {vuelos_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-airplane fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron vuelos</h4>
                <p>Crear un nuevo vuelo para comenzar</p>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Gestionar Vuelos', content)

@app.route('/vuelos/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def nuevo_vuelo():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('''
                INSERT INTO vuelos (numero_vuelo, aerolinea_id, origen, destino, 
                                  fecha_salida, fecha_llegada, capacidad, asientos_disponibles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                request.form['numero_vuelo'].upper(),
                request.form['aerolinea_id'],
                request.form['origen'].upper(),
                request.form['destino'].upper(),
                request.form['fecha_salida'],
                request.form['fecha_llegada'],
                int(request.form['capacidad']),
                int(request.form['capacidad'])
            ))
            
            vuelo_id = cur.fetchone()[0]
            conn.commit()
            
            detalles = {k: v for k, v in request.form.items()}
            registrar_log('CREAR', 'vuelos', vuelo_id, detalles)
            flash('Vuelo creado exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/vuelos')
            
        except Exception as e:
            flash(f'Error al crear vuelo: {str(e)}', 'danger')
    
    # Obtener aerolineas para el select
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, codigo, nombre FROM aerolineas WHERE activa = TRUE ORDER BY nombre")
    aerolineas = cur.fetchall()
    cur.close()
    conn.close()
    
    aerolineas_options = ''
    for a in aerolineas:
        aerolineas_options += f'<option value="{a["id"]}">{a["codigo"]} - {a["nombre"]}</option>'
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-airplane"></i> Nuevo Vuelo</h1>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion del Vuelo</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="numero_vuelo" class="form-label">Numero de Vuelo *</label>
                                <input type="text" class="form-control" id="numero_vuelo" name="numero_vuelo" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="aerolinea_id" class="form-label">Aerolinea *</label>
                                <select class="form-select" id="aerolinea_id" name="aerolinea_id" required>
                                    <option value="">Seleccionar aerolinea...</option>
                                    {aerolineas_options}
                                </select>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="origen" class="form-label">Origen *</label>
                                <input type="text" class="form-control" id="origen" name="origen" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="destino" class="form-label">Destino *</label>
                                <input type="text" class="form-control" id="destino" name="destino" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_salida" class="form-label">Fecha/Hora Salida *</label>
                                <input type="datetime-local" class="form-control" id="fecha_salida" name="fecha_salida" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_llegada" class="form-label">Fecha/Hora Llegada *</label>
                                <input type="datetime-local" class="form-control" id="fecha_llegada" name="fecha_llegada" required>
                            </div>
                            
                            <div class="col-md-12">
                                <label for="capacidad" class="form-label">Capacidad *</label>
                                <input type="number" class="form-control" id="capacidad" name="capacidad" value="150" min="1" required>
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/vuelos" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Crear Vuelo
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Nuevo Vuelo', content)

@app.route('/vuelos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable')
def editar_vuelo(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cur.execute('''
                UPDATE vuelos 
                SET numero_vuelo = %s, aerolinea_id = %s, origen = %s, destino = %s,
                    fecha_salida = %s, fecha_llegada = %s, estado = %s, capacidad = %s,
                    asientos_disponibles = %s
                WHERE id = %s
            ''', (
                request.form['numero_vuelo'].upper(),
                request.form['aerolinea_id'],
                request.form['origen'].upper(),
                request.form['destino'].upper(),
                request.form['fecha_salida'],
                request.form['fecha_llegada'],
                request.form['estado'],
                int(request.form['capacidad']),
                int(request.form['asientos_disponibles']),
                id
            ))
            
            conn.commit()
            detalles = {k: v for k, v in request.form.items()}
            registrar_log('ACTUALIZAR', 'vuelos', id, detalles)
            flash('Vuelo actualizado exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/vuelos')
            
        except Exception as e:
            flash(f'Error al actualizar vuelo: {str(e)}', 'danger')
    
    # Obtener datos del vuelo
    cur.execute('SELECT * FROM vuelos WHERE id = %s', (id,))
    vuelo = cur.fetchone()
    
    if not vuelo:
        flash('Vuelo no encontrado', 'danger')
        return redirect('/vuelos')
    
    # Obtener aerolineas
    cur.execute("SELECT id, codigo, nombre FROM aerolineas WHERE activa = TRUE ORDER BY nombre")
    aerolineas = cur.fetchall()
    
    cur.close()
    conn.close()
    
    aerolineas_options = ''
    for a in aerolineas:
        selected = 'selected' if a['id'] == vuelo['aerolinea_id'] else ''
        aerolineas_options += f'<option value="{a["id"]}" {selected}>{a["codigo"]} - {a["nombre"]}</option>'
    
    estados = ['programado', 'en_vuelo', 'aterrizado', 'cancelado']
    estado_options = ''
    for estado in estados:
        selected = 'selected' if estado == vuelo['estado'] else ''
        estado_options += f'<option value="{estado}" {selected}>{estado}</option>'
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-airplane"></i> Editar Vuelo</h1>
            <p class="lead">{vuelo['numero_vuelo']}</p>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion del Vuelo</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="numero_vuelo" class="form-label">Numero de Vuelo *</label>
                                <input type="text" class="form-control" id="numero_vuelo" name="numero_vuelo" 
                                       value="{vuelo['numero_vuelo']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="aerolinea_id" class="form-label">Aerolinea *</label>
                                <select class="form-select" id="aerolinea_id" name="aerolinea_id" required>
                                    <option value="">Seleccionar aerolinea...</option>
                                    {aerolineas_options}
                                </select>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="origen" class="form-label">Origen *</label>
                                <input type="text" class="form-control" id="origen" name="origen" 
                                       value="{vuelo['origen']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="destino" class="form-label">Destino *</label>
                                <input type="text" class="form-control" id="destino" name="destino" 
                                       value="{vuelo['destino']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_salida" class="form-label">Fecha/Hora Salida *</label>
                                <input type="datetime-local" class="form-control" id="fecha_salida" name="fecha_salida" 
                                       value="{vuelo['fecha_salida'].strftime('%Y-%m-%dT%H:%M')}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_llegada" class="form-label">Fecha/Hora Llegada *</label>
                                <input type="datetime-local" class="form-control" id="fecha_llegada" name="fecha_llegada" 
                                       value="{vuelo['fecha_llegada'].strftime('%Y-%m-%dT%H:%M')}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="capacidad" class="form-label">Capacidad *</label>
                                <input type="number" class="form-control" id="capacidad" name="capacidad" 
                                       value="{vuelo['capacidad']}" min="1" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="asientos_disponibles" class="form-label">Asientos Disponibles *</label>
                                <input type="number" class="form-control" id="asientos_disponibles" name="asientos_disponibles" 
                                       value="{vuelo['asientos_disponibles']}" min="0" required>
                            </div>
                            
                            <div class="col-md-12">
                                <label for="estado" class="form-label">Estado</label>
                                <select class="form-select" id="estado" name="estado">
                                    {estado_options}
                                </select>
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/vuelos" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Actualizar Vuelo
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Editar Vuelo', content)

@app.route('/vuelos/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_vuelo(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si tiene reservas activas
        cur.execute("SELECT COUNT(*) FROM reservas WHERE vuelo_id = %s AND estado = 'confirmada'", (id,))
        reservas_count = cur.fetchone()[0]
        
        if reservas_count > 0:
            flash('No se puede eliminar el vuelo porque tiene reservas activas', 'danger')
        else:
            # Obtener info antes de eliminar para el log
            cur.execute("SELECT numero_vuelo FROM vuelos WHERE id = %s", (id,))
            vuelo_num = cur.fetchone()
            
            cur.execute("DELETE FROM vuelos WHERE id = %s", (id,))
            conn.commit()
            
            if vuelo_num:
                registrar_log('ELIMINAR', 'vuelos', id, {'numero_vuelo': vuelo_num[0]})
            flash('Vuelo eliminado exitosamente', 'success')
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error al eliminar vuelo: {str(e)}', 'danger')
    
    return redirect('/vuelos')

@app.route('/vuelos/<int:id>/pasajeros')
@login_required
def ver_pasajeros_vuelo(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT p.*, r.asiento, r.clase, r.estado as estado_reserva, r.codigo_reserva
        FROM pasajeros p
        JOIN reservas r ON p.id = r.pasajero_id
        WHERE r.vuelo_id = %s AND r.estado = 'confirmada'
        ORDER BY p.apellido, p.nombre
    ''', (id,))
    
    pasajeros = cur.fetchall()
    
    cur.execute('SELECT numero_vuelo, origen, destino FROM vuelos WHERE id = %s', (id,))
    vuelo = cur.fetchone()
    
    cur.close()
    conn.close()
    
    pasajeros_html = ''
    for p in pasajeros:
        pasajeros_html += f'''
        <tr>
            <td>{p['pasaporte']}</td>
            <td>{p['nombre']} {p['apellido']}</td>
            <td>{p['nacionalidad'] if p['nacionalidad'] else 'N/A'}</td>
            <td>{p['email'] if p['email'] else 'N/A'}</td>
            <td><span class="badge bg-secondary">{p['asiento'] if p['asiento'] else 'N/A'}</span></td>
            <td><span class="badge bg-info">{p['clase']}</span></td>
            <td><code>{p['codigo_reserva']}</code></td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-people"></i> Pasajeros del Vuelo</h1>
            <p class="lead">{vuelo['numero_vuelo']} | {vuelo['origen']} → {vuelo['destino']}</p>
        </div>
        <div class="col-md-4 text-end">
            <a href="/vuelos" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver a Vuelos
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if pasajeros:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Pasaporte</th>
                            <th>Nombre</th>
                            <th>Nacionalidad</th>
                            <th>Email</th>
                            <th>Asiento</th>
                            <th>Clase</th>
                            <th>Codigo Reserva</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pasajeros_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-people fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No hay pasajeros en este vuelo</h4>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Pasajeros del Vuelo', content)

# ==================== CRUD PASAJEROS ====================
@app.route('/pasajeros')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_pasajeros():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    busqueda = request.args.get('busqueda', '')
    
    query = '''
        SELECT p.*, 
               COUNT(r.id) as total_reservas,
               MAX(r.fecha_reserva) as ultima_reserva
        FROM pasajeros p
        LEFT JOIN reservas r ON p.id = r.pasajero_id AND r.estado = 'confirmada'
    '''
    
    params = []
    
    if busqueda:
        query += " WHERE p.nombre ILIKE %s OR p.apellido ILIKE %s OR p.pasaporte ILIKE %s OR p.email ILIKE %s"
        params.extend([f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'])
    
    query += " GROUP BY p.id ORDER BY p.apellido, p.nombre"
    
    cur.execute(query, params)
    pasajeros = cur.fetchall()
    
    cur.close()
    conn.close()
    
    pasajeros_html = ''
    for p in pasajeros:
        pasajeros_html += f'''
        <tr>
            <td><code>{p['pasaporte']}</code></td>
            <td>{p['nombre']}</td>
            <td>{p['apellido']}</td>
            <td><span class="badge bg-info">{p['nacionalidad'] if p['nacionalidad'] else 'N/A'}</span></td>
            <td>{p['email'] if p['email'] else 'N/A'}</td>
            <td>{p['telefono'] if p['telefono'] else 'N/A'}</td>
            <td>
                <span class="badge bg-{'success' if p['total_reservas'] > 0 else 'secondary'}">
                    {p['total_reservas']}
                </span>
                {('<br><small class="text-muted">' + p['ultima_reserva'].strftime('%d/%m/%y') + '</small>' 
                  if p['ultima_reserva'] else '')}
            </td>
            <td>
                <div class="btn-group btn-group-sm">
        '''
        if current_user.rol in ['admin', 'responsable', 'empleado']:
            pasajeros_html += f'''
                    <a href="/pasajeros/editar/{p['id']}" class="btn btn-warning" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </a>
            '''
        if current_user.rol == 'admin':
            pasajeros_html += f'''
                    <form method="POST" action="/pasajeros/eliminar/{p['id']}" class="d-inline">
                        <button type="submit" class="btn btn-danger" title="Eliminar"
                                onclick="return confirm('¿Está seguro de eliminar este pasajero?')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </form>
            '''
        pasajeros_html += '''
                </div>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-people"></i> Gestionar Pasajeros</h1>
        </div>
        <div class="col-md-4 text-end">
            <a href="/pasajeros/nuevo" class="btn btn-success">
                <i class="bi bi-plus-circle"></i> Nuevo Pasajero
            </a>
            <a href="/dashboard" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver
            </a>
        </div>
    </div>

    <div class="card mb-4">
        <div class="card-header">
            <h5><i class="bi bi-search"></i> Buscar Pasajeros</h5>
        </div>
        <div class="card-body">
            <form method="GET" class="row g-3">
                <div class="col-md-10">
                    <input type="text" class="form-control" id="busqueda" name="busqueda" 
                           placeholder="Buscar por nombre, apellido, pasaporte o email..." 
                           value="{busqueda}">
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="bi bi-search"></i> Buscar
                    </button>
                </div>
            </form>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if pasajeros:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Pasaporte</th>
                            <th>Nombre</th>
                            <th>Apellido</th>
                            <th>Nacionalidad</th>
                            <th>Email</th>
                            <th>Telefono</th>
                            <th>Reservas</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pasajeros_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-people fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron pasajeros</h4>
                <p>Intenta cambiar la busqueda o crear un nuevo pasajero</p>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Gestionar Pasajeros', content)

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
                RETURNING id
            ''', (
                request.form['pasaporte'].upper(),
                request.form['nombre'],
                request.form['apellido'],
                request.form['nacionalidad'],
                request.form['fecha_nacimiento'] if request.form['fecha_nacimiento'] else None,
                request.form['telefono'],
                request.form['email']
            ))
            
            pasajero_id = cur.fetchone()[0]
            conn.commit()
            
            detalles = {k: v for k, v in request.form.items()}
            registrar_log('CREAR', 'pasajeros', pasajero_id, detalles)
            flash('Pasajero creado exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/pasajeros')
            
        except Exception as e:
            flash(f'Error al crear pasajero: {str(e)}', 'danger')
    
    content = '''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-person-plus"></i> Nuevo Pasajero</h1>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion Personal</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="pasaporte" class="form-label">Pasaporte *</label>
                                <input type="text" class="form-control" id="pasaporte" name="pasaporte" required>
                                <div class="form-text">Numero de pasaporte unico</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nacionalidad" class="form-label">Nacionalidad</label>
                                <input type="text" class="form-control" id="nacionalidad" name="nacionalidad">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nombre" class="form-label">Nombre *</label>
                                <input type="text" class="form-control" id="nombre" name="nombre" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="apellido" class="form-label">Apellido *</label>
                                <input type="text" class="form-control" id="apellido" name="apellido" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_nacimiento" class="form-label">Fecha de Nacimiento</label>
                                <input type="date" class="form-control" id="fecha_nacimiento" name="fecha_nacimiento">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="telefono" class="form-label">Telefono</label>
                                <input type="tel" class="form-control" id="telefono" name="telefono">
                            </div>
                            
                            <div class="col-md-12">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email">
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/pasajeros" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Crear Pasajero
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Nuevo Pasajero', content)

@app.route('/pasajeros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def editar_pasajero(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        try:
            cur.execute('''
                UPDATE pasajeros 
                SET pasaporte = %s, nombre = %s, apellido = %s, nacionalidad = %s,
                    fecha_nacimiento = %s, telefono = %s, email = %s
                WHERE id = %s
            ''', (
                request.form['pasaporte'].upper(),
                request.form['nombre'],
                request.form['apellido'],
                request.form['nacionalidad'],
                request.form['fecha_nacimiento'] if request.form['fecha_nacimiento'] else None,
                request.form['telefono'],
                request.form['email'],
                id
            ))
            
            conn.commit()
            detalles = {k: v for k, v in request.form.items()}
            registrar_log('ACTUALIZAR', 'pasajeros', id, detalles)
            flash('Pasajero actualizado exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/pasajeros')
            
        except Exception as e:
            flash(f'Error al actualizar pasajero: {str(e)}', 'danger')
    
    cur.execute('SELECT * FROM pasajeros WHERE id = %s', (id,))
    pasajero = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not pasajero:
        flash('Pasajero no encontrado', 'danger')
        return redirect('/pasajeros')
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-person"></i> Editar Pasajero</h1>
            <p class="lead">{pasajero['nombre']} {pasajero['apellido']}</p>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion Personal</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="pasaporte" class="form-label">Pasaporte *</label>
                                <input type="text" class="form-control" id="pasaporte" name="pasaporte" 
                                       value="{pasajero['pasaporte']}" required>
                                <div class="form-text">Numero de pasaporte unico</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nacionalidad" class="form-label">Nacionalidad</label>
                                <input type="text" class="form-control" id="nacionalidad" name="nacionalidad" 
                                       value="{pasajero['nacionalidad'] if pasajero['nacionalidad'] else ''}">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nombre" class="form-label">Nombre *</label>
                                <input type="text" class="form-control" id="nombre" name="nombre" 
                                       value="{pasajero['nombre']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="apellido" class="form-label">Apellido *</label>
                                <input type="text" class="form-control" id="apellido" name="apellido" 
                                       value="{pasajero['apellido']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_nacimiento" class="form-label">Fecha de Nacimiento</label>
                                <input type="date" class="form-control" id="fecha_nacimiento" name="fecha_nacimiento" 
                                       value="{pasajero['fecha_nacimiento'].strftime('%Y-%m-%d') if pasajero['fecha_nacimiento'] else ''}">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="telefono" class="form-label">Telefono</label>
                                <input type="tel" class="form-control" id="telefono" name="telefono" 
                                       value="{pasajero['telefono'] if pasajero['telefono'] else ''}">
                            </div>
                            
                            <div class="col-md-12">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email" 
                                       value="{pasajero['email'] if pasajero['email'] else ''}">
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/pasajeros" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Actualizar Pasajero
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Editar Pasajero', content)

@app.route('/pasajeros/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_pasajero(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si tiene reservas activas
        cur.execute("SELECT COUNT(*) FROM reservas WHERE pasajero_id = %s AND estado = 'confirmada'", (id,))
        reservas_count = cur.fetchone()[0]
        
        if reservas_count > 0:
            flash('No se puede eliminar el pasajero porque tiene reservas activas', 'danger')
        else:
            # Obtener info antes de eliminar para el log
            cur.execute("SELECT nombre, apellido, pasaporte FROM pasajeros WHERE id = %s", (id,))
            pasajero_info = cur.fetchone()
            
            cur.execute("DELETE FROM pasajeros WHERE id = %s", (id,))
            conn.commit()
            
            if pasajero_info:
                registrar_log('ELIMINAR', 'pasajeros', id, {
                    'nombre': pasajero_info[0],
                    'apellido': pasajero_info[1],
                    'pasaporte': pasajero_info[2]
                })
            flash('Pasajero eliminado exitosamente', 'success')
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error al eliminar pasajero: {str(e)}', 'danger')
    
    return redirect('/pasajeros')

# ==================== CRUD AEROLINEAS ====================
@app.route('/aerolineas')
@login_required
@role_required('admin', 'responsable')
def listar_aerolineas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT a.*, COUNT(v.id) as total_vuelos
        FROM aerolineas a
        LEFT JOIN vuelos v ON a.id = v.aerolinea_id
        GROUP BY a.id
        ORDER BY a.nombre
    ''')
    
    aerolineas = cur.fetchall()
    
    cur.close()
    conn.close()
    
    aerolineas_html = ''
    for a in aerolineas:
        aerolineas_html += f'''
        <tr>
            <td><strong>{a['codigo']}</strong></td>
            <td>{a['nombre']}</td>
            <td>{a['pais_origen'] if a['pais_origen'] else 'N/A'}</td>
            <td>{a['fecha_fundacion'].strftime('%d/%m/%Y') if a['fecha_fundacion'] else 'N/A'}</td>
            <td><span class="badge bg-{'info' if a['total_vuelos'] > 0 else 'secondary'}">{a['total_vuelos']}</span></td>
            <td>
                <span class="badge bg-{'success' if a['activa'] else 'danger'}">
                    {'Activa' if a['activa'] else 'Inactiva'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
        '''
        if current_user.rol in ['admin', 'responsable']:
            aerolineas_html += f'''
                    <a href="/aerolineas/editar/{a['id']}" class="btn btn-warning" title="Editar">
                        <i class="bi bi-pencil"></i>
                    </a>
            '''
        if current_user.rol == 'admin':
            aerolineas_html += f'''
                    <form method="POST" action="/aerolineas/eliminar/{a['id']}" class="d-inline">
                        <button type="submit" class="btn btn-danger" title="Eliminar"
                                onclick="return confirm('¿Está seguro de eliminar esta aerolinea?')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </form>
            '''
        aerolineas_html += '''
                </div>
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-building"></i> Aerolineas</h1>
        </div>
        <div class="col-md-4 text-end">
            <a href="/aerolineas/nuevo" class="btn btn-success">
                <i class="bi bi-plus-circle"></i> Nueva Aerolinea
            </a>
            <a href="/dashboard" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if aerolineas:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Codigo</th>
                            <th>Nombre</th>
                            <th>Pais Origen</th>
                            <th>Fecha Fundacion</th>
                            <th>Vuelos</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {aerolineas_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-building fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron aerolineas</h4>
                <p>Crear una nueva aerolinea para comenzar</p>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Aerolineas', content)

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
                RETURNING id
            ''', (
                request.form['codigo'].upper(),
                request.form['nombre'],
                request.form['pais_origen'],
                request.form['fecha_fundacion'] if request.form['fecha_fundacion'] else None
            ))
            
            aerolinea_id = cur.fetchone()[0]
            conn.commit()
            
            detalles = {k: v for k, v in request.form.items()}
            registrar_log('CREAR', 'aerolineas', aerolinea_id, detalles)
            flash('Aerolinea creada exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/aerolineas')
            
        except Exception as e:
            flash(f'Error al crear aerolinea: {str(e)}', 'danger')
    
    content = '''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-building"></i> Nueva Aerolinea</h1>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion de la Aerolinea</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="codigo" class="form-label">Codigo IATA *</label>
                                <input type="text" class="form-control" id="codigo" name="codigo" maxlength="3" required>
                                <div class="form-text">Codigo de 3 letras (ej: AA, DL, UA)</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nombre" class="form-label">Nombre *</label>
                                <input type="text" class="form-control" id="nombre" name="nombre" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="pais_origen" class="form-label">Pais de Origen</label>
                                <input type="text" class="form-control" id="pais_origen" name="pais_origen">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_fundacion" class="form-label">Fecha de Fundacion</label>
                                <input type="date" class="form-control" id="fecha_fundacion" name="fecha_fundacion">
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/aerolineas" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Crear Aerolinea
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Nueva Aerolinea', content)

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
                UPDATE aerolineas 
                SET codigo = %s, nombre = %s, pais_origen = %s, fecha_fundacion = %s, activa = %s
                WHERE id = %s
            ''', (
                request.form['codigo'].upper(),
                request.form['nombre'],
                request.form['pais_origen'],
                request.form['fecha_fundacion'] if request.form['fecha_fundacion'] else None,
                activa,
                id
            ))
            
            conn.commit()
            detalles = {k: v for k, v in request.form.items()}
            detalles['activa'] = activa
            registrar_log('ACTUALIZAR', 'aerolineas', id, detalles)
            flash('Aerolinea actualizada exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/aerolineas')
            
        except Exception as e:
            flash(f'Error al actualizar aerolinea: {str(e)}', 'danger')
    
    cur.execute('SELECT * FROM aerolineas WHERE id = %s', (id,))
    aerolinea = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not aerolinea:
        flash('Aerolinea no encontrada', 'danger')
        return redirect('/aerolineas')
    
    checked = 'checked' if aerolinea['activa'] else ''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-building"></i> Editar Aerolinea</h1>
            <p class="lead">{aerolinea['nombre']}</p>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion de la Aerolinea</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="codigo" class="form-label">Codigo IATA *</label>
                                <input type="text" class="form-control" id="codigo" name="codigo" 
                                       value="{aerolinea['codigo']}" maxlength="3" required>
                                <div class="form-text">Codigo de 3 letras (ej: AA, DL, UA)</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nombre" class="form-label">Nombre *</label>
                                <input type="text" class="form-control" id="nombre" name="nombre" 
                                       value="{aerolinea['nombre']}" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="pais_origen" class="form-label">Pais de Origen</label>
                                <input type="text" class="form-control" id="pais_origen" name="pais_origen" 
                                       value="{aerolinea['pais_origen'] if aerolinea['pais_origen'] else ''}">
                            </div>
                            
                            <div class="col-md-6">
                                <label for="fecha_fundacion" class="form-label">Fecha de Fundacion</label>
                                <input type="date" class="form-control" id="fecha_fundacion" name="fecha_fundacion" 
                                       value="{aerolinea['fecha_fundacion'].strftime('%Y-%m-%d') if aerolinea['fecha_fundacion'] else ''}">
                            </div>
                            
                            <div class="col-md-12">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="activa" name="activa" {checked}>
                                    <label class="form-check-label" for="activa">
                                        Aerolinea Activa
                                    </label>
                                </div>
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="d-flex justify-content-between">
                            <a href="/aerolineas" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Actualizar Aerolinea
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Editar Aerolinea', content)

@app.route('/aerolineas/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_aerolinea(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si tiene vuelos
        cur.execute("SELECT COUNT(*) FROM vuelos WHERE aerolinea_id = %s", (id,))
        vuelos_count = cur.fetchone()[0]
        
        if vuelos_count > 0:
            flash('No se puede eliminar la aerolinea porque tiene vuelos asociados', 'danger')
        else:
            # Obtener info antes de eliminar para el log
            cur.execute("SELECT codigo, nombre FROM aerolineas WHERE id = %s", (id,))
            aerolinea_info = cur.fetchone()
            
            cur.execute("DELETE FROM aerolineas WHERE id = %s", (id,))
            conn.commit()
            
            if aerolinea_info:
                registrar_log('ELIMINAR', 'aerolineas', id, {
                    'codigo': aerolinea_info[0],
                    'nombre': aerolinea_info[1]
                })
            flash('Aerolinea eliminada exitosamente', 'success')
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error al eliminar aerolinea: {str(e)}', 'danger')
    
    return redirect('/aerolineas')

# ==================== CRUD RESERVAS ====================
@app.route('/reservas')
@login_required
@role_required('admin', 'responsable', 'empleado')
def listar_reservas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT r.*, 
               v.numero_vuelo, v.origen, v.destino, v.fecha_salida,
               p.nombre as pasajero_nombre, p.apellido as pasajero_apellido, p.pasaporte,
               a.nombre as aerolinea_nombre, a.codigo as aerolinea_codigo
        FROM reservas r
        JOIN vuelos v ON r.vuelo_id = v.id
        JOIN pasajeros p ON r.pasajero_id = p.id
        JOIN aerolineas a ON v.aerolinea_id = a.id
        ORDER BY r.fecha_reserva DESC
    ''')
    
    reservas = cur.fetchall()
    
    cur.close()
    conn.close()
    
    reservas_html = ''
    for r in reservas:
        estado_color = 'success' if r['estado'] == 'confirmada' else 'danger' if r['estado'] == 'cancelada' else 'info'
        clase_color = 'warning' if r['clase'] == 'economica' else 'info' if r['clase'] == 'ejecutiva' else 'success'
        
        # CORREGIDO: Formatear el precio correctamente
        if r['precio'] is not None:
            precio_str = f"\${r['precio']:.2f}"
        else:
            precio_str = "\$0.00"
        
        reservas_html += f'''
        <tr>
            <td><code>{r['codigo_reserva']}</code></td>
            <td>
                <strong>{r['numero_vuelo']}</strong><br>
                <small>{r['origen']} → {r['destino']}</small><br>
                <small>{r['fecha_salida'].strftime('%d/%m %H:%M')}</small>
            </td>
            <td>
                {r['pasajero_nombre']} {r['pasajero_apellido']}<br>
                <small class="text-muted">{r['pasaporte']}</small>
            </td>
            <td>{r['fecha_reserva'].strftime('%d/%m %H:%M')}</td>
            <td><span class="badge bg-secondary">{r['asiento'] if r['asiento'] else 'N/A'}</span></td>
            <td><span class="badge bg-{clase_color}">{r['clase']}</span></td>
            <td>{precio_str}</td>
            <td><span class="badge bg-{estado_color}">{r['estado']}</span></td>
            <td>
        '''
        if r['estado'] == 'confirmada' and current_user.rol in ['admin', 'responsable', 'empleado']:
            reservas_html += f'''
                <form method="POST" action="/reservas/cancelar/{r['id']}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" title="Cancelar"
                            onclick="return confirm('¿Está seguro de cancelar esta reserva?')">
                        <i class="bi bi-x-circle"></i>
                    </button>
                </form>
            '''
        reservas_html += '''
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-ticket-perforated"></i> Reservas</h1>
        </div>
        <div class="col-md-4 text-end">
            <a href="/reservas/nueva" class="btn btn-success">
                <i class="bi bi-plus-circle"></i> Nueva Reserva
            </a>
            <a href="/dashboard" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if reservas:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Codigo</th>
                            <th>Vuelo</th>
                            <th>Pasajero</th>
                            <th>Fecha Reserva</th>
                            <th>Asiento</th>
                            <th>Clase</th>
                            <th>Precio</th>
                            <th>Estado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {reservas_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-ticket-perforated fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron reservas</h4>
                <p>Crear una nueva reserva para comenzar</p>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Reservas', content)

@app.route('/reservas/nueva', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def nueva_reserva():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Generar codigo de reserva unico
            codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            cur.execute('''
                INSERT INTO reservas (codigo_reserva, vuelo_id, pasajero_id, asiento, clase, precio)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                codigo,
                request.form['vuelo_id'],
                request.form['pasajero_id'],
                request.form['asiento'],
                request.form['clase'],
                float(request.form['precio'])
            ))
            
            reserva_id = cur.fetchone()[0]
            
            # Actualizar asientos disponibles
            cur.execute('''
                UPDATE vuelos 
                SET asientos_disponibles = asientos_disponibles - 1 
                WHERE id = %s
            ''', (request.form['vuelo_id'],))
            
            conn.commit()
            
            detalles = {k: v for k, v in request.form.items()}
            detalles['codigo_reserva'] = codigo
            registrar_log('CREAR', 'reservas', reserva_id, detalles)
            flash(f'Reserva creada exitosamente. Codigo: {codigo}', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/reservas')
            
        except Exception as e:
            flash(f'Error al crear reserva: {str(e)}', 'danger')
    
    # Obtener vuelos y pasajeros para los selects
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute("SELECT id, numero_vuelo, origen, destino, fecha_salida, asientos_disponibles FROM vuelos WHERE estado = 'programado' AND asientos_disponibles > 0 ORDER BY fecha_salida")
    vuelos = cur.fetchall()
    
    cur.execute("SELECT id, nombre, apellido, pasaporte FROM pasajeros ORDER BY apellido, nombre")
    pasajeros = cur.fetchall()
    
    cur.close()
    conn.close()
    
    vuelos_options = '<option value="">Seleccionar vuelo...</option>'
    for v in vuelos:
        vuelos_options += f'<option value="{v["id"]}">{v["numero_vuelo"]} | {v["origen"]} → {v["destino"]} | {v["fecha_salida"].strftime("%d/%m %H:%M")} | Asientos: {v["asientos_disponibles"]}</option>'
    
    pasajeros_options = '<option value="">Seleccionar pasajero...</option>'
    for p in pasajeros:
        pasajeros_options += f'<option value="{p["id"]}">{p["nombre"]} {p["apellido"]} | {p["pasaporte"]}</option>'
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-ticket-perforated"></i> Nueva Reserva</h1>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion de la Reserva</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="vuelo_id" class="form-label">Vuelo *</label>
                                <select class="form-select" id="vuelo_id" name="vuelo_id" required>
                                    {vuelos_options}
                                </select>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="pasajero_id" class="form-label">Pasajero *</label>
                                <select class="form-select" id="pasajero_id" name="pasajero_id" required>
                                    {pasajeros_options}
                                </select>
                            </div>
                            
                            <div class="col-md-4">
                                <label for="asiento" class="form-label">Asiento</label>
                                <input type="text" class="form-control" id="asiento" name="asiento" placeholder="Ej: 12A">
                            </div>
                            
                            <div class="col-md-4">
                                <label for="clase" class="form-label">Clase</label>
                                <select class="form-select" id="clase" name="clase">
                                    <option value="economica">Economica</option>
                                    <option value="ejecutiva">Ejecutiva</option>
                                    <option value="primera">Primera Clase</option>
                                </select>
                            </div>
                            
                            <div class="col-md-4">
                                <label for="precio" class="form-label">Precio ($)</label>
                                <input type="number" class="form-control" id="precio" name="precio" step="0.01" min="0" value="250.00">
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 
                            Al crear una reserva, se generara automaticamente un codigo unico y se reducira 
                            en 1 la cantidad de asientos disponibles en el vuelo seleccionado.
                        </div>
                        
                        <div class="d-flex justify-content-between">
                            <a href="/reservas" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Crear Reserva
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        const claseSelect = document.getElementById('clase');
        const precioInput = document.getElementById('precio');
        
        claseSelect.addEventListener('change', function() {{
            let basePrice = 250.00;
            const clase = this.value;
            
            if (clase === 'ejecutiva') {{
                basePrice = 500.00;
            }} else if (clase === 'primera') {{
                basePrice = 1000.00;
            }}
            
            precioInput.value = basePrice.toFixed(2);
        }});
    }});
    </script>
    '''
    
    return get_base_html('Nueva Reserva', content, extra_js='')

@app.route('/reservas/cancelar/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'responsable', 'empleado')
def cancelar_reserva(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Obtener info de la reserva
        cur.execute('SELECT vuelo_id, codigo_reserva FROM reservas WHERE id = %s', (id,))
        reserva = cur.fetchone()
        
        if reserva:
            cur.execute('''
                UPDATE reservas 
                SET estado = 'cancelada' 
                WHERE id = %s
            ''', (id,))
            
            # Liberar asiento
            cur.execute('''
                UPDATE vuelos 
                SET asientos_disponibles = asientos_disponibles + 1 
                WHERE id = %s
            ''', (reserva['vuelo_id'],))
            
            conn.commit()
            
            registrar_log('CANCELAR', 'reservas', id, {'codigo_reserva': reserva['codigo_reserva']})
            flash('Reserva cancelada exitosamente', 'success')
        else:
            flash('Reserva no encontrada', 'danger')
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error al cancelar reserva: {str(e)}', 'danger')
    
    return redirect('/reservas')

# ==================== LOGS ====================
@app.route('/logs')
@login_required
@role_required('admin', 'responsable')
def ver_logs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT l.*, u.username, u.nombre as usuario_nombre, u.rol
        FROM logs_auditoria l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        ORDER BY l.fecha_hora DESC
        LIMIT 100
    ''')
    
    logs = cur.fetchall()
    
    cur.close()
    conn.close()
    
    logs_html = ''
    for log in logs:
        accion_color = 'success' if log['accion'] == 'LOGIN' else 'primary' if log['accion'] == 'CREAR' else 'warning' if log['accion'] == 'ACTUALIZAR' else 'danger' if log['accion'] in ['ELIMINAR', 'CANCELAR'] else 'info'
        rol_color = 'danger' if log['rol'] == 'admin' else 'warning' if log['rol'] == 'responsable' else 'info' if log['rol'] == 'empleado' else 'secondary'
        
        logs_html += f'''
        <tr>
            <td>
                <small>{log['fecha_hora'].strftime('%d/%m/%Y')}</small><br>
                <small class="text-muted">{log['fecha_hora'].strftime('%H:%M:%S')}</small>
            </td>
            <td>
                {log['usuario_nombre'] if log['usuario_nombre'] else '<span class="text-muted">Usuario eliminado</span>'}<br>
                <small class="text-muted">{log['username'] if log['username'] else 'N/A'}</small>
            </td>
            <td><span class="badge bg-{rol_color}">{log['rol'] if log['rol'] else 'N/A'}</span></td>
            <td><span class="badge bg-{accion_color}">{log['accion']}</span></td>
            <td>{log['tabla_afectada'] if log['tabla_afectada'] else 'N/A'}</td>
            <td>{log['registro_id'] if log['registro_id'] else 'N/A'}</td>
            <td><small class="text-muted">{log['ip_address']}</small></td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-clock-history"></i> Logs del Sistema</h1>
            <p class="lead">Registro de todas las operaciones realizadas</p>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if logs:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Fecha/Hora</th>
                            <th>Usuario</th>
                            <th>Rol</th>
                            <th>Accion</th>
                            <th>Tabla</th>
                            <th>Registro ID</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs_html}
                    </tbody>
                </table>
            </div>
            
            <div class="mt-3 text-muted">
                <small>Mostrando los ultimos 100 registros</small>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-clock-history fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron logs</h4>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    '''
    
    return get_base_html('Logs del Sistema', content)

# ==================== USUARIOS ====================
@app.route('/usuarios')
@login_required
@role_required('admin')
def listar_usuarios():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cur.execute('''
        SELECT u.*, COUNT(l.id) as total_logs
        FROM usuarios u
        LEFT JOIN logs_auditoria l ON u.id = l.usuario_id
        GROUP BY u.id
        ORDER BY u.fecha_creacion DESC
    ''')
    
    usuarios = cur.fetchall()
    
    cur.close()
    conn.close()
    
    usuarios_html = ''
    for u in usuarios:
        rol_color = 'danger' if u['rol'] == 'admin' else 'warning' if u['rol'] == 'responsable' else 'info' if u['rol'] == 'empleado' else 'secondary'
        estado_badge = 'success' if u['activo'] else 'danger'
        
        usuarios_html += f'''
        <tr>
            <td><code>{u['username']}</code></td>
            <td>{u['nombre']}</td>
            <td>{u['email'] if u['email'] else 'N/A'}</td>
            <td><span class="badge bg-{rol_color}">{u['rol']}</span></td>
            <td>{u['fecha_creacion'].strftime('%d/%m/%Y %H:%M')}</td>
            <td><span class="badge bg-{estado_badge}">{'Activo' if u['activo'] else 'Inactivo'}</span></td>
            <td><span class="badge bg-info">{u['total_logs']}</span></td>
            <td>
        '''
        if u['id'] != current_user.id:
            usuarios_html += f'''
                <form method="POST" action="/usuarios/eliminar/{u['id']}" class="d-inline">
                    <button type="submit" class="btn btn-danger btn-sm" title="Eliminar"
                            onclick="return confirm('¿Está seguro de eliminar este usuario?')">
                        <i class="bi bi-trash"></i>
                    </button>
                </form>
            '''
        else:
            usuarios_html += '''
                <button class="btn btn-outline-secondary btn-sm" disabled title="No puedes eliminar tu propio usuario">
                    <i class="bi bi-person-check"></i>
                </button>
            '''
        usuarios_html += '''
            </td>
        </tr>
        '''
    
    content = f'''
    <div class="row mb-4">
        <div class="col-md-8">
            <h1><i class="bi bi-people-fill"></i> Usuarios del Sistema</h1>
            <p class="lead">Gestion de usuarios y permisos</p>
        </div>
        <div class="col-md-4 text-end">
            <a href="/usuarios/nuevo" class="btn btn-success">
                <i class="bi bi-plus-circle"></i> Nuevo Usuario
            </a>
            <a href="/dashboard" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Volver
            </a>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
    '''
    
    if usuarios:
        content += f'''
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Usuario</th>
                            <th>Nombre</th>
                            <th>Email</th>
                            <th>Rol</th>
                            <th>Fecha Creacion</th>
                            <th>Estado</th>
                            <th>Logs</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {usuarios_html}
                    </tbody>
                </table>
            </div>
        '''
    else:
        content += '''
            <div class="text-center py-5">
                <i class="bi bi-people-fill fs-1 text-muted"></i>
                <h4 class="text-muted mt-3">No se encontraron usuarios</h4>
                <p>Crear un nuevo usuario para comenzar</p>
            </div>
        '''
    
    content += '''
        </div>
    </div>
    
    <div class="row mt-4">
        <div class="col-md-3">
            <div class="card border-danger">
                <div class="card-body">
                    <h6 class="card-title">Administrador</h6>
                    <p class="card-text small">Control total del sistema. Puede crear, modificar y eliminar cualquier registro.</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card border-warning">
                <div class="card-body">
                    <h6 class="card-title">Responsable</h6>
                    <p class="card-text small">Puede gestionar registros pero no eliminar tablas completas ni realizar borrados masivos.</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card border-info">
                <div class="card-body">
                    <h6 class="card-title">Empleado</h6>
                    <p class="card-text small">Puede realizar operaciones de venta, check-in y gestion basica de pasajeros.</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card border-secondary">
                <div class="card-body">
                    <h6 class="card-title">Consulta</h6>
                    <p class="card-text small">Solo puede ver informacion. No puede realizar modificaciones.</p>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Usuarios', content)

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def nuevo_usuario():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            password_hash = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cur.execute('''
                INSERT INTO usuarios (username, password_hash, nombre, email, rol)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                request.form['username'],
                password_hash,
                request.form['nombre'],
                request.form['email'],
                request.form['rol']
            ))
            
            usuario_id = cur.fetchone()[0]
            conn.commit()
            
            detalles = {k: v for k, v in request.form.items() if k != 'password'}
            registrar_log('CREAR', 'usuarios', usuario_id, detalles)
            flash('Usuario creado exitosamente', 'success')
            
            cur.close()
            conn.close()
            
            return redirect('/usuarios')
            
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'danger')
    
    content = '''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-person-plus"></i> Nuevo Usuario</h1>
        </div>
    </div>

    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5>Informacion del Usuario</h5>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label for="username" class="form-label">Nombre de Usuario *</label>
                                <input type="text" class="form-control" id="username" name="username" required>
                                <div class="form-text">Nombre unico para iniciar sesion</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="password" class="form-label">Contrasena *</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                                <div class="form-text">Minimo 6 caracteres</div>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="nombre" class="form-label">Nombre Completo *</label>
                                <input type="text" class="form-control" id="nombre" name="nombre" required>
                            </div>
                            
                            <div class="col-md-6">
                                <label for="email" class="form-label">Email</label>
                                <input type="email" class="form-control" id="email" name="email">
                            </div>
                            
                            <div class="col-md-12">
                                <label for="rol" class="form-label">Rol *</label>
                                <select class="form-select" id="rol" name="rol" required>
                                    <option value="">Seleccionar rol...</option>
                                    <option value="admin">Administrador (Control total)</option>
                                    <option value="responsable">Responsable (Gestionar sin borrado masivo)</option>
                                    <option value="empleado">Empleado (Operaciones basicas)</option>
                                    <option value="consulta">Consulta (Solo lectura)</option>
                                </select>
                            </div>
                        </div>
                        
                        <hr class="my-4">
                        
                        <div class="alert alert-warning">
                            <i class="bi bi-exclamation-triangle"></i> 
                            <strong>Importante:</strong> Los permisos de cada rol estan predefinidos en el sistema.
                            Asegurate de asignar el rol correcto segun las responsabilidades del usuario.
                        </div>
                        
                        <div class="d-flex justify-content-between">
                            <a href="/usuarios" class="btn btn-secondary">
                                <i class="bi bi-arrow-left"></i> Cancelar
                            </a>
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-check-circle"></i> Crear Usuario
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    
    return get_base_html('Nuevo Usuario', content)

@app.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_usuario(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # No permitir eliminar al propio usuario admin
        if id == current_user.id:
            flash('No puedes eliminar tu propio usuario', 'danger')
        else:
            # Obtener info antes de eliminar para el log
            cur.execute("SELECT username, nombre, rol FROM usuarios WHERE id = %s", (id,))
            usuario_info = cur.fetchone()
            
            cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))
            conn.commit()
            
            if usuario_info:
                registrar_log('ELIMINAR', 'usuarios', id, {
                    'username': usuario_info[0],
                    'nombre': usuario_info[1],
                    'rol': usuario_info[2]
                })
            flash('Usuario eliminado exitosamente', 'success')
        
        cur.close()
        conn.close()
        
    except Exception as e:
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
    
    return redirect('/usuarios')

# ==================== LOGOUT ====================
@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    registrar_log('LOGOUT', detalles={'username': username})
    logout_user()
    flash('Has cerrado sesion exitosamente', 'info')
    return redirect('/login')

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)