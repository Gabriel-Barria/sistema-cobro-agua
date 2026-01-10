"""
Script de migración de datos de SQLite a PostgreSQL
Transfiere todos los datos preservando IDs y relaciones
"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys

# Configuración
SQLITE_DB = os.path.join('db', 'lecturas.db')
POSTGRES_URL = os.environ.get('DATABASE_URL')

if not POSTGRES_URL:
    print("❌ Error: DATABASE_URL no está configurado")
    print("Ejemplo: export DATABASE_URL='postgresql://user:pass@localhost:5432/lecturas'")
    sys.exit(1)

if not os.path.exists(SQLITE_DB):
    print(f"❌ Error: No se encuentra la base de datos SQLite en {SQLITE_DB}")
    sys.exit(1)


def migrate():
    """Ejecuta la migración completa de SQLite a PostgreSQL."""
    print("🚀 Iniciando migración de SQLite a PostgreSQL")
    print(f"📁 SQLite: {SQLITE_DB}")
    print(f"🐘 PostgreSQL: {POSTGRES_URL.split('@')[-1]}")  # Mostrar solo host/db
    print()

    # Conexiones
    print("📡 Conectando a bases de datos...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor()

    # Orden de tablas (por dependencias)
    tables = [
        'clientes',
        'medidores',
        'lecturas',
        'configuracion_boletas',
        'boletas'
    ]

    # Deshabilitar constraints temporalmente
    print("⚙️  Deshabilitando constraints...")
    pg_cursor.execute('SET session_replication_role = replica;')

    total_rows = 0

    for table in tables:
        print(f"\n📦 Migrando tabla: {table}")

        # Leer de SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f'SELECT * FROM {table}')
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"  ⚠️  Tabla {table} vacía, saltando...")
            continue

        # Obtener nombres de columnas
        columns = [desc[0] for desc in sqlite_cursor.description]

        # Insertar en PostgreSQL
        placeholders = ','.join(['%s'] * len(columns))
        columns_str = ','.join(columns)

        insert_query = f'''
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        '''

        data = [tuple(row) for row in rows]

        # Insertar en lotes de 100 para mejor rendimiento
        for i in range(0, len(data), 100):
            batch = data[i:i+100]
            execute_values(pg_cursor, insert_query, batch, page_size=100)

        print(f"  ✅ {len(rows)} filas migradas")
        total_rows += len(rows)

        # Actualizar secuencia de IDs (solo para tablas con SERIAL)
        if table != 'configuracion_boletas':  # Todas las tablas tienen id SERIAL
            try:
                pg_cursor.execute(f'''
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1),
                        true
                    )
                ''')
                print(f"  🔢 Secuencia actualizada")
            except Exception as e:
                print(f"  ⚠️  No se pudo actualizar secuencia: {e}")

    # Re-habilitar constraints
    print("\n⚙️  Rehabilitando constraints...")
    pg_cursor.execute('SET session_replication_role = DEFAULT;')

    pg_conn.commit()
    print(f"\n✅ Migración completada: {total_rows} filas totales migradas")

    # Verificación
    verify_migration(sqlite_conn, pg_conn)

    # Cerrar conexiones
    sqlite_conn.close()
    pg_conn.close()

    print("\n🎉 ¡Migración finalizada exitosamente!")


def verify_migration(sqlite_conn, pg_conn):
    """Verifica la integridad de la migración comparando conteos."""
    print("\n🔍 Verificando integridad...")

    tables = ['clientes', 'medidores', 'lecturas', 'boletas', 'configuracion_boletas']

    all_ok = True
    for table in tables:
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
        sqlite_count = sqlite_cursor.fetchone()[0]

        pg_cursor.execute(f'SELECT COUNT(*) FROM {table}')
        pg_count = pg_cursor.fetchone()[0]

        match = sqlite_count == pg_count
        status = "✅" if match else "❌"

        if not match:
            all_ok = False

        print(f"  {status} {table:25} SQLite: {sqlite_count:5} | PostgreSQL: {pg_count:5}")

    if all_ok:
        print("\n✅ Verificación exitosa: Todos los datos migrados correctamente")
    else:
        print("\n⚠️  Advertencia: Hay diferencias en los conteos. Revisar migración.")
        return False

    return True


def show_stats(pg_conn):
    """Muestra estadísticas de la base de datos PostgreSQL."""
    print("\n📊 Estadísticas de PostgreSQL:")

    pg_cursor = pg_conn.cursor()

    stats_query = '''
        SELECT
            (SELECT COUNT(*) FROM clientes) as clientes,
            (SELECT COUNT(*) FROM medidores) as medidores,
            (SELECT COUNT(*) FROM lecturas) as lecturas,
            (SELECT COUNT(*) FROM boletas) as boletas,
            (SELECT COUNT(*) FROM configuracion_boletas) as configuraciones
    '''

    pg_cursor.execute(stats_query)
    stats = pg_cursor.fetchone()

    print(f"  - Clientes: {stats[0]}")
    print(f"  - Medidores: {stats[1]}")
    print(f"  - Lecturas: {stats[2]}")
    print(f"  - Boletas: {stats[3]}")
    print(f"  - Configuraciones: {stats[4]}")


if __name__ == '__main__':
    try:
        migrate()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migración interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
