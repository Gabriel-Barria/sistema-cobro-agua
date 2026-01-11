"""
Script para crear usuario administrador inicial
Ejecutar UNA VEZ después de crear la tabla usuarios
"""
from src.database import get_connection, crear_tablas
from werkzeug.security import generate_password_hash

def crear_admin_inicial():
    """Crea usuario administrador por defecto si no existe."""

    # Primero crear/verificar la tabla usuarios
    print("Creando tabla de usuarios...")
    try:
        crear_tablas()
    except Exception as e:
        print(f"Error al crear tablas: {e}")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", ('admin',))
        if cursor.fetchone():
            print("Usuario 'admin' ya existe")
            conn.close()
            return

        # Crear admin
        password_hash = generate_password_hash('admin123')

        cursor.execute('''
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol)
            VALUES (%s, %s, %s, %s)
        ''', ('admin', password_hash, 'Administrador del Sistema', 'administrador'))

        conn.commit()
        print("\n✓ Usuario 'admin' creado exitosamente")
        print("  Username: admin")
        print("  Password: admin123")
        print("  IMPORTANTE: Cambiar la contraseña después del primer login\n")

    except Exception as e:
        print(f"✗ Error al crear usuario admin: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    crear_admin_inicial()
