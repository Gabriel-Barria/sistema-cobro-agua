"""
Módulo de base de datos - Conexión y creación de tablas PostgreSQL
"""
import os

# Detectar si usar SQLite (dev) o PostgreSQL (prod)
USE_POSTGRESQL = os.environ.get('DATABASE_URL') is not None

if USE_POSTGRESQL:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuración de base de datos
if USE_POSTGRESQL:
    DATABASE_URL = os.environ.get(
        'DATABASE_URL',
        'postgresql://lecturas_user:lecturas_pass@localhost:5432/lecturas'
    )
else:
    # SQLite para desarrollo
    DB_NAME = os.environ.get('DB_NAME', 'lecturas.db')
    DB_PATH = os.path.join(BASE_DIR, 'db', DB_NAME)


class SQLiteCursorWrapper:
    """Wrapper para cursor de SQLite que convierte placeholders %s a ? y RETURNING a lastrowid"""
    def __init__(self, cursor):
        self._cursor = cursor
        self._returning_id = False

    def execute(self, query, params=()):
        # Convertir %s a ? para SQLite
        converted_query = query.replace('%s', '?')

        # Detectar y remover RETURNING id (sintaxis PostgreSQL)
        if 'RETURNING id' in converted_query:
            self._returning_id = True
            converted_query = converted_query.replace('RETURNING id', '').strip()
        else:
            self._returning_id = False

        # Convertir funciones PostgreSQL a SQLite
        converted_query = converted_query.replace('SUBSTRING(', 'SUBSTR(')
        converted_query = converted_query.replace('STRING_AGG(', 'GROUP_CONCAT(')

        # Convertir CAST(x AS TEXT) a CAST(x AS TEXT) - SQLite lo soporta
        # No necesita cambios

        return self._cursor.execute(converted_query, params)

    def fetchone(self):
        # Si era un INSERT con RETURNING id, retornar lastrowid como tupla
        if self._returning_id:
            return (self._cursor.lastrowid,)
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class SQLiteConnectionWrapper:
    """Wrapper para conexión SQLite que retorna cursores compatibles con PostgreSQL"""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return SQLiteCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def execute(self, query, params=()):
        converted_query = query.replace('%s', '?')
        return self._conn.execute(converted_query, params)


class PostgreSQLCursorWrapper:
    """Wrapper para cursor de PostgreSQL que permite acceso por índice en RealDictCursor"""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=()):
        return self._cursor.execute(query, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        # Permitir acceso por índice en dict
        class DictWithIndex(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    return list(self.values())[key]
                return super().__getitem__(key)
        return DictWithIndex(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        # Convertir a lista de DictWithIndex
        class DictWithIndex(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    return list(self.values())[key]
                return super().__getitem__(key)
        return [DictWithIndex(row) for row in rows]

    @property
    def rowcount(self):
        return self._cursor.rowcount


class PostgreSQLConnectionWrapper:
    """Wrapper para conexión PostgreSQL"""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PostgreSQLCursorWrapper(self._conn.cursor())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()


def get_connection():
    """Obtiene una conexión a la base de datos (PostgreSQL o SQLite según entorno)."""
    if USE_POSTGRESQL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        # Retornar wrapper que permite acceso por índice
        return PostgreSQLConnectionWrapper(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Retornar wrapper que convierte %s a ? automáticamente
        return SQLiteConnectionWrapper(conn)


def crear_tablas():
    """Crea las tablas necesarias si no existen."""
    if USE_POSTGRESQL:
        # En PostgreSQL, las tablas se crean vía init_db.sql
        print("PostgreSQL: Las tablas se crean automáticamente vía init_db.sql")
        return

    # Solo para SQLite (desarrollo)
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
            fecha_inicio DATE DEFAULT NULL,
            fecha_baja DATE DEFAULT NULL,
            motivo_baja TEXT DEFAULT NULL,
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

    # Tabla configuracion_boletas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion_boletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cargo_fijo REAL NOT NULL DEFAULT 0,
            precio_m3 REAL NOT NULL DEFAULT 0,
            activo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla boletas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS boletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_boleta TEXT UNIQUE NOT NULL,
            lectura_id INTEGER NOT NULL,
            cliente_nombre TEXT NOT NULL,
            medidor_id INTEGER NOT NULL,
            periodo_año INTEGER NOT NULL,
            periodo_mes INTEGER NOT NULL,
            lectura_actual INTEGER NOT NULL,
            lectura_anterior INTEGER,
            consumo_m3 INTEGER NOT NULL,
            cargo_fijo REAL NOT NULL,
            precio_m3 REAL NOT NULL,
            subtotal_consumo REAL NOT NULL,
            total REAL NOT NULL,
            fecha_emision DATE NOT NULL,
            pagada INTEGER DEFAULT 0,
            fecha_pago DATE,
            metodo_pago TEXT,
            comprobante_path TEXT,
            estado_anterior INTEGER DEFAULT NULL,
            fecha_envio_revision DATE DEFAULT NULL,
            fecha_aprobacion DATE DEFAULT NULL,
            fecha_rechazo DATE DEFAULT NULL,
            motivo_rechazo TEXT DEFAULT NULL,
            comprobante_anterior TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
        )
    ''')

    # Índices para boletas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_boletas_lectura ON boletas(lectura_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_boletas_medidor ON boletas(medidor_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_boletas_pagada ON boletas(pagada)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_boletas_periodo ON boletas(periodo_año, periodo_mes)')

    conn.commit()
    conn.close()
    print(f"Base de datos creada en: {DB_PATH}")


def inicializar_db():
    """Inicializa la base de datos creando el directorio y las tablas."""
    if USE_POSTGRESQL:
        print("PostgreSQL: Base de datos inicializada vía Docker (init_db.sql)")
        return

    # Solo para SQLite (desarrollo)
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    crear_tablas()
    print(f"SQLite: Base de datos creada en: {DB_PATH}")


if __name__ == '__main__':
    inicializar_db()
