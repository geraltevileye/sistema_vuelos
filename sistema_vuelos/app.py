# -*- coding: utf-8 -*-
"""
SISTEMA DE GESTIÓN DE VUELOS - VERSIÓN CORREGIDA Y SEGURA
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

# ==================== CONFIGURACIÓN INICIAL ====================

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración desde variables de entorno
app.secret_key = os.environ.get('SECRET_KEY', 'clave-temporal-cambiar-en-produccion')
app.config['SESSION_COOKIE_SECURE'] = True  # Solo HTTPS en producción
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
        # Obtener credenciales de variables de entorno
        db_config = {
            'host': os.environ.get('DB_HOST'),
            'database': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'port': os.environ.get('DB_PORT', 5432)
        }
        
        # Verificar que todas las credenciales estén presentes
        missing = [key for key, value in db_config.items() if not value and key != 'port']
        if missing:
            raise ValueError(f"Faltan credenciales: {', '.join(missing)}")
        
        # Establecer conexión
        conn = psycopg2.connect(**db_config)
        
        # Configurar parámetros de conexión
        conn.autocommit = False
        
        return conn
        
    except psycopg2.Error as e:
        print(f"Error de conexión a PostgreSQL: {e}")
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")
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
        
        cur.execute('''
            SELECT id, username, nombre, rol 
            FROM usuarios 
            WHERE id = %s AND activo = TRUE
        ''', (user_id,))
        
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                nombre=user_data['nombre'],
                rol=user_data['rol']
            )
        
        return None
        
    except Exception as e:
        print(f"Error cargando usuario: {e}")
        return None

# ==================== DECORADORES ====================

def role_required(*roles):
    """Decorador para verificar permisos de rol"""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.rol not in roles:
                flash('No tienes permisos para acceder a esta página.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# ==================== FUNCIONES AUXILIARES ====================

def registrar_log(accion, tabla=None, registro_id=None, detalles=None):
    """Registrar actividad en logs de auditoría"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Preparar detalles como JSON
        detalles_json = None
        if detalles:
            try:
                detalles_json = json.dumps(detalles, ensure_ascii=False, default=str)
            except:
                detalles_json = str(detalles)
        
        # Insertar log
        cur.execute('''
            INSERT INTO logs_auditoria 
            (usuario_id, accion, tabla_afectada, registro_id, detalles, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            current_user.id if current_user.is_authenticated else None,
            accion,
            tabla,
            registro_id,
            detalles_json,
            request.remote_addr if request else '127.0.0.1'
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        # No fallar si hay error en los logs
        print(f"Error registrando log: {e}")

def get_flashed_messages_html():
    """Generar HTML para mensajes flash"""
    messages = get_flashed_messages(with_categories=True)
    if not messages:
        return ''
    
    html_parts = []
    for category, message in messages:
        alert_class = {
            'success': 'alert-success',
            'danger': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }.get(category, 'alert-info')
        
        html_parts.append(f'''
        <div class="alert {alert_class} alert-dismissible fade show" role="alert">
            {message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        ''')
    
    return '\n'.join(html_parts)

# ==================== RUTAS PRINCIPALES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Por favor, completa todos los campos.', 'warning')
            return redirect(url_for('login'))
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            cur.execute('''
                SELECT id, username, nombre, rol, password_hash 
                FROM usuarios 
                WHERE username = %s AND activo = TRUE
            ''', (username,))
            
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                user_obj = User(user['id'], user['username'], user['nombre'], user['rol'])
                login_user(user_obj, remember=True)
                
                registrar_log('LOGIN', detalles={
                    'username': username,
                    'rol': user['rol']
                })
                
                flash(f'¡Bienvenido, {user["nombre"]}!', 'success')
                return redirect(url_for('dashboard'))
            
            flash('Usuario o contraseña incorrectos.', 'danger')
            
        except Exception as e:
            flash('Error al iniciar sesión. Por favor, intenta nuevamente.', 'danger')
            print(f"Error en login: {e}")
    
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
                display: flex;
                align-items: center;
                padding: 20px;
            }
            .login-card {
                max-width: 400px;
                margin: 0 auto;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
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
                        </div>
                        <div class="card-body p-4">
                            <h5 class="card-title text-center mb-4">Iniciar Sesión</h5>
                            ''' + get_flashed_messages_html() + '''
                            
                            <form method="POST" action="/login">
                                <div class="mb-3">
                                    <label for="username" class="form-label">Usuario</label>
                                    <div class="input-group">
                                        <span class="input-group-text">
                                            <i class="bi bi-person"></i>
                                        </span>
                                        <input type="text" class="form-control" id="username" 
                                               name="username" required autofocus>
                                    </div>
                                </div>
                                
                                <div class="mb-4">
                                    <label for="password" class="form-label">Contraseña</label>
                                    <div class="input-group">
                                        <span class="input-group-text">
                                            <i class="bi bi-key"></i>
                                        </span>
                                        <input type="password" class="form-control" id="password" 
                                               name="password" required>
                                    </div>
                                </div>
                                
                                <div class="d-grid gap-2">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="bi bi-box-arrow-in-right"></i> Iniciar Sesión
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
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
    """Cerrar sesión"""
    username = current_user.username
    logout_user()
    registrar_log('LOGOUT', detalles={'username': username})
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# ==================== DASHBOARD ====================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Página principal del dashboard"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        hoy = datetime.now().date()
        
        # Obtener estadísticas
        estadisticas = {
            'vuelos_hoy': 0,
            'pasajeros_hoy': 0,
            'aerolineas_activas': 0,
            'reservas_hoy': 0
        }
        
        # Vuelos hoy
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM vuelos 
            WHERE DATE(fecha_salida) = %s
        """, (hoy,))
        resultado = cur.fetchone()
        estadisticas['vuelos_hoy'] = resultado['count'] if resultado else 0
        
        # Pasajeros hoy
        cur.execute("""
            SELECT COUNT(DISTINCT p.id) as count
            FROM pasajeros p 
            JOIN reservas r ON p.id = r.pasajero_id 
            JOIN vuelos v ON r.vuelo_id = v.id 
            WHERE DATE(v.fecha_salida) = %s 
            AND r.estado = 'confirmada'
        """, (hoy,))
        resultado = cur.fetchone()
        estadisticas['pasajeros_hoy'] = resultado['count'] if resultado else 0
        
        # Aerolíneas activas
        cur.execute("SELECT COUNT(*) as count FROM aerolineas WHERE activa = TRUE")
        resultado = cur.fetchone()
        estadisticas['aerolineas_activas'] = resultado['count'] if resultado else 0
        
        # Reservas hoy
        cur.execute("SELECT COUNT(*) as count FROM reservas WHERE DATE(fecha_reserva) = %s", (hoy,))
        resultado = cur.fetchone()
        estadisticas['reservas_hoy'] = resultado['count'] if resultado else 0
        
        # Próximos vuelos
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
        
        # Generar HTML del dashboard
        content = generar_dashboard_html(estadisticas, proximos_vuelos, hoy)
        
        return f'''
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Dashboard - Sistema Vuelos</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css">
            <style>
                body {{ background-color: #f8f9fa; min-height: 100vh; }}
                .navbar {{ box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
                .stat-card {{ transition: transform 0.3s; border: none; }}
                .stat-card:hover {{ transform: translateY(-5px); }}
                .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075); }}
            </style>
        </head>
        <body>
            <!-- Navbar -->
            <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
                <div class="container-fluid">
                    <a class="navbar-brand" href="/dashboard">
                        <i class="bi bi-airplane"></i> Sistema Vuelos
                    </a>
                    <div class="navbar-nav ms-auto">
                        <span class="navbar-text text-light me-3">
                            <i class="bi bi-person-circle"></i> {current_user.nombre}
                            <span class="badge bg-light text-dark ms-1">{current_user.rol}</span>
                        </span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">
                            <i class="bi bi-box-arrow-right"></i> Salir
                        </a>
                    </div>
                </div>
            </nav>
            
            <div class="container">
                {get_flashed_messages_html()}
                {content}
            </div>
            
            <footer class="footer mt-5 py-3 bg-light border-top">
                <div class="container text-center">
                    <span class="text-muted">
                        Sistema de Gestión de Vuelos &copy; {datetime.now().year}
                    </span>
                </div>
            </footer>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
        </body>
        </html>
        '''
        
    except Exception as e:
        flash(f'Error al cargar el dashboard: {str(e)}', 'danger')
        return redirect(url_for('login'))

def generar_dashboard_html(estadisticas, proximos_vuelos, hoy):
    """Generar HTML del dashboard"""
    
    # Tarjetas de estadísticas
    stats_html = f'''
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-white bg-primary stat-card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title">Vuelos Hoy</h6>
                            <h2 class="card-text">{estadisticas["vuelos_hoy"]}</h2>
                        </div>
                        <i class="bi bi-airplane fs-1 opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-success stat-card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title">Pasajeros Hoy</h6>
                            <h2 class="card-text">{estadisticas["pasajeros_hoy"]}</h2>
                        </div>
                        <i class="bi bi-people fs-1 opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-info stat-card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title">Aerolíneas Activas</h6>
                            <h2 class="card-text">{estadisticas["aerolineas_activas"]}</h2>
                        </div>
                        <i class="bi bi-building fs-1 opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card text-white bg-warning stat-card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="card-title">Reservas Hoy</h6>
                            <h2 class="card-text">{estadisticas["reservas_hoy"]}</h2>
                        </div>
                        <i class="bi bi-ticket-perforated fs-1 opacity-50"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    
    # Tabla de próximos vuelos
    vuelos_html = ''
    if proximos_vuelos:
        for vuelo in proximos_vuelos:
            estado_color = {
                'programado': 'success',
                'en_vuelo': 'warning',
                'aterrizado': 'info',
                'cancelado': 'danger'
            }.get(vuelo['estado'], 'secondary')
            
            vuelos_html += f'''
            <tr>
                <td><strong>{vuelo["numero_vuelo"]}</strong></td>
                <td>{vuelo["aerolinea_codigo"]} - {vuelo["aerolinea_nombre"]}</td>
                <td>{vuelo["origen"]}</td>
                <td>{vuelo["destino"]}</td>
                <td>{vuelo["fecha_salida"].strftime('%d/%m %H:%M')}</td>
                <td><span class="badge bg-{estado_color}">{vuelo["estado"]}</span></td>
                <td>{vuelo["asientos_disponibles"]}/{vuelo["capacidad"]}</td>
            </tr>
            '''
    else:
        vuelos_html = '''
        <tr>
            <td colspan="7" class="text-center text-muted py-4">
                No hay vuelos programados
            </td>
        </tr>
        '''
    
    # Accesos rápidos según rol
    accesos_html = '<div class="d-grid gap-2">'
    
    if current_user.rol in ['admin', 'responsable', 'empleado']:
        accesos_html += '''
        <a href="/vuelos" class="btn btn-outline-primary">
            <i class="bi bi-airplane"></i> Gestionar Vuelos
        </a>
        <a href="/pasajeros" class="btn btn-outline-success">
            <i class="bi bi-people"></i> Gestionar Pasajeros
        </a>
        <a href="/reservas" class="btn btn-outline-warning">
            <i class="bi bi-ticket-perforated"></i> Gestionar Reservas
        </a>
        '''
    
    if current_user.rol in ['admin', 'responsable']:
        accesos_html += '''
        <a href="/aerolineas" class="btn btn-outline-info">
            <i class="bi bi-building"></i> Aerolíneas
        </a>
        <a href="/logs" class="btn btn-outline-secondary">
            <i class="bi bi-clock-history"></i> Ver Logs
        </a>
        '''
    
    if current_user.rol == 'admin':
        accesos_html += '''
        <a href="/usuarios" class="btn btn-outline-dark">
            <i class="bi bi-people-fill"></i> Usuarios
        </a>
        '''
    
    accesos_html += '</div>'
    
    return f'''
    <div class="row mb-4">
        <div class="col-12">
            <h1><i class="bi bi-speedometer2"></i> Dashboard</h1>
            <p class="lead">Bienvenido, {current_user.nombre}!</p>
        </div>
    </div>
    
    {stats_html}
    
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header bg-light">
                    <h5 class="mb-0"><i class="bi bi-airplane-engines"></i> Próximos Vuelos</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Vuelo</th>
                                    <th>Aerolínea</th>
                                    <th>Origen</th>
                                    <th>Destino</th>
                                    <th>Salida</th>
                                    <th>Estado</th>
                                    <th>Asientos</th>
                                </tr>
                            </thead>
                            <tbody>
                                {vuelos_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header bg-light">
                    <h5 class="mb-0"><i class="bi bi-lightning-charge"></i> Accesos Rápidos</h5>
                </div>
                <div class="card-body">
                    {accesos_html}
                </div>
            </div>
        </div>
    </div>
    '''

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return '''
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-6 text-center">
                <h1 class="display-1">404</h1>
                <p class="lead">Página no encontrada</p>
                <a href="/dashboard" class="btn btn-primary">
                    <i class="bi bi-house"></i> Volver al Dashboard
                </a>
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
                <p class="text-muted">Por favor, intenta nuevamente más tarde.</p>
                <a href="/dashboard" class="btn btn-primary">
                    <i class="bi bi-house"></i> Volver al Dashboard
                </a>
            </div>
        </div>
    </div>
    ''', 500

# ==================== EJECUCIÓN ====================

if __name__ == '__main__':
    # Configuración para producción/desarrollo
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Iniciando aplicación en modo {'debug' if debug_mode else 'producción'}")
    print(f"Servidor escuchando en puerto {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        threaded=True
    )
