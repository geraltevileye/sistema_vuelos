import os
import psycopg2
from psycopg2 import sql
import bcrypt

# Conexión a tu BD de Render
connection_string = "postgresql://yova:j0smlHpbZTp1qgZsruJUHI9XW7Gv9gtt@dpg-d4u0hcfgi27c73a9b4rg-a.virginia-postgres.render.com/sistema_2tdl"

try:
    conn = psycopg2.connect(connection_string)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("✅ Conectado a PostgreSQL en Render")
    
    # Tabla usuarios
    cur.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        nombre VARCHAR(100) NOT NULL,
        email VARCHAR(100),
        rol VARCHAR(20) NOT NULL DEFAULT 'empleado',
        activo BOOLEAN DEFAULT TRUE,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabla aerolineas
    cur.execute('''
    CREATE TABLE IF NOT EXISTS aerolineas (
        id SERIAL PRIMARY KEY,
        codigo VARCHAR(3) UNIQUE NOT NULL,
        nombre VARCHAR(100) NOT NULL,
        pais_origen VARCHAR(100),
        fecha_fundacion DATE,
        activa BOOLEAN DEFAULT TRUE
    )
    ''')
    
    # Tabla vuelos
    cur.execute('''
    CREATE TABLE IF NOT EXISTS vuelos (
        id SERIAL PRIMARY KEY,
        numero_vuelo VARCHAR(10) NOT NULL,
        aerolinea_id INTEGER REFERENCES aerolineas(id),
        origen VARCHAR(100) NOT NULL,
        destino VARCHAR(100) NOT NULL,
        fecha_salida TIMESTAMP NOT NULL,
        fecha_llegada TIMESTAMP NOT NULL,
        capacidad INTEGER NOT NULL,
        asientos_disponibles INTEGER NOT NULL,
        estado VARCHAR(20) DEFAULT 'programado',
        CONSTRAINT chk_capacidad CHECK (asientos_disponibles <= capacidad)
    )
    ''')
    
    # Tabla pasajeros
    cur.execute('''
    CREATE TABLE IF NOT EXISTS pasajeros (
        id SERIAL PRIMARY KEY,
        pasaporte VARCHAR(50) UNIQUE NOT NULL,
        nombre VARCHAR(100) NOT NULL,
        apellido VARCHAR(100) NOT NULL,
        nacionalidad VARCHAR(100),
        fecha_nacimiento DATE,
        telefono VARCHAR(20),
        email VARCHAR(100)
    )
    ''')
    
    # Tabla reservas
    cur.execute('''
    CREATE TABLE IF NOT EXISTS reservas (
        id SERIAL PRIMARY KEY,
        codigo_reserva VARCHAR(20) UNIQUE NOT NULL,
        vuelo_id INTEGER REFERENCES vuelos(id),
        pasajero_id INTEGER REFERENCES pasajeros(id),
        asiento VARCHAR(10),
        clase VARCHAR(20) DEFAULT 'economica',
        precio DECIMAL(10,2),
        estado VARCHAR(20) DEFAULT 'confirmada',
        fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabla logs
    cur.execute('''
    CREATE TABLE IF NOT EXISTS logs_auditoria (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER REFERENCES usuarios(id),
        accion VARCHAR(50) NOT NULL,
        tabla_afectada VARCHAR(50),
        registro_id INTEGER,
        detalles JSONB,
        ip_address VARCHAR(45),
        fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insertar usuario admin por defecto
    admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cur.execute('''
    INSERT INTO usuarios (username, password_hash, nombre, rol) 
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (username) DO NOTHING
    ''', ('admin', admin_password, 'Administrador', 'admin'))
    
    # Insertar aerolíneas demo
    aerolineas_demo = [
        ('AA', 'American Airlines', 'USA'),
        ('LA', 'LATAM Airlines', 'Chile'),
        ('IB', 'Iberia', 'Spain'),
        ('AF', 'Air France', 'France'),
        ('LH', 'Lufthansa', 'Germany')
    ]
    
    for codigo, nombre, pais in aerolineas_demo:
        cur.execute('''
        INSERT INTO aerolineas (codigo, nombre, pais_origen, activa)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (codigo) DO NOTHING
        ''', (codigo, nombre, pais))
    
    print("✅ Tablas creadas exitosamente")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    crear_tablas()
