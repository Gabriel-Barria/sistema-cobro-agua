"""
Blueprint de autenticación - Login y Logout
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from src.models_usuarios import verificar_credenciales

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login para staff (admin y registradores)."""

    # Si ya está autenticado, redirigir según rol
    if 'usuario_id' in session:
        if session.get('rol') == 'registrador':
            return redirect(url_for('mobile.registro_lecturas'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Debes ingresar usuario y contraseña', 'error')
            return render_template('auth/login.html')

        # Verificar credenciales
        usuario = verificar_credenciales(username, password)

        if usuario:
            # Guardar en sesión
            session['usuario_id'] = usuario['id']
            session['username'] = usuario['username']
            session['nombre_completo'] = usuario['nombre_completo']
            session['rol'] = usuario['rol']

            flash(f'Bienvenido, {usuario["nombre_completo"]}', 'success')

            # Redirigir según rol
            if usuario['rol'] == 'registrador':
                return redirect(url_for('mobile.registro_lecturas'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Cierra sesión del usuario actual."""
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('auth.login'))
