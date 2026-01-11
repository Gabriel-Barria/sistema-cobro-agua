"""
Utilidades de autenticación y decoradores para protección de rutas
"""
from functools import wraps
from flask import session, redirect, url_for, flash


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
            return redirect(url_for('index'))

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
