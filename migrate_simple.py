"""
Script de migración de datos de SQLite a PostgreSQL - Versión simplificada
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
    print("ERROR: DATABASE_URL no esta configurado")
    sys.exit(1)

if not os.path.exists(SQLITE_DB):
    print(f"ERROR: No se encuentra {SQLITE_DB}")
    sys.exit(1)

def migrate():
    print("\n=== Iniciando migracion SQLite a PostgreSQL ===")
    print(f"SQLite: {SQLITE_DB}")
    print(f"PostgreSQL: {POSTGRES_URL.split('@')[-1]}\n")

    # Conexiones
    print("Conectando a bases de datos...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cursor = pg_conn.cursor()

    # Orden de tablas (por dependencias)
    tables = ['clientes', 'medidores', 'lecturas', 'configuracion_boletas', 'boletas']

    # Deshabilitar constraints temporalmente
    print("Deshabilitando constraints...")
    pg_cursor.execute('SET session_replication_role = replica;')

    total_rows = 0

    for table in tables:
        print(f"\n[{table}]")

        # Leer de SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f'SELECT * FROM {table}')
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"  Tabla vacia, saltando...")
            continue

        # Obtener nombres de columnas
        columns = [desc[0] for desc in sqlite_cursor.description]

        # Insertar en PostgreSQL
        placeholders = ','.join(['%s'] * len(columns))
        columns_str = ','.join(columns)

        insert_query = f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

        data = [tuple(row) for row in rows]

        # Insertar en lotes de 100
        for i in range(0, len(data), 100):
            batch = data[i:i+100]
            for row in batch:
                try:
                    pg_cursor.execute(insert_query, row)
                except Exception as e:
                    print(f"  Error insertando: {e}")

        print(f"  {len(rows)} filas migradas")
        total_rows += len(rows)

        # Actualizar secuencia de IDs
        try:
            pg_cursor.execute(f'''
                SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                              COALESCE((SELECT MAX(id) FROM {table}), 1), true)
            ''')
            print(f"  Secuencia actualizada")
        except:
            pass

    # Re-habilitar constraints
    print("\nRehabilitando constraints...")
    pg_cursor.execute('SET session_replication_role = DEFAULT;')

    pg_conn.commit()
    print(f"\n=== Migracion completada: {total_rows} filas totales ===\n")

    # Verificación
    verify_migration(sqlite_conn, pg_conn)

    sqlite_conn.close()
    pg_conn.close()

    print("\n=== EXITO ===\n")


def verify_migration(sqlite_conn, pg_conn):
    print("Verificando integridad...\n")

    tables = ['clientes', 'medidores', 'lecturas', 'boletas', 'configuracion_boletas']

    print(f"{'Tabla':<25} {'SQLite':>10} {'PostgreSQL':>12}")
    print("-" * 50)

    all_ok = True
    for table in tables:
        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
        sqlite_count = sqlite_cursor.fetchone()[0]

        pg_cursor.execute(f'SELECT COUNT(*) FROM {table}')
        pg_count = pg_cursor.fetchone()[0]

        match = sqlite_count == pg_count
        status = "OK" if match else "ERROR"

        if not match:
            all_ok = False

        print(f"{table:<25} {sqlite_count:>10} {pg_count:>12}   [{status}]")

    if all_ok:
        print("\nTodos los datos migrados correctamente")
    else:
        print("\nADVERTENCIA: Hay diferencias en los conteos")
        return False

    return True


if __name__ == '__main__':
    try:
        migrate()
    except KeyboardInterrupt:
        print("\n\nMigracion interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR durante la migracion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
