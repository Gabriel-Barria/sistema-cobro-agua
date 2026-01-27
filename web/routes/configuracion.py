"""
Rutas para configuracion del sistema
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from web.auth import admin_required
from src.models_configuracion import (
    obtener_todas_configuraciones,
    guardar_configuracion
)
from src.models_boletas import obtener_configuracion, guardar_configuracion as guardar_tarifas

configuracion_bp = Blueprint('configuracion', __name__)


@configuracion_bp.route('/')
@admin_required
def index():
    """Dashboard de configuracion."""
    config = obtener_todas_configuraciones()
    tarifas = obtener_configuracion()

    return render_template('configuracion/index.html',
                           config=config,
                           tarifas=tarifas)


@configuracion_bp.route('/sistema', methods=['GET', 'POST'])
@admin_required
def sistema():
    """Configuracion global del sistema."""
    if request.method == 'POST':
        # Guardar configuraciones
        configs = {
            'frecuencia_facturacion': request.form.get('frecuencia_facturacion', 'mensual'),
            'dia_corte_periodo': int(request.form.get('dia_corte_periodo', 1)),
            'regla_periodo': request.form.get('regla_periodo', 'mes_anterior'),
            'dia_toma_lectura': int(request.form.get('dia_toma_lectura', 5)),
            'crear_lecturas_faltantes': request.form.get('crear_lecturas_faltantes') == 'on',
            'valor_lectura_faltante': request.form.get('valor_lectura_faltante', 'ultima')
        }

        for clave, valor in configs.items():
            guardar_configuracion(clave, valor)

        flash('Configuracion guardada exitosamente', 'success')
        return redirect(url_for('configuracion.sistema'))

    config = obtener_todas_configuraciones()
    return render_template('configuracion/sistema.html', config=config)


@configuracion_bp.route('/tarifas', methods=['GET', 'POST'])
@admin_required
def tarifas():
    """Configuracion de tarifas de boletas."""
    if request.method == 'POST':
        cargo_fijo = float(request.form.get('cargo_fijo', 0))
        precio_m3 = float(request.form.get('precio_m3', 0))

        guardar_tarifas(cargo_fijo, precio_m3)
        flash('Tarifas guardadas exitosamente', 'success')
        return redirect(url_for('configuracion.tarifas'))

    config = obtener_configuracion()
    return render_template('configuracion/tarifas.html', config=config)
