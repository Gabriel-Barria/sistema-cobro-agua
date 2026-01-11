"""
Módulo de base de datos - Conexión PostgreSQL
IMPORTANTE: Este módulo SOLO funciona con PostgreSQL (para producción/servidor)
Para desarrollo local con SQLite, usar una versión diferente del archivo
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuración de base de datos PostgreSQL
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/sistema-cobro-agua'
)


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
    """Obtiene una conexión a la base de datos PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    # Retornar wrapper que permite acceso por índice
    return PostgreSQLConnectionWrapper(conn)


def crear_tablas():
    """Crea las tablas necesarias en PostgreSQL (especialmente tabla usuarios)"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Tabla de usuarios del sistema (staff)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nombre_completo VARCHAR(100) NOT NULL,
                rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrador', 'registrador')),
                activo SMALLINT DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Índice para búsqueda rápida por username
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usuarios_username
            ON usuarios(username)
        ''')

        conn.commit()
        print("✓ PostgreSQL: Tabla 'usuarios' creada/verificada exitosamente")

    except Exception as e:
        print(f"✗ Error al crear tablas: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_db():
    """Inicializa la base de datos."""
    print("✓ PostgreSQL: Base de datos inicializada vía Docker (init_db.sql)")

    # Verificar conexión
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✓ Conectado a PostgreSQL: {version[0][:50]}...")
        conn.close()
    except Exception as e:
        print(f"✗ Error al conectar a PostgreSQL: {e}")
        raise


if __name__ == '__main__':
    inicializar_db()
