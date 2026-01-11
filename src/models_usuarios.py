"""
Modelos y funciones CRUD para gestión de usuarios del sistema
"""
from src.database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


def crear_usuario(username, password, nombre_completo, rol):
    """
    Crea un nuevo usuario del sistema.

    Args:
        username: Nombre de usuario único
        password: Contraseña en texto plano (se hasheará)
        nombre_completo: Nombre completo del usuario
        rol: 'administrador' o 'registrador'

    Returns:
        int: ID del usuario creado
    """
    conn = get_connection()
    cursor = conn.cursor()

    password_hash = generate_password_hash(password)

    cursor.execute('''
        INSERT INTO usuarios (username, password_hash, nombre_completo, rol)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    ''', (username, password_hash, nombre_completo, rol))

    usuario_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return usuario_id


def verificar_credenciales(username, password):
    """
    Verifica credenciales de login.

    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano

    Returns:
        dict: Datos del usuario si credenciales son válidas, None si inválidas
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, password_hash, nombre_completo, rol, activo
        FROM usuarios
        WHERE username = %s AND activo = 1
    ''', (username,))

    usuario = cursor.fetchone()
    conn.close()

    if usuario and check_password_hash(usuario['password_hash'], password):
        return {
            'id': usuario['id'],
            'username': usuario['username'],
            'nombre_completo': usuario['nombre_completo'],
            'rol': usuario['rol']
        }

    return None


def obtener_usuario(usuario_id):
    """Obtiene datos de un usuario por ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, nombre_completo, rol, activo, created_at
        FROM usuarios
        WHERE id = %s
    ''', (usuario_id,))

    usuario = cursor.fetchone()
    conn.close()

    return usuario


def obtener_usuarios():
    """Obtiene lista de todos los usuarios."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, nombre_completo, rol, activo, created_at
        FROM usuarios
        ORDER BY created_at DESC
    ''')

    usuarios = cursor.fetchall()
    conn.close()

    return usuarios


def actualizar_usuario(usuario_id, username, nombre_completo, rol, activo):
    """Actualiza datos de un usuario (sin cambiar contraseña)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE usuarios
        SET username = %s,
            nombre_completo = %s,
            rol = %s,
            activo = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', (username, nombre_completo, rol, activo, usuario_id))

    conn.commit()
    conn.close()


def cambiar_password(usuario_id, nueva_password):
    """Cambia la contraseña de un usuario."""
    conn = get_connection()
    cursor = conn.cursor()

    password_hash = generate_password_hash(nueva_password)

    cursor.execute('''
        UPDATE usuarios
        SET password_hash = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', (password_hash, usuario_id))

    conn.commit()
    conn.close()


def eliminar_usuario(usuario_id):
    """Desactiva un usuario (soft delete)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE usuarios
        SET activo = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    ''', (usuario_id,))

    conn.commit()
    conn.close()
