import psycopg2
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def init_database():
    conn = get_connection()
    cur = conn.cursor()
    
    print("Inicializando base de datos...")
    
    # Eliminar tablas si existen
    cur.execute('''
        DROP TABLE IF EXISTS logs_auditoria CASCADE;
        DROP TABLE IF EXISTS equipaje CASCADE;
        DROP TABLE IF EXISTS reservas CASCADE;
        DROP TABLE IF EXISTS pasajeros CASCADE;
        DROP TABLE IF EXISTS vuelos CASCADE;
        DROP TABLE IF EXISTS aerolineas CASCADE;
        DROP TABLE IF EXISTS usuarios CASCADE;
    ''')
    
    # Crear tabla usuarios
    cur.execute('''
        CREATE TABLE usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            rol VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'responsable', 'consulta', 'empleado')),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT TRUE
        );
    ''')
    
    # Crear tabla aerolineas
    cur.execute('''
        CREATE TABLE aerolineas (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(3) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            pais_origen VARCHAR(50),
            fecha_fundacion DATE,
            activa BOOLEAN DEFAULT TRUE
        );
    ''')
    
    # Crear tabla vuelos
    cur.execute('''
        CREATE TABLE vuelos (
            id SERIAL PRIMARY KEY,
            numero_vuelo VARCHAR(10) UNIQUE NOT NULL,
            aerolinea_id INTEGER REFERENCES aerolineas(id),
            origen VARCHAR(100) NOT NULL,
            destino VARCHAR(100) NOT NULL,
            fecha_salida TIMESTAMP NOT NULL,
            fecha_llegada TIMESTAMP NOT NULL,
            estado VARCHAR(20) DEFAULT 'programado' CHECK (estado IN ('programado', 'en_vuelo', 'aterrizado', 'cancelado')),
            capacidad INTEGER NOT NULL,
            asientos_disponibles INTEGER NOT NULL
        );
    ''')
    
    # Crear tabla pasajeros
    cur.execute('''
        CREATE TABLE pasajeros (
            id SERIAL PRIMARY KEY,
            pasaporte VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            apellido VARCHAR(100) NOT NULL,
            nacionalidad VARCHAR(50),
            fecha_nacimiento DATE,
            telefono VARCHAR(20),
            email VARCHAR(100)
        );
    ''')
    
    # Crear tabla reservas
    cur.execute('''
        CREATE TABLE reservas (
            id SERIAL PRIMARY KEY,
            codigo_reserva VARCHAR(10) UNIQUE NOT NULL,
            vuelo_id INTEGER REFERENCES vuelos(id),
            pasajero_id INTEGER REFERENCES pasajeros(id),
            fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            estado VARCHAR(20) DEFAULT 'confirmada' CHECK (estado IN ('confirmada', 'cancelada', 'check-in')),
            asiento VARCHAR(5),
            clase VARCHAR(20) DEFAULT 'economica',
            precio DECIMAL(10,2)
        );
    ''')
    
    # Crear tabla equipaje
    cur.execute('''
        CREATE TABLE equipaje (
            id SERIAL PRIMARY KEY,
            reserva_id INTEGER REFERENCES reservas(id),
            numero_etiqueta VARCHAR(20) UNIQUE NOT NULL,
            peso DECIMAL(5,2),
            dimensiones VARCHAR(20),
            tipo VARCHAR(20) CHECK (tipo IN ('mano', 'bodega')),
            estado VARCHAR(20) DEFAULT 'registrado'
        );
    ''')
    
    # Crear tabla logs_auditoria
    cur.execute('''
        CREATE TABLE logs_auditoria (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER REFERENCES usuarios(id),
            accion VARCHAR(50) NOT NULL,
            tabla_afectada VARCHAR(50),
            registro_id INTEGER,
            detalles TEXT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address VARCHAR(45)
        );
    ''')
    
    # Crear usuarios iniciales
    usuarios_iniciales = [
        ('admin', 'admin123', 'Administrador Principal', 'admin@aerolinea.com', 'admin'),
        ('responsable', 'responsable123', 'Responsable Operaciones', 'responsable@aerolinea.com', 'responsable'),
        ('consulta', 'consulta123', 'Usuario Consulta', 'consulta@aerolinea.com', 'consulta'),
        ('empleado1', 'empleado123', 'Empleado Reservas', 'empleado@aerolinea.com', 'empleado'),
    ]
    
    for username, password, nombre, email, rol in usuarios_iniciales:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute('''
            INSERT INTO usuarios (username, password_hash, nombre, email, rol)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        ''', (username, password_hash, nombre, email, rol))
    
    # Crear aerolineas de ejemplo
    aerolineas = [
        ('AA', 'American Airlines', 'USA'),
        ('DL', 'Delta Air Lines', 'USA'),
        ('UA', 'United Airlines', 'USA'),
        ('AM', 'Aeromexico', 'Mexico'),
        ('IB', 'Iberia', 'Spain'),
        ('LH', 'Lufthansa', 'Germany'),
        ('AF', 'Air France', 'France'),
    ]
    
    for codigo, nombre, pais in aerolineas:
        cur.execute('''
            INSERT INTO aerolineas (codigo, nombre, pais_origen)
            VALUES (%s, %s, %s)
            ON CONFLICT (codigo) DO NOTHING
        ''', (codigo, nombre, pais))
    
    # Crear vuelos de ejemplo
    cur.execute("SELECT id FROM aerolineas WHERE codigo = 'AA'")
    aa_id = cur.fetchone()[0]
    
    cur.execute("SELECT id FROM aerolineas WHERE codigo = 'DL'")
    dl_id = cur.fetchone()[0]
    
    vuelos_ejemplo = [
        ('AA123', aa_id, 'Nueva York', 'Los Angeles', '2025-12-10 08:00:00', '2025-12-10 11:00:00', 180, 180),
        ('DL456', dl_id, 'Atlanta', 'Miami', '2025-12-10 10:30:00', '2025-12-10 12:00:00', 150, 150),
        ('AA789', aa_id, 'Chicago', 'Dallas', '2025-12-10 14:00:00', '2025-12-10 16:30:00', 200, 200),
    ]
    
    for num, a_id, orig, dest, salida, llegada, cap, disp in vuelos_ejemplo:
        cur.execute('''
            INSERT INTO vuelos (numero_vuelo, aerolinea_id, origen, destino, fecha_salida, fecha_llegada, capacidad, asientos_disponibles)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (numero_vuelo) DO NOTHING
        ''', (num, a_id, orig, dest, salida, llegada, cap, disp))
    
    # Crear pasajeros de ejemplo
    pasajeros_ejemplo = [
        ('P12345678', 'Juan', 'Perez', 'Mexico', '1985-05-15', '+525512345678', 'juan@email.com'),
        ('US87654321', 'Maria', 'Gomez', 'USA', '1990-08-22', '+13105551212', 'maria@email.com'),
        ('E11223344', 'Carlos', 'Lopez', 'Spain', '1978-11-30', '+34123456789', 'carlos@email.com'),
    ]
    
    for pasaporte, nombre, apellido, nacionalidad, fecha_nac, telefono, email in pasajeros_ejemplo:
        cur.execute('''
            INSERT INTO pasajeros (pasaporte, nombre, apellido, nacionalidad, fecha_nacimiento, telefono, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pasaporte) DO NOTHING
        ''', (pasaporte, nombre, apellido, nacionalidad, fecha_nac, telefono, email))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("Base de datos inicializada exitosamente!")
    print("Usuarios creados:")
    print("  - admin / admin123 (Administrador)")
    print("  - responsable / responsable123 (Responsable)")
    print("  - consulta / consulta123 (Solo lectura)")
    print("  - empleado1 / empleado123 (Empleado)")

if __name__ == '__main__':
    init_database()

