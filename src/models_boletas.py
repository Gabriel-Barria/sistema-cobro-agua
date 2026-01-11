"""
Modelos para el sistema de boletas - CRUD desacoplado
"""
from datetime import date
from typing import List, Dict, Optional
from .database import get_connection


# =============================================================================
# CONFIGURACION DE BOLETAS
# =============================================================================

def obtener_configuracion():
    """Obtiene la configuracion activa de boletas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, cargo_fijo, precio_m3, activo, created_at, updated_at
        FROM configuracion_boletas
        WHERE activo = 1
        ORDER BY id DESC
        LIMIT 1
    ''')
    config = cursor.fetchone()
    conn.close()
    return dict(config) if config else None


def guardar_configuracion(cargo_fijo: float, precio_m3: float):
    """Guarda o actualiza la configuracion de boletas."""
    conn = get_connection()
    cursor = conn.cursor()

    # Desactivar configuraciones anteriores
    cursor.execute('UPDATE configuracion_boletas SET activo = 0')

    # Crear nueva configuracion
    cursor.execute('''
        INSERT INTO configuracion_boletas (cargo_fijo, precio_m3, activo)
        VALUES (%s, %s, 1)
        RETURNING id
    ''', (cargo_fijo, precio_m3))

    config_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return config_id


# =============================================================================
# BOLETAS - CRUD
# =============================================================================

def generar_numero_boleta(año: int, mes: int) -> str:
    """Genera un numero de boleta unico formato BOL-YYYYMM-XXXX."""
    conn = get_connection()
    cursor = conn.cursor()

    # Buscar el número máximo existente para ese periodo
    cursor.execute('''
        SELECT numero_boleta FROM boletas
        WHERE periodo_año = %s AND periodo_mes = %s
        ORDER BY numero_boleta DESC
        LIMIT 1
    ''', (año, mes))

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        # Extraer el número secuencial del formato BOL-YYYYMM-XXXX
        ultimo_numero = resultado['numero_boleta']
        numero_secuencial = int(ultimo_numero.split('-')[-1])
        numero = numero_secuencial + 1
    else:
        # Primera boleta del periodo
        numero = 1

    return f"BOL-{año}{mes:02d}-{numero:04d}"


def crear_boleta(lectura_id: int, cliente_nombre: str, medidor_id: int,
                 periodo_año: int, periodo_mes: int, lectura_actual: int,
                 lectura_anterior: int, consumo_m3: int, cargo_fijo: float,
                 precio_m3: float) -> int:
    """Crea una nueva boleta."""
    conn = get_connection()
    cursor = conn.cursor()

    numero_boleta = generar_numero_boleta(periodo_año, periodo_mes)
    subtotal_consumo = consumo_m3 * precio_m3
    total = cargo_fijo + subtotal_consumo
    fecha_emision = date.today().isoformat()

    cursor.execute('''
        INSERT INTO boletas (
            numero_boleta, lectura_id, cliente_nombre, medidor_id,
            periodo_año, periodo_mes, lectura_actual, lectura_anterior,
            consumo_m3, cargo_fijo, precio_m3, subtotal_consumo, total,
            fecha_emision, pagada
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        RETURNING id
    ''', (numero_boleta, lectura_id, cliente_nombre, medidor_id,
          periodo_año, periodo_mes, lectura_actual, lectura_anterior,
          consumo_m3, cargo_fijo, precio_m3, subtotal_consumo, total,
          fecha_emision))

    boleta_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return boleta_id


def obtener_boleta(boleta_id: int):
    """Obtiene una boleta por su ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, l.foto_path
        FROM boletas b
        LEFT JOIN lecturas l ON b.lectura_id = l.id
        WHERE b.id = %s
    ''', (boleta_id,))
    boleta = cursor.fetchone()
    conn.close()
    return dict(boleta) if boleta else None


def obtener_boleta_por_lectura(lectura_id: int):
    """Verifica si ya existe una boleta para una lectura."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM boletas WHERE lectura_id = %s', (lectura_id,))
    boleta = cursor.fetchone()
    conn.close()
    return dict(boleta) if boleta else None


def listar_boletas(cliente_id: int = None, medidor_id: int = None,
                   pagada: int = None, sin_comprobante: bool = False,
                   año: int = None, mes: int = None):
    """Lista boletas con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT b.*, m.numero_medidor, c.nombre as cliente_nombre_actual, c.id as cliente_id
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if medidor_id is not None:
        query += ' AND b.medidor_id = %s'
        params.append(medidor_id)

    if pagada is not None:
        query += ' AND b.pagada = %s'
        params.append(pagada)

    if sin_comprobante:
        query += ' AND b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = \'\')'

    if año is not None:
        query += ' AND b.periodo_año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND b.periodo_mes = %s'
        params.append(mes)

    query += ' ORDER BY b.periodo_año DESC, b.periodo_mes DESC, b.id DESC'

    cursor.execute(query, params)
    boletas = cursor.fetchall()
    conn.close()
    return [dict(b) for b in boletas]


def marcar_boleta_pagada(boleta_id: int, metodo_pago: str) -> bool:
    """Marca una boleta como pagada."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET pagada = 1, fecha_pago = %s, metodo_pago = %s
        WHERE id = %s
    ''', (date.today().isoformat(), metodo_pago, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def desmarcar_boleta_pagada(boleta_id: int) -> bool:
    """Desmarca una boleta como pagada."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET pagada = 0, fecha_pago = NULL, metodo_pago = NULL
        WHERE id = %s
    ''', (boleta_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def guardar_comprobante(boleta_id: int, comprobante_path: str) -> bool:
    """Guarda la ruta del comprobante de pago."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET comprobante_path = %s
        WHERE id = %s
    ''', (comprobante_path, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_boleta(boleta_id: int) -> bool:
    """Elimina una boleta."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM boletas WHERE id = %s', (boleta_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# =============================================================================
# FUNCIONES AUXILIARES PARA CALCULO
# =============================================================================

def obtener_lectura_anterior(medidor_id: int, año: int, mes: int):
    """Obtiene la lectura del periodo anterior."""
    conn = get_connection()
    cursor = conn.cursor()

    # Calcular periodo anterior
    if mes == 1:
        mes_anterior = 12
        año_anterior = año - 1
    else:
        mes_anterior = mes - 1
        año_anterior = año

    cursor.execute('''
        SELECT lectura_m3 FROM lecturas
        WHERE medidor_id = %s AND año = %s AND mes = %s
    ''', (medidor_id, año_anterior, mes_anterior))

    lectura = cursor.fetchone()
    conn.close()
    return lectura['lectura_m3'] if lectura else None


def calcular_consumo(lectura_actual: int, lectura_anterior: int) -> int:
    """Calcula el consumo como diferencia entre lecturas."""
    if lectura_anterior is None:
        return lectura_actual
    consumo = lectura_actual - lectura_anterior
    return max(0, consumo)  # No permitir consumo negativo


def obtener_lecturas_sin_boleta(año: int = None, mes: int = None,
                                 cliente_id: int = None):
    """Obtiene lecturas que aun no tienen boleta asociada."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT l.*, m.numero_medidor, c.nombre as cliente_nombre, c.id as cliente_id
        FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        LEFT JOIN boletas b ON l.id = b.lectura_id
        WHERE b.id IS NULL AND m.activo = 1
    '''
    params = []

    if año is not None:
        query += ' AND l.año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND l.mes = %s'
        params.append(mes)

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    query += ' ORDER BY l.año DESC, l.mes DESC, c.nombre'

    cursor.execute(query, params)
    lecturas = cursor.fetchall()
    conn.close()
    return [dict(l) for l in lecturas]


def obtener_años_disponibles():
    """Obtiene los años con lecturas disponibles."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT año FROM lecturas ORDER BY año DESC')
    años = [row['año'] for row in cursor.fetchall()]
    conn.close()
    return años


def obtener_estadisticas_boletas(cliente_id: int = None, medidor_id: int = None,
                                  pagada: int = None, sin_comprobante: bool = False,
                                  año: int = None, mes: int = None):
    """Obtiene estadisticas de boletas con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN b.pagada = 2 THEN 1 ELSE 0 END) as pagadas,
            SUM(CASE WHEN b.pagada = 1 THEN 1 ELSE 0 END) as en_revision,
            SUM(CASE WHEN b.pagada = 0 THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = '') THEN 1 ELSE 0 END) as sin_comprobante,
            SUM(b.total) as monto_total,
            SUM(CASE WHEN b.pagada = 2 THEN b.total ELSE 0 END) as monto_pagado,
            SUM(CASE WHEN b.pagada = 1 THEN b.total ELSE 0 END) as monto_en_revision,
            SUM(CASE WHEN b.pagada = 0 THEN b.total ELSE 0 END) as monto_pendiente
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if medidor_id is not None:
        query += ' AND b.medidor_id = %s'
        params.append(medidor_id)

    if pagada is not None:
        query += ' AND b.pagada = %s'
        params.append(pagada)

    if sin_comprobante:
        query += ' AND b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = \'\')'

    if año is not None:
        query += ' AND b.periodo_año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND b.periodo_mes = %s'
        params.append(mes)

    cursor.execute(query, params)
    stats = cursor.fetchone()
    conn.close()
    return dict(stats) if stats else None


def obtener_boletas_pendientes_por_cliente(cliente_id: int, estado: int = 0) -> List[Dict]:
    """
    Obtiene boletas de un cliente por estado.

    Args:
        cliente_id: ID del cliente
        estado: 0 = Pendiente, 1 = En Revisión, 2 = Pagada

    Returns:
        Lista de boletas con info del medidor
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT b.*, m.numero_medidor, m.direccion
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        WHERE m.cliente_id = %s AND b.pagada = %s
        ORDER BY b.periodo_año DESC, b.periodo_mes DESC
    ''', (cliente_id, estado))

    boletas = cursor.fetchall()
    conn.close()
    return [dict(b) for b in boletas]


def marcar_boletas_en_revision(boleta_ids: List[int], comprobante_path: str) -> bool:
    """
    Marca múltiples boletas como "En Revisión" y asigna el mismo comprobante.

    Transición: Pendiente (0) → En Revisión (1)

    Args:
        boleta_ids: Lista de IDs de boletas
        comprobante_path: Ruta relativa del comprobante compartido

    Returns:
        True si todas las actualizaciones fueron exitosas
    """
    if not boleta_ids:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    fecha_envio = date.today().isoformat()

    try:
        updated_count = 0
        for boleta_id in boleta_ids:
            # Actualizar estado de la boleta
            cursor.execute('''
                UPDATE boletas
                SET pagada = 1,
                    comprobante_path = %s
                WHERE id = %s AND pagada = 0
            ''', (comprobante_path, boleta_id))
            updated_count += cursor.rowcount

            # Registrar en historial (misma transacción)
            cursor.execute('''
                INSERT INTO historial_pagos (boleta_id, comprobante_path, fecha_envio, estado)
                VALUES (%s, %s, %s, 'en_revision')
            ''', (boleta_id, comprobante_path, fecha_envio))

        conn.commit()
        conn.close()

        return updated_count > 0

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error en marcar_boletas_en_revision: {e}")
        return False


def aprobar_boletas(boleta_ids: List[int], metodo_pago: str = 'transferencia') -> bool:
    """
    Aprueba múltiples boletas: En Revisión (1) → Pagada (2)

    Args:
        boleta_ids: Lista de IDs de boletas
        metodo_pago: Método de pago (default: transferencia)

    Returns:
        True si todas las aprobaciones fueron exitosas
    """
    if not boleta_ids:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    fecha_pago = date.today().isoformat()

    try:
        updated_count = 0
        for boleta_id in boleta_ids:
            # Actualizar historial (misma transacción)
            cursor.execute('''
                UPDATE historial_pagos
                SET estado = 'aprobado',
                    fecha_procesamiento = %s,
                    metodo_pago = %s
                WHERE boleta_id = %s AND estado = 'en_revision'
            ''', (fecha_pago, metodo_pago, boleta_id))

            # Actualizar estado de la boleta
            cursor.execute('''
                UPDATE boletas
                SET pagada = 2,
                    fecha_pago = %s,
                    metodo_pago = %s
                WHERE id = %s AND pagada = 1
            ''', (fecha_pago, metodo_pago, boleta_id))
            updated_count += cursor.rowcount

        conn.commit()
        conn.close()

        return updated_count > 0

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error en aprobar_boletas: {e}")
        return False


def rechazar_boletas(boleta_ids: List[int], motivo: str) -> bool:
    """
    Rechaza múltiples boletas: En Revisión (1) → Pendiente (0)

    Args:
        boleta_ids: Lista de IDs de boletas
        motivo: Motivo del rechazo (visible para el cliente)

    Returns:
        True si todos los rechazos fueron exitosos
    """
    if not boleta_ids:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    fecha_procesamiento = date.today().isoformat()

    try:
        updated_count = 0
        for boleta_id in boleta_ids:
            # Actualizar historial (misma transacción)
            cursor.execute('''
                UPDATE historial_pagos
                SET estado = 'rechazado',
                    fecha_procesamiento = %s,
                    motivo_rechazo = %s
                WHERE boleta_id = %s AND estado = 'en_revision'
            ''', (fecha_procesamiento, motivo, boleta_id))

            # Cambiar estado de la boleta
            cursor.execute('''
                UPDATE boletas
                SET comprobante_path = NULL,
                    pagada = 0
                WHERE id = %s AND pagada = 1
            ''', (boleta_id,))
            updated_count += cursor.rowcount

        conn.commit()
        conn.close()

        return updated_count > 0

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error en rechazar_boletas: {e}")
        return False


# =============================================================================
# HISTORIAL DE INTENTOS DE PAGO
# =============================================================================

def crear_intento_pago(boleta_id: int, comprobante_path: str) -> int:
    """
    Registra un nuevo intento de pago en el historial.

    Args:
        boleta_id: ID de la boleta
        comprobante_path: Ruta del comprobante

    Returns:
        ID del registro creado
    """
    conn = get_connection()
    cursor = conn.cursor()

    fecha_envio = date.today().isoformat()

    cursor.execute('''
        INSERT INTO historial_pagos (boleta_id, comprobante_path, fecha_envio, estado)
        VALUES (%s, %s, %s, 'en_revision')
        RETURNING id
    ''', (boleta_id, comprobante_path, fecha_envio))

    intento_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return intento_id


def actualizar_intento_aprobado(boleta_id: int, metodo_pago: str) -> bool:
    """
    Marca el intento en revisión como aprobado.

    Args:
        boleta_id: ID de la boleta
        metodo_pago: Método de pago utilizado

    Returns:
        True si se actualizó correctamente
    """
    conn = get_connection()
    cursor = conn.cursor()

    fecha_procesamiento = date.today().isoformat()

    cursor.execute('''
        UPDATE historial_pagos
        SET estado = 'aprobado',
            fecha_procesamiento = %s,
            metodo_pago = %s
        WHERE boleta_id = %s AND estado = 'en_revision'
    ''', (fecha_procesamiento, metodo_pago, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def actualizar_intento_rechazado(boleta_id: int, motivo: str) -> bool:
    """
    Marca el intento en revisión como rechazado.

    Args:
        boleta_id: ID de la boleta
        motivo: Motivo del rechazo

    Returns:
        True si se actualizó correctamente
    """
    conn = get_connection()
    cursor = conn.cursor()

    fecha_procesamiento = date.today().isoformat()

    cursor.execute('''
        UPDATE historial_pagos
        SET estado = 'rechazado',
            fecha_procesamiento = %s,
            motivo_rechazo = %s
        WHERE boleta_id = %s AND estado = 'en_revision'
    ''', (fecha_procesamiento, motivo, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def obtener_historial_pagos(boleta_id: int) -> List[Dict]:
    """
    Obtiene todos los intentos de pago de una boleta.

    Args:
        boleta_id: ID de la boleta

    Returns:
        Lista de intentos ordenados cronológicamente
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, boleta_id, comprobante_path, fecha_envio, estado,
               fecha_procesamiento, motivo_rechazo, metodo_pago, created_at
        FROM historial_pagos
        WHERE boleta_id = %s
        ORDER BY id ASC
    ''', (boleta_id,))

    historial = cursor.fetchall()
    conn.close()
    return [dict(h) for h in historial]


def obtener_ultimo_rechazo(boleta_id: int) -> Optional[Dict]:
    """
    Obtiene el último rechazo de una boleta.

    Args:
        boleta_id: ID de la boleta

    Returns:
        Diccionario con info del rechazo o None si no hay rechazos
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, boleta_id, comprobante_path, fecha_envio, estado,
               fecha_procesamiento, motivo_rechazo, created_at
        FROM historial_pagos
        WHERE boleta_id = %s AND estado = 'rechazado'
        ORDER BY id DESC
        LIMIT 1
    ''', (boleta_id,))

    rechazo = cursor.fetchone()
    conn.close()
    return dict(rechazo) if rechazo else None


def obtener_intento_en_revision(boleta_id: int) -> Optional[Dict]:
    """
    Obtiene el intento actualmente en revisión de una boleta.

    Args:
        boleta_id: ID de la boleta

    Returns:
        Diccionario con info del intento o None si no hay ninguno en revisión
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, boleta_id, comprobante_path, fecha_envio, estado, created_at
        FROM historial_pagos
        WHERE boleta_id = %s AND estado = 'en_revision'
        ORDER BY id DESC
        LIMIT 1
    ''', (boleta_id,))

    intento = cursor.fetchone()
    conn.close()
    return dict(intento) if intento else None


def listar_historial_pagos(estado: str = None) -> List[Dict]:
    """
    Lista todos los intentos de pago con información de la boleta.

    Args:
        estado: Filtrar por estado ('en_revision', 'aprobado', 'rechazado') o None para todos

    Returns:
        Lista de intentos con datos de boleta y cliente
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT h.id, h.boleta_id, h.comprobante_path, h.fecha_envio, h.estado,
               h.fecha_procesamiento, h.motivo_rechazo, h.metodo_pago, h.created_at,
               b.numero_boleta, b.cliente_nombre, b.total, b.periodo_mes, b.periodo_año
        FROM historial_pagos h
        JOIN boletas b ON h.boleta_id = b.id
    '''

    if estado:
        query += ' WHERE h.estado = %s'
        query += ' ORDER BY h.id DESC'
        cursor.execute(query, (estado,))
    else:
        query += ' ORDER BY h.id DESC'
        cursor.execute(query)

    historial = cursor.fetchall()
    conn.close()
    return [dict(h) for h in historial]
