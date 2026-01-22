"""
Rutas para gestión de clientes
"""
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response

from web.auth import admin_required
from src.models import (
    listar_clientes, obtener_cliente, actualizar_cliente,
    crear_cliente, eliminar_cliente, buscar_cliente_por_nombre
)

clientes_bp = Blueprint('clientes', __name__)


@clientes_bp.route('/')
@admin_required
def listar():
    """Lista todos los clientes con filtros."""
    busqueda = request.args.get('busqueda', '').strip() or None
    con_medidores = request.args.get('con_medidores', '').strip() or None
    sin_telefono = request.args.get('sin_telefono') == '1'

    clientes = listar_clientes(busqueda=busqueda, con_medidores=con_medidores,
                               sin_telefono=sin_telefono)

    return render_template('clientes/lista.html',
                           clientes=clientes,
                           busqueda=busqueda or '',
                           con_medidores=con_medidores or '',
                           sin_telefono=sin_telefono)


@clientes_bp.route('/nuevo', methods=['GET', 'POST'])
@admin_required
def crear():
    """Formulario para crear nuevo cliente."""
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip().lower()
        nombre_completo = request.form.get('nombre_completo', '').strip() or None
        rut = request.form.get('rut', '').strip() or None
        telefono = request.form.get('telefono', '').strip() or None
        email = request.form.get('email', '').strip() or None

        if not nombre:
            flash('El nombre es requerido', 'error')
            return redirect(url_for('clientes.crear'))

        # Verificar si ya existe
        if buscar_cliente_por_nombre(nombre):
            flash('Ya existe un cliente con ese nombre', 'error')
            return redirect(url_for('clientes.crear'))

        cliente_id = crear_cliente(nombre, nombre_completo, rut, telefono, email)
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
        telefono = request.form.get('telefono', '').strip() or None
        email = request.form.get('email', '').strip() or None
        volver_a_lista = request.form.get('volver_a_lista') == '1'

        # Verificar si el nuevo nombre ya existe (y no es el mismo cliente)
        if nombre and nombre != cliente['nombre']:
            existente = buscar_cliente_por_nombre(nombre)
            if existente and existente['id'] != cliente_id:
                flash('Ya existe otro cliente con ese nombre', 'error')
                if volver_a_lista:
                    return redirect(url_for('clientes.listar'))
                return redirect(url_for('clientes.editar', cliente_id=cliente_id))

        actualizar_cliente(cliente_id, nombre=nombre, nombre_completo=nombre_completo,
                          rut=rut, telefono=telefono, email=email)
        flash('Cliente actualizado', 'success')

        # Si viene del modal en la lista, volver a la lista con filtros
        if volver_a_lista:
            filtros = {
                'busqueda': request.form.get('busqueda', '').strip() or None,
                'con_medidores': request.form.get('con_medidores', '').strip() or None,
                'sin_telefono': request.form.get('sin_telefono') or None
            }
            # Limpiar valores None
            filtros = {k: v for k, v in filtros.items() if v}
            return redirect(url_for('clientes.listar', **filtros))

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

    exito, motivo = eliminar_cliente(cliente_id)

    if exito:
        flash('Cliente eliminado exitosamente', 'success')
    elif motivo == "medidores":
        flash('No se puede eliminar el cliente porque tiene medidores asociados', 'error')
    else:
        flash('Error al eliminar el cliente', 'error')

    return redirect(url_for('clientes.listar'))


@clientes_bp.route('/exportar')
@admin_required
def exportar():
    """Exporta clientes filtrados a Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from datetime import datetime

    # Obtener parametros de filtro
    busqueda = request.args.get('busqueda', '').strip() or None
    con_medidores = request.args.get('con_medidores', '').strip() or None
    sin_telefono = request.args.get('sin_telefono') == '1'

    # Obtener clientes con filtros
    clientes = listar_clientes(busqueda=busqueda, con_medidores=con_medidores,
                               sin_telefono=sin_telefono)

    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Título y fecha
    ws.merge_cells('A1:G1')
    ws['A1'] = 'LISTADO DE CLIENTES'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal="center")

    ws.merge_cells('A2:G2')
    ws['A2'] = f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
    ws['A2'].alignment = Alignment(horizontal="center")

    # Filtros aplicados
    row = 3
    if any([busqueda, con_medidores, sin_telefono]):
        ws.merge_cells(f'A{row}:G{row}')
        filtros_texto = []
        if busqueda:
            filtros_texto.append(f'Busqueda: {busqueda}')
        if con_medidores == 'si':
            filtros_texto.append('Con medidores')
        elif con_medidores == 'no':
            filtros_texto.append('Sin medidores')
        if sin_telefono:
            filtros_texto.append('Sin telefono')

        ws[f'A{row}'] = 'Filtros aplicados: ' + ' | '.join(filtros_texto)
        ws[f'A{row}'].font = Font(italic=True)
        ws[f'A{row}'].alignment = Alignment(horizontal="center")
        row += 1

    # Resumen
    row += 1
    ws.merge_cells(f'A{row}:G{row}')
    ws[f'A{row}'] = f'Total: {len(clientes)} cliente(s)'
    ws[f'A{row}'].font = Font(bold=True)
    ws[f'A{row}'].alignment = Alignment(horizontal="center")
    ws[f'A{row}'].fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")

    # Espacio
    row += 2

    # Encabezados de tabla
    headers = ['ID', 'Nombre', 'Nombre Completo', 'RUT', 'Telefono', 'Email', 'Medidores']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Datos
    row += 1
    for cliente in clientes:
        ws.cell(row=row, column=1, value=cliente.get('id', '')).border = border
        ws.cell(row=row, column=2, value=cliente.get('nombre', '')).border = border
        ws.cell(row=row, column=3, value=cliente.get('nombre_completo', '') or '-').border = border
        ws.cell(row=row, column=4, value=cliente.get('rut', '') or '-').border = border
        ws.cell(row=row, column=5, value=cliente.get('telefono', '') or '-').border = border
        ws.cell(row=row, column=6, value=cliente.get('email', '') or '-').border = border
        ws.cell(row=row, column=7, value=cliente.get('num_medidores', 0)).border = border
        row += 1

    # Ajustar anchos de columna
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 18
    ws.column_dimensions['F'].width = 30
    ws.column_dimensions['G'].width = 12

    # Preparar respuesta
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Nombre del archivo con timestamp
    filename = f'clientes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'

    return response
