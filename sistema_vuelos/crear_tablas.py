import psycopg2
import os
import bcrypt
from datetime import datetime

def crear_tablas():
    try:
        # Conexión a la base de datos de Render
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            port=os.environ.get('DB_PORT', 5432),
            sslmode='require'
        )
        
        conn.autocommit = True
        cur = conn.cursor()
        
        print("🔄 Creando tablas en la base de datos de Render...")
        
        # 1. Tabla usuarios
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
        print("✅ Tabla 'usuarios' creada")
        
        # 2. Tabla aerolineas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS aerolineas (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(3) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                pais_origen VARCHAR(50),
                fecha_fundacion DATE,
                activa BOOLEAN DEFAULT TRUE
            )
        ''')
        print("✅ Tabla 'aerolineas' creada")
        
        # 3. Tabla vuelos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS vuelos (
                id SERIAL PRIMARY KEY,
                numero_vuelo VARCHAR(10) NOT NULL,
                aerolinea_id INTEGER REFERENCES aerolineas(id),
                origen VARCHAR(50) NOT NULL,
                destino VARCHAR(50) NOT NULL,
                fecha_salida TIMESTAMP NOT NULL,
                fecha_llegada TIMESTAMP NOT NULL,
                capacidad INTEGER NOT NULL,
                asientos_disponibles INTEGER NOT NULL,
                estado VARCHAR(20) DEFAULT 'programado',
                CONSTRAINT chk_capacidad CHECK (asientos_disponibles <= capacidad),
                CONSTRAINT chk_fechas CHECK (fecha_salida < fecha_llegada)
            )
        ''')
        print("✅ Tabla 'vuelos' creada")
        
        # 4. Tabla pasajeros
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pasajeros (
                id SERIAL PRIMARY KEY,
                pasaporte VARCHAR(20) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100) NOT NULL,
                nacionalidad VARCHAR(50),
                fecha_nacimiento DATE,
                telefono VARCHAR(20),
                email VARCHAR(100)
            )
        ''')
        print("✅ Tabla 'pasajeros' creada")
        
        # 5. Tabla reservas
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
                fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(vuelo_id, pasajero_id)
            )
        ''')
        print("✅ Tabla 'reservas' creada")
        
        # 6. Tabla logs
        cur.execute('''
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                accion VARCHAR(50) NOT NULL,
                tabla_afectada VARCHAR(50),
                registro_id INTEGER,
                detalles TEXT,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45)
            )
        ''')
        print("✅ Tabla 'logs_auditoria' creada")
        
        # Crear índices
        cur.execute('CREATE INDEX IF NOT EXISTS idx_vuelos_fecha ON vuelos(fecha_salida)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_reservas_vuelo ON reservas(vuelo_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_reservas_pasajero ON reservas(pasajero_id)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_auditoria(fecha_hora)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_auditoria(usuario_id)')
        print("✅ Índices creados")
        
        # Insertar aerolíneas de ejemplo
        aerolineas = [
            ('AA', 'American Airlines', 'Estados Unidos', '1930-04-15'),
            ('DL', 'Delta Air Lines', 'Estados Unidos', '1924-05-30'),
            ('UA', 'United Airlines', 'Estados Unidos', '1926-04-06'),
            ('LA', 'LATAM Airlines', 'Chile', '1929-03-05'),
            ('IB', 'Iberia', 'España', '1927-06-28')
        ]
        
        for codigo, nombre, pais, fecha in aerolineas:
            cur.execute('''
                INSERT INTO aerolineas (codigo, nombre, pais_origen, fecha_fundacion)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
            ''', (codigo, nombre, pais, fecha))
        print("✅ Aerolíneas insertadas")
        
        # Insertar usuarios por defecto
        usuarios = [
            ('admin', 'admin123', 'Administrador Principal', 'admin'),
            ('responsable', 'responsable123', 'Responsable de Operaciones', 'responsable'),
            ('empleado', 'empleado123', 'Empleado General', 'empleado'),
            ('consulta', 'consulta123', 'Usuario de Consulta', 'consulta')
        ]
        
        for username, password, nombre, rol in usuarios:
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE username = %s", (username,))
            if cur.fetchone()[0] == 0:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                cur.execute('''
                    INSERT INTO usuarios (username, password_hash, nombre, rol)
                    VALUES (%s, %s, %s, %s)
                ''', (username, password_hash, nombre, rol))
        print("✅ Usuarios insertados")
        
        # Insertar vuelos de ejemplo
        vuelos = [
            ('AA245', 1, 'MIA', 'JFK', '2025-01-15 08:00:00', '2025-01-15 11:00:00', 150, 140),
            ('DL789', 2, 'ATL', 'LAX', '2025-01-15 10:30:00', '2025-01-15 13:45:00', 180, 160),
            ('UA456', 3, 'ORD', 'DFW', '2025-01-15 14:15:00', '2025-01-15 16:30:00', 200, 195),
            ('LA123', 4, 'SCL', 'MIA', '2025-01-16 09:00:00', '2025-01-16 16:00:00', 220, 210),
            ('IB890', 5, 'MAD', 'JFK', '2025-01-16 11:30:00', '2025-01-16 14:45:00', 180, 175)
        ]
        
        for num_vuelo, aerolinea_id, origen, destino, salida, llegada, capacidad, disponibles in vuelos:
            cur.execute('''
                INSERT INTO vuelos (numero_vuelo, aerolinea_id, origen, destino, 
                                  fecha_salida, fecha_llegada, capacidad, asientos_disponibles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            ''', (num_vuelo, aerolinea_id, origen, destino, salida, llegada, capacidad, disponibles))
        print("✅ Vuelos insertados")
        
        cur.close()
        conn.close()
        
        print("\n🎉 ¡Base de datos inicializada exitosamente en Render!")
        print("\n🔑 Credenciales para iniciar sesión:")
        print("   👤 admin / admin123")
        print("   👤 responsable / responsable123")
        print("   👤 empleado / empleado123")
        print("   👤 consulta / consulta123")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    crear_tablas()
