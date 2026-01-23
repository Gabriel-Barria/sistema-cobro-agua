"""
Modelos para el sistema de pagos mejorado.
Incluye funciones para pagos, saldos y movimientos.
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

from src.database import get_connection


def generar_numero_pago() -> str:
    """Genera un número de pago único con formato PAG-YYYYMM-XXXX."""
    conn = get_connection()
    cursor = conn.cursor()

    ahora = datetime.now()
    prefijo = f"PAG-{ahora.year}{ahora.month:02d}-"

    cursor.execute('''
        SELECT numero_pago FROM pagos
        WHERE numero_pago LIKE %s
        ORDER BY numero_pago DESC
        LIMIT 1
    ''', (prefijo + '%',))

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        ultimo_numero = int(resultado['numero_pago'].split('-')[-1])
        nuevo_numero = ultimo_numero + 1
    else:
        nuevo_numero = 1

    return f"{prefijo}{nuevo_numero:04d}"


def obtener_saldo_cliente(cliente_id: int) -> Decimal:
    """Obtiene el saldo a favor actual del cliente."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT saldo_disponible FROM saldos_cliente
        WHERE cliente_id = %s
    ''', (cliente_id,))

    resultado = cursor.fetchone()
    conn.close()

    return Decimal(str(resultado['saldo_disponible'])) if resultado else Decimal('0')


def actualizar_saldo_cliente(cliente_id: int, nuevo_saldo: Decimal) -> bool:
    """Actualiza el saldo disponible del cliente."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO saldos_cliente (cliente_id, saldo_disponible, ultima_actualizacion)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (cliente_id)
            DO UPDATE SET saldo_disponible = %s, ultima_actualizacion = CURRENT_TIMESTAMP
        ''', (cliente_id, nuevo_saldo, nuevo_saldo))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def registrar_movimiento_saldo(cliente_id: int, tipo: str, origen: str,
                                monto: Decimal, descripcion: str = None,
                                pago_id: int = None, boleta_id: int = None,
                                usuario_id: int = None) -> int:
    """
    Registra un movimiento en el historial de saldos.

    Args:
        cliente_id: ID del cliente
        tipo: 'ingreso', 'egreso', 'ajuste'
        origen: 'excedente_pago', 'aplicacion_boleta', 'ajuste_admin', etc.
        monto: Monto del movimiento (positivo para ingreso, negativo para egreso)
        descripcion: Descripción opcional
        pago_id: ID del pago relacionado (opcional)
        boleta_id: ID de la boleta relacionada (opcional)
        usuario_id: ID del usuario que hace el ajuste (opcional)

    Returns:
        ID del movimiento creado
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        saldo_anterior = obtener_saldo_cliente(cliente_id)
        saldo_nuevo = saldo_anterior + monto

        cursor.execute('''
            INSERT INTO movimientos_saldo
            (cliente_id, tipo, origen, pago_id, boleta_id, monto,
             saldo_anterior, saldo_nuevo, descripcion, usuario_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (cliente_id, tipo, origen, pago_id, boleta_id, monto,
              saldo_anterior, saldo_nuevo, descripcion, usuario_id))

        movimiento_id = cursor.fetchone()['id']

        # Actualizar saldo del cliente
        actualizar_saldo_cliente(cliente_id, saldo_nuevo)

        conn.commit()
        return movimiento_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def registrar_pago(cliente_id: int, monto_total: Decimal,
                   boletas_ids: List[int], comprobante_path: str = None,
                   metodo_pago: str = 'transferencia',
                   usar_saldo: bool = False,
                   fecha_pago: date = None,
                   notas: str = None) -> Dict:
    """
    Registra un nuevo pago de cliente.

    Args:
        cliente_id: ID del cliente
        monto_total: Monto del depósito/transferencia
        boletas_ids: Lista de boletas a pagar (en orden de prioridad)
        comprobante_path: Ruta del comprobante (opcional para pagos directos)
        metodo_pago: Método de pago
        usar_saldo: Si usar saldo a favor disponible
        fecha_pago: Fecha del pago (default: hoy)
        notas: Notas adicionales

    Returns:
        dict con: pago_id, numero_pago, monto_aplicado, saldo_generado, boletas_afectadas
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        numero_pago = generar_numero_pago()

        # Obtener saldo disponible del cliente
        saldo_disponible = Decimal('0')
        if usar_saldo:
            saldo_disponible = obtener_saldo_cliente(cliente_id)

        # Monto total disponible para aplicar
        monto_disponible = Decimal(str(monto_total)) + saldo_disponible

        # Determinar estado inicial
        estado = 'en_revision' if comprobante_path else 'pendiente'

        # Crear registro de pago
        cursor.execute('''
            INSERT INTO pagos (numero_pago, cliente_id, monto_total,
                              comprobante_path, metodo_pago, estado,
                              fecha_pago, fecha_envio, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
            RETURNING id
        ''', (numero_pago, cliente_id, monto_total, comprobante_path,
              metodo_pago, estado, fecha_pago or date.today(), notas))

        pago_id = cursor.fetchone()['id']

        # Aplicar pago a boletas
        resultado = _aplicar_pago_a_boletas(
            cursor, pago_id, cliente_id,
            monto_disponible, boletas_ids, saldo_disponible
        )

        # Actualizar totales del pago
        cursor.execute('''
            UPDATE pagos
            SET monto_aplicado = %s, monto_a_favor = %s
            WHERE id = %s
        ''', (resultado['monto_aplicado'], resultado['saldo_generado'], pago_id))

        # Actualizar estado de boletas a "En Revisión"
        for boleta_id in resultado['boletas_afectadas']:
            cursor.execute('''
                UPDATE boletas SET pagada = 1, comprobante_path = %s
                WHERE id = %s AND pagada = 0
            ''', (comprobante_path, boleta_id,))

        conn.commit()

        return {
            'pago_id': pago_id,
            'numero_pago': numero_pago,
            'estado': estado,
            **resultado
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def _aplicar_pago_a_boletas(cursor, pago_id: int, cliente_id: int,
                            monto_disponible: Decimal, boletas_ids: List[int],
                            saldo_usado: Decimal = Decimal('0')) -> Dict:
    """
    Distribuye el monto disponible entre las boletas seleccionadas.
    Esta es una función interna que usa el cursor existente.

    Returns:
        dict con: monto_aplicado, saldo_generado, boletas_afectadas, detalles
    """
    monto_restante = monto_disponible
    monto_aplicado_total = Decimal('0')
    boletas_afectadas = []
    detalles = []

    # Ordenar boletas por periodo (más antigua primero)
    cursor.execute('''
        SELECT id, total, monto_pagado, saldo_pendiente
        FROM boletas
        WHERE id = ANY(%s) AND saldo_pendiente > 0
        ORDER BY periodo_año ASC, periodo_mes ASC
    ''', (boletas_ids,))
    boletas_ordenadas = cursor.fetchall()

    for boleta in boletas_ordenadas:
        if monto_restante <= 0:
            break

        boleta_id = boleta['id']
        saldo_boleta = Decimal(str(boleta['saldo_pendiente']))
        monto_aplicar = min(monto_restante, saldo_boleta)
        es_completo = (monto_aplicar >= saldo_boleta)

        # Registrar en pago_boletas
        cursor.execute('''
            INSERT INTO pago_boletas (pago_id, boleta_id, monto_aplicado, es_pago_completo)
            VALUES (%s, %s, %s, %s)
        ''', (pago_id, boleta_id, monto_aplicar, es_completo))

        monto_restante -= monto_aplicar
        monto_aplicado_total += monto_aplicar
        boletas_afectadas.append(boleta_id)
        detalles.append({
            'boleta_id': boleta_id,
            'monto_aplicado': float(monto_aplicar),
            'es_completo': es_completo
        })

    # Calcular saldo a favor (si sobró dinero)
    saldo_generado = max(Decimal('0'), monto_restante)

    return {
        'monto_aplicado': monto_aplicado_total,
        'saldo_generado': saldo_generado,
        'saldo_usado': saldo_usado,
        'boletas_afectadas': boletas_afectadas,
        'detalles': detalles
    }


def aprobar_pago(pago_id: int, usuario_id: int = None) -> Tuple[bool, str]:
    """
    Aprueba un pago y aplica efectivamente los montos a las boletas.

    Args:
        pago_id: ID del pago a aprobar
        usuario_id: ID del usuario que aprueba

    Returns:
        Tuple (éxito, mensaje)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Obtener pago
        cursor.execute('''
            SELECT * FROM pagos WHERE id = %s AND estado = 'en_revision'
        ''', (pago_id,))
        pago = cursor.fetchone()

        if not pago:
            return False, "Pago no encontrado o no está en revisión"

        # Obtener aplicaciones de boletas
        cursor.execute('''
            SELECT * FROM pago_boletas WHERE pago_id = %s
        ''', (pago_id,))
        aplicaciones = cursor.fetchall()

        # Actualizar cada boleta
        for app in aplicaciones:
            monto = Decimal(str(app['monto_aplicado']))

            cursor.execute('''
                UPDATE boletas
                SET monto_pagado = monto_pagado + %s,
                    saldo_pendiente = saldo_pendiente - %s,
                    pagada = CASE
                        WHEN saldo_pendiente - %s <= 0 THEN 2
                        ELSE 0
                    END,
                    fecha_pago = CASE
                        WHEN saldo_pendiente - %s <= 0 THEN CURRENT_DATE
                        ELSE fecha_pago
                    END,
                    metodo_pago = %s
                WHERE id = %s
            ''', (monto, monto, monto, monto, pago['metodo_pago'], app['boleta_id']))

        # Generar saldo a favor si hay excedente
        monto_a_favor = Decimal(str(pago['monto_a_favor']))
        if monto_a_favor > 0:
            registrar_movimiento_saldo(
                cliente_id=pago['cliente_id'],
                tipo='ingreso',
                origen='excedente_pago',
                monto=monto_a_favor,
                descripcion=f'Excedente del pago {pago["numero_pago"]}',
                pago_id=pago_id,
                usuario_id=usuario_id
            )

        # Actualizar estado del pago
        cursor.execute('''
            UPDATE pagos
            SET estado = 'aprobado',
                fecha_procesamiento = CURRENT_DATE,
                procesado_por = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (usuario_id, pago_id))

        conn.commit()
        return True, "Pago aprobado exitosamente"

    except Exception as e:
        conn.rollback()
        return False, f"Error al aprobar pago: {str(e)}"
    finally:
        conn.close()


def rechazar_pago(pago_id: int, motivo: str, usuario_id: int = None) -> Tuple[bool, str]:
    """
    Rechaza un pago y revierte las boletas a estado pendiente.

    Args:
        pago_id: ID del pago a rechazar
        motivo: Motivo del rechazo
        usuario_id: ID del usuario que rechaza

    Returns:
        Tuple (éxito, mensaje)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Obtener pago
        cursor.execute('''
            SELECT * FROM pagos WHERE id = %s AND estado = 'en_revision'
        ''', (pago_id,))
        pago = cursor.fetchone()

        if not pago:
            return False, "Pago no encontrado o no está en revisión"

        # Obtener boletas afectadas
        cursor.execute('''
            SELECT boleta_id FROM pago_boletas WHERE pago_id = %s
        ''', (pago_id,))
        boletas = cursor.fetchall()

        # Revertir boletas a estado pendiente (solo si no tienen otros pagos en revisión)
        for b in boletas:
            # Verificar si la boleta tiene otros pagos en revisión
            cursor.execute('''
                SELECT COUNT(*) as otros FROM pago_boletas pb
                JOIN pagos p ON pb.pago_id = p.id
                WHERE pb.boleta_id = %s AND p.estado = 'en_revision' AND p.id != %s
            ''', (b['boleta_id'], pago_id))
            otros = cursor.fetchone()['otros']

            if otros == 0:
                cursor.execute('''
                    UPDATE boletas SET pagada = 0, comprobante_path = NULL
                    WHERE id = %s AND pagada = 1
                ''', (b['boleta_id'],))

        # Actualizar estado del pago
        cursor.execute('''
            UPDATE pagos
            SET estado = 'rechazado',
                fecha_procesamiento = CURRENT_DATE,
                procesado_por = %s,
                motivo_rechazo = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (usuario_id, motivo, pago_id))

        conn.commit()
        return True, "Pago rechazado"

    except Exception as e:
        conn.rollback()
        return False, f"Error al rechazar pago: {str(e)}"
    finally:
        conn.close()


def registrar_pago_directo(cliente_id: int, monto_total: Decimal,
                           boletas_ids: List[int], metodo_pago: str,
                           usuario_id: int, fecha_pago: date = None,
                           notas: str = None,
                           comprobante_path: str = None) -> Dict:
    """
    Registra un pago directo desde el admin (ej: pago en efectivo).
    El pago se aprueba automáticamente.

    Args:
        cliente_id: ID del cliente
        monto_total: Monto del pago
        boletas_ids: Lista de boletas a pagar
        metodo_pago: Método de pago (efectivo, transferencia, etc.)
        usuario_id: ID del admin que registra
        fecha_pago: Fecha del pago
        notas: Notas adicionales

    Returns:
        dict con información del pago
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        numero_pago = generar_numero_pago()
        monto_total = Decimal(str(monto_total))

        # Crear registro de pago con estado aprobado
        cursor.execute('''
            INSERT INTO pagos (numero_pago, cliente_id, monto_total,
                              metodo_pago, estado, fecha_pago, fecha_envio,
                              fecha_procesamiento, procesado_por, notas,
                              comprobante_path)
            VALUES (%s, %s, %s, %s, 'aprobado', %s, CURRENT_DATE,
                    CURRENT_DATE, %s, %s, %s)
            RETURNING id
        ''', (numero_pago, cliente_id, monto_total, metodo_pago,
              fecha_pago or date.today(), usuario_id, notas, comprobante_path))

        pago_id = cursor.fetchone()['id']

        # Aplicar pago a boletas (ordenadas por periodo, más antigua primero)
        monto_restante = monto_total
        monto_aplicado_total = Decimal('0')
        boletas_afectadas = []

        cursor.execute('''
            SELECT id, total, saldo_pendiente
            FROM boletas
            WHERE id = ANY(%s) AND saldo_pendiente > 0
            ORDER BY periodo_año ASC, periodo_mes ASC
        ''', (boletas_ids,))
        boletas_ordenadas = cursor.fetchall()

        for boleta in boletas_ordenadas:
            if monto_restante <= 0:
                break

            boleta_id = boleta['id']
            saldo_boleta = Decimal(str(boleta['saldo_pendiente']))
            monto_aplicar = min(monto_restante, saldo_boleta)
            es_completo = (monto_aplicar >= saldo_boleta)

            # Registrar relación
            cursor.execute('''
                INSERT INTO pago_boletas (pago_id, boleta_id, monto_aplicado, es_pago_completo)
                VALUES (%s, %s, %s, %s)
            ''', (pago_id, boleta_id, monto_aplicar, es_completo))

            # Actualizar boleta
            nuevo_estado = 2 if es_completo else 0
            cursor.execute('''
                UPDATE boletas
                SET monto_pagado = monto_pagado + %s,
                    saldo_pendiente = saldo_pendiente - %s,
                    pagada = %s,
                    fecha_pago = CASE WHEN %s = 2 THEN %s ELSE fecha_pago END,
                    metodo_pago = %s,
                    comprobante_path = COALESCE(%s, comprobante_path)
                WHERE id = %s
            ''', (monto_aplicar, monto_aplicar, nuevo_estado,
                  nuevo_estado, fecha_pago or date.today(), metodo_pago,
                  comprobante_path, boleta_id))

            monto_restante -= monto_aplicar
            monto_aplicado_total += monto_aplicar
            boletas_afectadas.append(boleta_id)

        # Calcular saldo a favor
        saldo_generado = max(Decimal('0'), monto_restante)

        # Actualizar totales del pago
        cursor.execute('''
            UPDATE pagos SET monto_aplicado = %s, monto_a_favor = %s WHERE id = %s
        ''', (monto_aplicado_total, saldo_generado, pago_id))

        # Si hay excedente, agregarlo al saldo del cliente
        if saldo_generado > 0:
            registrar_movimiento_saldo(
                cliente_id=cliente_id,
                tipo='ingreso',
                origen='excedente_pago',
                monto=saldo_generado,
                descripcion=f'Excedente del pago {numero_pago}',
                pago_id=pago_id,
                usuario_id=usuario_id
            )

        conn.commit()

        return {
            'pago_id': pago_id,
            'numero_pago': numero_pago,
            'estado': 'aprobado',
            'monto_aplicado': float(monto_aplicado_total),
            'saldo_generado': float(saldo_generado),
            'boletas_afectadas': boletas_afectadas
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def listar_pagos(cliente_id: int = None, estado: str = None,
                 fecha_desde: date = None, fecha_hasta: date = None,
                 limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Lista pagos con filtros opcionales.

    Args:
        cliente_id: Filtrar por cliente
        estado: Filtrar por estado (pendiente, en_revision, aprobado, rechazado)
        fecha_desde: Fecha inicio
        fecha_hasta: Fecha fin
        limit: Límite de resultados
        offset: Offset para paginación

    Returns:
        Lista de pagos con información del cliente
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT p.*,
               c.nombre as cliente_nombre,
               u.nombre_completo as procesado_por_nombre,
               (SELECT COUNT(*) FROM pago_boletas WHERE pago_id = p.id) as num_boletas
        FROM pagos p
        JOIN clientes c ON p.cliente_id = c.id
        LEFT JOIN usuarios u ON p.procesado_por = u.id
        WHERE 1=1
    '''
    params = []

    if cliente_id:
        query += ' AND p.cliente_id = %s'
        params.append(cliente_id)

    if estado:
        query += ' AND p.estado = %s'
        params.append(estado)

    if fecha_desde:
        query += ' AND p.fecha_envio >= %s'
        params.append(fecha_desde)

    if fecha_hasta:
        query += ' AND p.fecha_envio <= %s'
        params.append(fecha_hasta)

    query += ' ORDER BY p.created_at DESC LIMIT %s OFFSET %s'
    params.extend([limit, offset])

    cursor.execute(query, params)
    pagos = cursor.fetchall()
    conn.close()

    return [dict(p) for p in pagos]


def obtener_pago(pago_id: int) -> Optional[Dict]:
    """Obtiene un pago por ID con sus boletas asociadas."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.*,
               c.nombre as cliente_nombre,
               u.nombre_completo as procesado_por_nombre
        FROM pagos p
        JOIN clientes c ON p.cliente_id = c.id
        LEFT JOIN usuarios u ON p.procesado_por = u.id
        WHERE p.id = %s
    ''', (pago_id,))

    pago = cursor.fetchone()

    if not pago:
        conn.close()
        return None

    # Obtener boletas del pago
    cursor.execute('''
        SELECT pb.*, b.numero_boleta, b.total as boleta_total,
               b.saldo_pendiente, b.pagada
        FROM pago_boletas pb
        JOIN boletas b ON pb.boleta_id = b.id
        WHERE pb.pago_id = %s
    ''', (pago_id,))

    boletas = cursor.fetchall()
    conn.close()

    resultado = dict(pago)
    resultado['boletas'] = [dict(b) for b in boletas]

    return resultado


def obtener_resumen_cuenta_cliente(cliente_id: int) -> Dict:
    """
    Obtiene resumen completo de la cuenta del cliente.

    Returns:
        dict con: saldo_favor, total_deuda, boletas_pendientes,
                  pagos_en_revision, movimientos_recientes
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Saldo a favor
    saldo_favor = obtener_saldo_cliente(cliente_id)

    # Total deuda y boletas pendientes
    cursor.execute('''
        SELECT COALESCE(SUM(b.saldo_pendiente), 0) as total_deuda,
               COUNT(*) as boletas_pendientes
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        WHERE m.cliente_id = %s AND b.saldo_pendiente > 0
    ''', (cliente_id,))
    deuda = cursor.fetchone()

    # Pagos en revisión
    cursor.execute('''
        SELECT COUNT(*) as cantidad
        FROM pagos
        WHERE cliente_id = %s AND estado = 'en_revision'
    ''', (cliente_id,))
    pagos_pendientes = cursor.fetchone()

    # Movimientos recientes
    cursor.execute('''
        SELECT * FROM movimientos_saldo
        WHERE cliente_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    ''', (cliente_id,))
    movimientos = cursor.fetchall()

    conn.close()

    return {
        'saldo_favor': float(saldo_favor),
        'total_deuda': float(deuda['total_deuda']),
        'boletas_pendientes': deuda['boletas_pendientes'],
        'pagos_en_revision': pagos_pendientes['cantidad'],
        'movimientos_recientes': [dict(m) for m in movimientos]
    }


def listar_saldos_clientes() -> List[Dict]:
    """Lista todos los clientes con su saldo a favor."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.id, c.nombre, c.nombre_completo,
               COALESCE(s.saldo_disponible, 0) as saldo_disponible,
               s.ultima_actualizacion
        FROM clientes c
        LEFT JOIN saldos_cliente s ON c.id = s.cliente_id
        ORDER BY s.saldo_disponible DESC NULLS LAST, c.nombre
    ''')

    clientes = cursor.fetchall()
    conn.close()

    return [dict(c) for c in clientes]


def ajustar_saldo_cliente(cliente_id: int, monto: Decimal,
                          descripcion: str, usuario_id: int) -> Tuple[bool, str]:
    """
    Realiza un ajuste manual al saldo del cliente.

    Args:
        cliente_id: ID del cliente
        monto: Monto del ajuste (positivo o negativo)
        descripcion: Descripción del ajuste
        usuario_id: ID del admin que realiza el ajuste

    Returns:
        Tuple (éxito, mensaje)
    """
    try:
        saldo_actual = obtener_saldo_cliente(cliente_id)
        nuevo_saldo = saldo_actual + Decimal(str(monto))

        if nuevo_saldo < 0:
            return False, "El ajuste resultaría en un saldo negativo"

        registrar_movimiento_saldo(
            cliente_id=cliente_id,
            tipo='ajuste',
            origen='ajuste_admin',
            monto=Decimal(str(monto)),
            descripcion=descripcion,
            usuario_id=usuario_id
        )

        return True, f"Saldo ajustado. Nuevo saldo: ${nuevo_saldo:,.0f}"

    except Exception as e:
        return False, f"Error al ajustar saldo: {str(e)}"


def obtener_historial_movimientos(cliente_id: int, limit: int = 50) -> List[Dict]:
    """Obtiene el historial de movimientos de saldo de un cliente."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT ms.*,
               p.numero_pago,
               b.numero_boleta
        FROM movimientos_saldo ms
        LEFT JOIN pagos p ON ms.pago_id = p.id
        LEFT JOIN boletas b ON ms.boleta_id = b.id
        WHERE ms.cliente_id = %s
        ORDER BY ms.created_at DESC
        LIMIT %s
    ''', (cliente_id, limit))

    movimientos = cursor.fetchall()
    conn.close()

    return [dict(m) for m in movimientos]


def usar_saldo_en_boletas(cliente_id: int, boletas_ids: List[int],
                          usuario_id: int = None) -> Dict:
    """
    Usa el saldo a favor del cliente para pagar boletas.
    No requiere comprobante ya que usa saldo existente.

    Args:
        cliente_id: ID del cliente
        boletas_ids: IDs de boletas a pagar
        usuario_id: ID del usuario (opcional)

    Returns:
        dict con información del resultado
    """
    saldo_disponible = obtener_saldo_cliente(cliente_id)

    if saldo_disponible <= 0:
        raise ValueError("No hay saldo disponible")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        numero_pago = generar_numero_pago()
        monto_usado = Decimal('0')
        boletas_afectadas = []

        # Crear pago con estado aprobado (uso de saldo)
        cursor.execute('''
            INSERT INTO pagos (numero_pago, cliente_id, monto_total,
                              metodo_pago, estado, fecha_pago, fecha_envio,
                              fecha_procesamiento, notas)
            VALUES (%s, %s, 0, 'saldo_favor', 'aprobado', CURRENT_DATE,
                    CURRENT_DATE, CURRENT_DATE, 'Pago con saldo a favor')
            RETURNING id
        ''', (numero_pago, cliente_id))

        pago_id = cursor.fetchone()['id']

        # Aplicar saldo a boletas (ordenadas por periodo, más antigua primero)
        saldo_restante = saldo_disponible

        cursor.execute('''
            SELECT id, saldo_pendiente
            FROM boletas
            WHERE id = ANY(%s) AND saldo_pendiente > 0
            ORDER BY periodo_año ASC, periodo_mes ASC
        ''', (boletas_ids,))
        boletas_ordenadas = cursor.fetchall()

        for boleta in boletas_ordenadas:
            if saldo_restante <= 0:
                break

            boleta_id = boleta['id']
            saldo_boleta = Decimal(str(boleta['saldo_pendiente']))
            monto_aplicar = min(saldo_restante, saldo_boleta)
            es_completo = (monto_aplicar >= saldo_boleta)

            # Registrar relación
            cursor.execute('''
                INSERT INTO pago_boletas (pago_id, boleta_id, monto_aplicado, es_pago_completo)
                VALUES (%s, %s, %s, %s)
            ''', (pago_id, boleta_id, monto_aplicar, es_completo))

            # Actualizar boleta
            nuevo_estado = 2 if es_completo else 0
            cursor.execute('''
                UPDATE boletas
                SET monto_pagado = monto_pagado + %s,
                    saldo_pendiente = saldo_pendiente - %s,
                    pagada = %s,
                    fecha_pago = CASE WHEN %s = 2 THEN CURRENT_DATE ELSE fecha_pago END,
                    metodo_pago = 'saldo_favor'
                WHERE id = %s
            ''', (monto_aplicar, monto_aplicar, nuevo_estado, nuevo_estado, boleta_id))

            # Registrar movimiento de egreso
            registrar_movimiento_saldo(
                cliente_id=cliente_id,
                tipo='egreso',
                origen='aplicacion_boleta',
                monto=-monto_aplicar,
                descripcion=f'Aplicado a boleta {boleta_id}',
                pago_id=pago_id,
                boleta_id=boleta_id,
                usuario_id=usuario_id
            )

            saldo_restante -= monto_aplicar
            monto_usado += monto_aplicar
            boletas_afectadas.append(boleta_id)

        # Actualizar pago con monto aplicado
        cursor.execute('''
            UPDATE pagos SET monto_aplicado = %s WHERE id = %s
        ''', (monto_usado, pago_id))

        conn.commit()

        return {
            'pago_id': pago_id,
            'numero_pago': numero_pago,
            'monto_usado': float(monto_usado),
            'saldo_restante': float(saldo_restante),
            'boletas_afectadas': boletas_afectadas
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
