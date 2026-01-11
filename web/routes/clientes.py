"""
Rutas para gestión de clientes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import admin_required
from src.models import (
    listar_clientes, obtener_cliente, actualizar_cliente,
    crear_cliente, eliminar_cliente, buscar_cliente_por_nombre
)

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
@admin_required
def listar():
    """Lista todos los clientes."""
    clientes = listar_clientes()
    return render_template('clientes/lista.html', clientes=clientes)


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@admin_required
def crear():
    """Formulario para crear nuevo cliente."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip().lower()
        nombre_completo = request.form.get('nombre_completo', '').strip() or None
        rut = request.form.get('rut', '').strip() or None

        if not nombre:
            flash('El nombre es requerido', 'error')
            return redirect(url_for('clientes.crear'))

        # Verificar si ya existe
        if buscar_cliente_por_nombre(nombre):
            flash('Ya existe un cliente con ese nombre', 'error')
            return redirect(url_for('clientes.crear'))

        cliente_id = crear_cliente(nombre, nombre_completo, rut)
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('clientes.detalle', cliente_id=cliente_id))

    return render_template('clientes/crear.html')


@clientes_bp.route('/<int:cliente_id>')
@admin_required
def detalle(cliente_id):
    """Muestra detalle de un cliente."""
    cliente = obtener_cliente(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes.listar'))

    return render_template('clientes/detalle.html', cliente=cliente)


@clientes_bp.route('/<int:cliente_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(cliente_id):
    """Edita datos de un cliente."""
    cliente = obtener_cliente(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes.listar'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip().lower() or None
        nombre_completo = request.form.get('nombre_completo', '').strip() or None
        rut = request.form.get('rut', '').strip() or None

        # Verificar si el nuevo nombre ya existe (y no es el mismo cliente)
        if nombre and nombre != cliente['nombre']:
            existente = buscar_cliente_por_nombre(nombre)
            if existente and existente['id'] != cliente_id:
                flash('Ya existe otro cliente con ese nombre', 'error')
                return redirect(url_for('clientes.editar', cliente_id=cliente_id))

        actualizar_cliente(cliente_id, nombre=nombre, nombre_completo=nombre_completo, rut=rut)
        flash('Cliente actualizado', 'success')
        return redirect(url_for('clientes.detalle', cliente_id=cliente_id))

    return render_template('clientes/editar.html', cliente=cliente)


@clientes_bp.route('/<int:cliente_id>/eliminar', methods=['POST'])
@admin_required
def eliminar(cliente_id):
    """Elimina un cliente."""
    cliente = obtener_cliente(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes.listar'))

    if eliminar_cliente(cliente_id):
        flash('Cliente eliminado', 'success')
    else:
        flash('No se puede eliminar el cliente porque tiene medidores asociados', 'error')

    return redirect(url_for('clientes.listar'))
