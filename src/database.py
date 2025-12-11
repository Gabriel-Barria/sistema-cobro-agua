"""
Módulo de base de datos - Conexión y creación de tablas SQLite
"""
import sqlite3
import os

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'db', 'lecturas.db')


def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    conn.execute("PRAGMA foreign_keys = ON")  # Habilitar foreign keys
    return conn


def crear_tablas():
    """Crea las tablas necesarias si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            nombre_completo TEXT,
            rut TEXT,
            activo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla medidores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            numero_medidor TEXT,
            direccion TEXT,
            activo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    # Tabla lecturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lecturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medidor_id INTEGER NOT NULL,
            lectura_m3 INTEGER NOT NULL,
            fecha_lectura DATE NOT NULL,
            foto_path TEXT NOT NULL,
            foto_nombre TEXT NOT NULL,
            año INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medidor_id) REFERENCES medidores(id)
        )
    ''')

    # Índices para búsquedas eficientes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medidores_cliente ON medidores(cliente_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lecturas_medidor ON lecturas(medidor_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas(fecha_lectura)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_lecturas_año_mes ON lecturas(año, mes)')

    conn.commit()
    conn.close()
    print(f"Base de datos creada en: {DB_PATH}")


def inicializar_db():
    """Inicializa la base de datos creando el directorio y las tablas."""
    # Crear directorio db si no existe
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    crear_tablas()


if __name__ == '__main__':
    inicializar_db()
