"""
Rutas para gestión de clientes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.models import listar_clientes, obtener_cliente, actualizar_cliente

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
def listar():
    """Lista todos los clientes."""
    clientes = listar_clientes()
    return render_template('clientes/lista.html', clientes=clientes)


@clientes_bp.route('/<int:cliente_id>')
def detalle(cliente_id):
    """Muestra detalle de un cliente."""
    cliente = obtener_cliente(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes.listar'))

    return render_template('clientes/detalle.html', cliente=cliente)


@clientes_bp.route('/<int:cliente_id>/editar', methods=['GET', 'POST'])
def editar(cliente_id):
    """Edita datos de un cliente."""
    cliente = obtener_cliente(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('clientes.listar'))

    if request.method == 'POST':
        nombre_completo = request.form.get('nombre_completo', '').strip() or None
        rut = request.form.get('rut', '').strip() or None

        actualizar_cliente(cliente_id, nombre_completo=nombre_completo, rut=rut)
        flash('Cliente actualizado', 'success')
        return redirect(url_for('clientes.detalle', cliente_id=cliente_id))

    return render_template('clientes/editar.html', cliente=cliente)
