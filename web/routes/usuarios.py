"""
Blueprint de gestión de usuarios (solo administradores)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from web.auth import admin_required
from src.models_usuarios import (
    crear_usuario, obtener_usuarios, obtener_usuario,
    actualizar_usuario, cambiar_password, eliminar_usuario
)

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


@usuarios_bp.route('/')
@admin_required
def lista():
    """Lista todos los usuarios del sistema."""
    usuarios = obtener_usuarios()
    return render_template('usuarios/lista.html', usuarios=usuarios)


@usuarios_bp.route('/crear', methods=['GET', 'POST'])
@admin_required
def crear():
    """Crea un nuevo usuario."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre_completo = request.form.get('nombre_completo')
        rol = request.form.get('rol')

        if not all([username, password, nombre_completo, rol]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('usuarios/crear.html')

        if rol not in ['administrador', 'registrador']:
            flash('Rol inválido', 'error')
            return render_template('usuarios/crear.html')

        try:
            crear_usuario(username, password, nombre_completo, rol)
            flash(f'Usuario "{username}" creado exitosamente', 'success')
            return redirect(url_for('usuarios.lista'))
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'error')

    return render_template('usuarios/crear.html')


@usuarios_bp.route('/<int:usuario_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(usuario_id):
    """Edita un usuario existente."""
    usuario = obtener_usuario(usuario_id)

    if not usuario:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('usuarios.lista'))

    if request.method == 'POST':
        username = request.form.get('username')
        nombre_completo = request.form.get('nombre_completo')
        rol = request.form.get('rol')
        activo = int(request.form.get('activo', 1))

        try:
            actualizar_usuario(usuario_id, username, nombre_completo, rol, activo)
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('usuarios.lista'))
        except Exception as e:
            flash(f'Error al actualizar usuario: {str(e)}', 'error')

    return render_template('usuarios/editar.html', usuario=usuario)


@usuarios_bp.route('/<int:usuario_id>/cambiar-password', methods=['GET', 'POST'])
@admin_required
def cambiar_pass(usuario_id):
    """Cambia la contraseña de un usuario."""
    usuario = obtener_usuario(usuario_id)

    if not usuario:
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('usuarios.lista'))

    if request.method == 'POST':
        nueva_password = request.form.get('password')
        confirmacion = request.form.get('password_confirmacion')

        if nueva_password != confirmacion:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('usuarios/cambiar_password.html', usuario=usuario)

        try:
            cambiar_password(usuario_id, nueva_password)
            flash('Contraseña cambiada exitosamente', 'success')
            return redirect(url_for('usuarios.lista'))
        except Exception as e:
            flash(f'Error al cambiar contraseña: {str(e)}', 'error')

    return render_template('usuarios/cambiar_password.html', usuario=usuario)


@usuarios_bp.route('/<int:usuario_id>/eliminar', methods=['POST'])
@admin_required
def eliminar(usuario_id):
    """Desactiva un usuario."""
    try:
        eliminar_usuario(usuario_id)
        flash('Usuario desactivado exitosamente', 'success')
    except Exception as e:
        flash(f'Error al desactivar usuario: {str(e)}', 'error')

    return redirect(url_for('usuarios.lista'))
