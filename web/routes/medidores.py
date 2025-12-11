"""
Rutas para gestión de medidores
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from src.models import listar_medidores, obtener_medidor, listar_lecturas

medidores_bp = Blueprint('medidores', __name__)


@medidores_bp.route('/')
def listar():
    """Lista todos los medidores."""
    medidores = listar_medidores()
    return render_template('medidores/lista.html', medidores=medidores)


@medidores_bp.route('/<int:medidor_id>')
def detalle(medidor_id):
    """Muestra detalle de un medidor con historial de lecturas."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    # Obtener historial de lecturas
    lecturas = listar_lecturas(medidor_id=medidor_id, limit=100)

    return render_template('medidores/detalle.html', medidor=medidor, lecturas=lecturas)
