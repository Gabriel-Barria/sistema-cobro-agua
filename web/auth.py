"""
Utilidades de autenticación y decoradores para protección de rutas
"""
from functools import wraps
from flask import session, redirect, url_for, flash


def get_current_user():
    """
    Obtiene el usuario actual de la sesión.

    Returns:
        dict con id, username, rol, nombre_completo o None si no hay sesión
    """
    if 'usuario_id' not in session:
        return None

    return {
        'id': session.get('usuario_id'),
        'username': session.get('username'),
        'rol': session.get('rol'),
        'nombre_completo': session.get('nombre_completo')
    }


def login_required(f):
    """
    Decorador para rutas que requieren login (cualquier rol).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorador para rutas que requieren rol de administrador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login'))

        if session.get('rol') != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'error')
            # Registradores van a mobile, otros al login
            if session.get('rol') == 'registrador':
                return redirect(url_for('mobile.registro_lecturas'))
            return redirect(url_for('auth.login'))

        return f(*args, **kwargs)
    return decorated_function


def registrador_required(f):
    """
    Decorador para rutas que requieren rol de registrador o administrador.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login'))

        if session.get('rol') not in ['administrador', 'registrador']:
            flash('No tienes permisos para acceder a esta página', 'error')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function
