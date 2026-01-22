"""
Módulo de modelos - Funciones CRUD para clientes, medidores y lecturas
"""
from datetime import date
from typing import Optional, List, Dict
from .database import get_connection


# ============== CLIENTES ==============

def crear_cliente(nombre: str, nombre_completo: str = None, rut: str = None,
                  telefono: str = None, email: str = None) -> int:
    """
    Crea un nuevo cliente.

    Args:
        nombre: Nombre normalizado del cliente
        nombre_completo: Nombre legal completo (opcional)
        rut: RUT del cliente (opcional)
        telefono: Teléfono del cliente (opcional)
        email: Correo electrónico del cliente (opcional)

    Returns:
        ID del cliente creado
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clientes (nombre, nombre_completo, rut, telefono, email)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (nombre, nombre_completo, rut, telefono, email))
    cliente_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return cliente_id


def buscar_cliente_por_nombre(nombre: str) -> Optional[Dict]:
    """
    Busca un cliente por su nombre normalizado.

    Args:
        nombre: Nombre a buscar

    Returns:
        Dict con datos del cliente o None si no existe
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE nombre = %s', (nombre,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def obtener_o_crear_cliente(nombre: str) -> int:
    """
    Obtiene el ID de un cliente existente o lo crea si no existe.

    Args:
        nombre: Nombre normalizado del cliente

    Returns:
        ID del cliente
    """
    cliente = buscar_cliente_por_nombre(nombre)
    if cliente:
        return cliente['id']
    return crear_cliente(nombre)


def listar_clientes(busqueda: str = None, con_medidores: str = None,
                    filtro_telefono: str = None) -> List[Dict]:
    """
    Lista clientes con filtros opcionales.

    Args:
        busqueda: Texto para buscar en nombre, nombre_completo, RUT, telefono o email
        con_medidores: 'si' para clientes con medidores, 'no' para sin medidores, None para todos
        filtro_telefono: 'con' para clientes con telefono, 'sin' para sin telefono, None para todos

    Returns:
        Lista de clientes con conteo de medidores
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT c.*,
               COUNT(m.id) as num_medidores
        FROM clientes c
        LEFT JOIN medidores m ON c.id = m.cliente_id
        WHERE 1=1
    '''
    params = []

    if busqueda:
        query += ''' AND (
            LOWER(c.nombre) LIKE LOWER(%s) OR
            LOWER(c.nombre_completo) LIKE LOWER(%s) OR
            LOWER(c.rut) LIKE LOWER(%s) OR
            LOWER(c.telefono) LIKE LOWER(%s) OR
            LOWER(c.email) LIKE LOWER(%s)
        )'''
        busqueda_param = f'%{busqueda}%'
        params.extend([busqueda_param, busqueda_param, busqueda_param, busqueda_param, busqueda_param])

    if filtro_telefono == 'sin':
        query += ' AND (c.telefono IS NULL OR c.telefono = %s)'
        params.append('')
    elif filtro_telefono == 'con':
        query += ' AND c.telefono IS NOT NULL AND c.telefono != %s'
        params.append('')

    query += ' GROUP BY c.id'

    if con_medidores == 'si':
        query += ' HAVING COUNT(m.id) > 0'
    elif con_medidores == 'no':
        query += ' HAVING COUNT(m.id) = 0'

    query += ' ORDER BY c.nombre'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_cliente(cliente_id: int) -> Optional[Dict]:
    """Obtiene un cliente por ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE id = %s', (cliente_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_cliente(cliente_id: int, nombre: str = None, nombre_completo: str = None,
                       rut: str = None, telefono: str = None, email: str = None) -> bool:
    """Actualiza datos de un cliente."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if nombre is not None:
        updates.append('nombre = %s')
        params.append(nombre)
    if nombre_completo is not None:
        updates.append('nombre_completo = %s')
        params.append(nombre_completo if nombre_completo else None)
    if rut is not None:
        updates.append('rut = %s')
        params.append(rut if rut else None)
    if telefono is not None:
        updates.append('telefono = %s')
        params.append(telefono if telefono else None)
    if email is not None:
        updates.append('email = %s')
        params.append(email if email else None)

    if not updates:
        conn.close()
        return False

    params.append(cliente_id)
    query = f'UPDATE clientes SET {", ".join(updates)} WHERE id = %s'

    cursor.execute(query, params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============== MEDIDORES ==============

def crear_medidor(cliente_id: int, numero_medidor: str = None, direccion: str = None, fecha_inicio: str = None) -> int:
    """
    Crea un nuevo medidor asociado a un cliente.

    Args:
        cliente_id: ID del cliente
        numero_medidor: Número/identificador del medidor (opcional)
        direccion: Dirección del medidor (opcional)
        fecha_inicio: Fecha de alta del medidor (opcional, formato YYYY-MM-DD)

    Returns:
        ID del medidor creado
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO medidores (cliente_id, numero_medidor, direccion, fecha_inicio)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    ''', (cliente_id, numero_medidor, direccion, fecha_inicio))
    medidor_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return medidor_id


def buscar_medidor_por_cliente(cliente_id: int) -> Optional[Dict]:
    """
    Busca el medidor de un cliente (asume 1 medidor por cliente).

    Args:
        cliente_id: ID del cliente

    Returns:
        Dict con datos del medidor o None si no existe
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM medidores WHERE cliente_id = %s', (cliente_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def obtener_o_crear_medidor(cliente_id: int) -> int:
    """
    Obtiene el ID del medidor de un cliente o lo crea si no existe.

    Args:
        cliente_id: ID del cliente

    Returns:
        ID del medidor
    """
    medidor = buscar_medidor_por_cliente(cliente_id)
    if medidor:
        return medidor['id']
    return crear_medidor(cliente_id)


def listar_medidores(cliente_id: int = None, busqueda: str = None,
                     estado: str = None) -> List[Dict]:
    """
    Lista medidores con filtros opcionales.

    Args:
        cliente_id: Filtrar por cliente específico
        busqueda: Texto para buscar en numero_medidor, direccion o nombre de cliente
        estado: 'activo' o 'inactivo', None para todos

    Returns:
        Lista de medidores con info del cliente y conteo de lecturas
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT m.*, c.nombre as cliente_nombre,
               COUNT(l.id) as num_lecturas
        FROM medidores m
        JOIN clientes c ON m.cliente_id = c.id
        LEFT JOIN lecturas l ON m.id = l.medidor_id
        WHERE 1=1
    '''
    params = []

    if cliente_id:
        query += ' AND m.cliente_id = %s'
        params.append(cliente_id)

    if busqueda:
        query += ''' AND (
            LOWER(m.numero_medidor) LIKE LOWER(%s) OR
            LOWER(m.direccion) LIKE LOWER(%s) OR
            LOWER(c.nombre) LIKE LOWER(%s)
        )'''
        busqueda_param = f'%{busqueda}%'
        params.extend([busqueda_param, busqueda_param, busqueda_param])

    if estado == 'activo':
        query += ' AND m.activo = 1'
    elif estado == 'inactivo':
        query += ' AND m.activo = 0'

    query += ' GROUP BY m.id, c.nombre ORDER BY c.nombre'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_medidor(medidor_id: int) -> Optional[Dict]:
    """Obtiene un medidor por ID con info del cliente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, c.nombre as cliente_nombre
        FROM medidores m
        JOIN clientes c ON m.cliente_id = c.id
        WHERE m.id = %s
    ''', (medidor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_medidor(medidor_id: int, numero_medidor: str = None,
                       direccion: str = None, cliente_id: int = None) -> bool:
    """Actualiza datos de un medidor."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if numero_medidor is not None:
        updates.append('numero_medidor = %s')
        params.append(numero_medidor if numero_medidor else None)
    if direccion is not None:
        updates.append('direccion = %s')
        params.append(direccion if direccion else None)
    if cliente_id is not None:
        updates.append('cliente_id = %s')
        params.append(cliente_id)

    if not updates:
        return False

    params.append(medidor_id)
    query = f'UPDATE medidores SET {", ".join(updates)} WHERE id = %s'

    cursor.execute(query, params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_medidor(medidor_id: int) -> tuple:
    """
    Elimina un medidor (solo si no tiene lecturas ni boletas).

    Returns:
        tuple: (exito: bool, mensaje: str)
            - (True, "ok") si se eliminó correctamente
            - (False, "lecturas") si tiene lecturas asociadas
            - (False, "boletas") si tiene boletas asociadas
            - (False, "error") si hubo un error
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar si tiene lecturas
    cursor.execute('SELECT COUNT(*) FROM lecturas WHERE medidor_id = %s', (medidor_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return (False, "lecturas")

    # Verificar si tiene boletas
    cursor.execute('SELECT COUNT(*) FROM boletas WHERE medidor_id = %s', (medidor_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return (False, "boletas")

    cursor.execute('DELETE FROM medidores WHERE id = %s', (medidor_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected > 0:
        return (True, "ok")
    return (False, "error")


def desactivar_medidor(medidor_id: int, fecha_baja: str, motivo_baja: str = None) -> bool:
    """
    Desactiva un medidor estableciendo activo=0 y registrando fecha y motivo de baja.

    Args:
        medidor_id: ID del medidor a desactivar
        fecha_baja: Fecha de baja (formato YYYY-MM-DD)
        motivo_baja: Motivo de la desactivación (opcional)

    Returns:
        True si se desactivó exitosamente, False en caso contrario
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE medidores
        SET activo = 0, fecha_baja = %s, motivo_baja = %s
        WHERE id = %s
    ''', (fecha_baja, motivo_baja, medidor_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def reactivar_medidor(medidor_id: int, fecha_inicio: str = None) -> bool:
    """
    Reactiva un medidor estableciendo activo=1 y limpiando fecha y motivo de baja.

    Args:
        medidor_id: ID del medidor a reactivar
        fecha_inicio: Nueva fecha de inicio (opcional, si se cambia)

    Returns:
        True si se reactivó exitosamente, False en caso contrario
    """
    conn = get_connection()
    cursor = conn.cursor()

    if fecha_inicio:
        cursor.execute('''
            UPDATE medidores
            SET activo = 1, fecha_baja = NULL, motivo_baja = NULL, fecha_inicio = %s
            WHERE id = %s
        ''', (fecha_inicio, medidor_id))
    else:
        cursor.execute('''
            UPDATE medidores
            SET activo = 1, fecha_baja = NULL, motivo_baja = NULL
            WHERE id = %s
        ''', (medidor_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_cliente(cliente_id: int) -> tuple:
    """
    Elimina un cliente (solo si no tiene medidores).

    Returns:
        tuple: (exito: bool, mensaje: str)
            - (True, "ok") si se eliminó correctamente
            - (False, "medidores") si tiene medidores asociados
            - (False, "error") si hubo un error
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Verificar si tiene medidores
    cursor.execute('SELECT COUNT(*) FROM medidores WHERE cliente_id = %s', (cliente_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return (False, "medidores")

    cursor.execute('DELETE FROM clientes WHERE id = %s', (cliente_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()

    if affected > 0:
        return (True, "ok")
    return (False, "error")


# ============== LECTURAS ==============

def crear_lectura(medidor_id: int, lectura_m3: int, fecha_lectura: date,
                  foto_path: str, foto_nombre: str, año: int, mes: int) -> int:
    """
    Crea una nueva lectura.

    Args:
        medidor_id: ID del medidor
        lectura_m3: Valor de la lectura en m3
        fecha_lectura: Fecha de la lectura
        foto_path: Ruta a la foto
        foto_nombre: Nombre original del archivo
        año: Año del periodo
        mes: Mes del periodo

    Returns:
        ID de la lectura creada
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO lecturas (medidor_id, lectura_m3, fecha_lectura, foto_path, foto_nombre, año, mes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (medidor_id, lectura_m3, fecha_lectura, foto_path, foto_nombre, año, mes))
    lectura_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return lectura_id


def lectura_existe(medidor_id: int, año: int, mes: int) -> bool:
    """
    Verifica si ya existe una lectura para un medidor en un periodo.

    Args:
        medidor_id: ID del medidor
        año: Año del periodo
        mes: Mes del periodo

    Returns:
        True si existe, False si no
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM lecturas
        WHERE medidor_id = %s AND año = %s AND mes = %s
    ''', (medidor_id, año, mes))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0


def listar_lecturas(medidor_id: int = None, año: int = None, mes: int = None,
                    cliente_id: int = None, limit: int = 100, offset: int = 0,
                    orden_col: str = None, orden_dir: str = 'asc',
                    solo_incompletos: bool = False) -> List[Dict]:
    """
    Lista lecturas con filtros opcionales.

    Args:
        medidor_id: Filtrar por medidor
        año: Filtrar por año
        mes: Filtrar por mes
        cliente_id: Filtrar por cliente
        limit: Límite de resultados
        offset: Desplazamiento para paginación
        orden_col: Columna para ordenar (id, cliente, periodo, lectura_m3, fecha_lectura)
        orden_dir: Dirección del orden (asc, desc)
        solo_incompletos: Si True, solo muestra lecturas de medidores incompletos

    Returns:
        Lista de lecturas con info del medidor y cliente
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT l.*, m.numero_medidor, c.nombre as cliente_nombre, c.id as cliente_id
        FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if medidor_id:
        query += ' AND l.medidor_id = %s'
        params.append(medidor_id)
    if año:
        query += ' AND l.año = %s'
        params.append(año)
    if mes:
        query += ' AND l.mes = %s'
        params.append(mes)
    if cliente_id:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if solo_incompletos:
        medidores_inc = obtener_medidores_incompletos()
        if medidores_inc:
            placeholders = ','.join('%s' * len(medidores_inc))
            query += f' AND l.medidor_id IN ({placeholders})'
            params.extend(medidores_inc)
        else:
            # No hay medidores incompletos, no devolver nada
            query += ' AND 1=0'

    # Mapeo de columnas permitidas
    columnas_orden = {
        'id': 'l.id',
        'cliente': 'c.nombre',
        'periodo': 'l.año, l.mes',
        'lectura_m3': 'l.lectura_m3',
        'fecha_lectura': 'l.fecha_lectura'
    }

    # Validar dirección
    direccion = 'DESC' if orden_dir == 'desc' else 'ASC'

    if orden_col and orden_col in columnas_orden:
        query += f' ORDER BY {columnas_orden[orden_col]} {direccion}'
        # Agregar orden secundario para periodo
        if orden_col == 'periodo':
            pass  # Ya tiene año y mes
        else:
            query += ', l.año DESC, l.mes DESC'
    else:
        query += ' ORDER BY l.año DESC, l.mes DESC, c.nombre'

    query += ' LIMIT %s OFFSET %s'
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_lectura(lectura_id: int) -> Optional[Dict]:
    """Obtiene una lectura por ID con info completa."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.*, m.numero_medidor, c.nombre as cliente_nombre, c.id as cliente_id
        FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE l.id = %s
    ''', (lectura_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_lectura(lectura_id: int, lectura_m3: int = None,
                       fecha_lectura: date = None) -> bool:
    """Actualiza datos de una lectura."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []

    if lectura_m3 is not None:
        updates.append('lectura_m3 = %s')
        params.append(lectura_m3)
    if fecha_lectura is not None:
        updates.append('fecha_lectura = %s')
        params.append(fecha_lectura)

    if not updates:
        return False

    params.append(lectura_id)
    query = f'UPDATE lecturas SET {", ".join(updates)} WHERE id = %s'

    cursor.execute(query, params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_lectura(lectura_id: int) -> bool:
    """Elimina una lectura."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lecturas WHERE id = %s', (lectura_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def contar_lecturas(medidor_id: int = None, año: int = None, mes: int = None,
                    cliente_id: int = None, solo_incompletos: bool = False) -> int:
    """Cuenta lecturas con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT COUNT(*) FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if medidor_id:
        query += ' AND l.medidor_id = %s'
        params.append(medidor_id)
    if año:
        query += ' AND l.año = %s'
        params.append(año)
    if mes:
        query += ' AND l.mes = %s'
        params.append(mes)
    if cliente_id:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if solo_incompletos:
        medidores_inc = obtener_medidores_incompletos()
        if medidores_inc:
            placeholders = ','.join('%s' * len(medidores_inc))
            query += f' AND l.medidor_id IN ({placeholders})'
            params.extend(medidores_inc)
        else:
            query += ' AND 1=0'

    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ============== ESTADÍSTICAS ==============

def obtener_medidores_incompletos() -> List[int]:
    """
    Obtiene IDs de medidores que no tienen todos los meses registrados
    desde diciembre 2023 hasta noviembre 2025.

    Returns:
        Lista de IDs de medidores incompletos
    """
    total_periodos = 24  # dic 2023 + 12 meses 2024 + 11 meses 2025

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener medidores que NO tienen todos los periodos
    cursor.execute('''
        SELECT m.id
        FROM medidores m
        WHERE (
            SELECT COUNT(DISTINCT l.año * 100 + l.mes)
            FROM lecturas l
            WHERE l.medidor_id = m.id
            AND (
                (l.año = 2023 AND l.mes = 12) OR
                (l.año = 2024) OR
                (l.año = 2025 AND l.mes <= 11)
            )
        ) < %s
    ''', (total_periodos,))

    rows = cursor.fetchall()
    conn.close()
    return [row[0] if isinstance(row, tuple) else row['id'] for row in rows]


def obtener_clientes_incompletos() -> List[int]:
    """
    Obtiene IDs de clientes que tienen al menos un medidor incompleto.

    Returns:
        Lista de IDs de clientes incompletos
    """
    total_periodos = 24  # dic 2023 + 12 meses 2024 + 11 meses 2025

    conn = get_connection()
    cursor = conn.cursor()

    # Obtener clientes con al menos un medidor incompleto
    cursor.execute('''
        SELECT DISTINCT m.cliente_id
        FROM medidores m
        WHERE (
            SELECT COUNT(DISTINCT l.año * 100 + l.mes)
            FROM lecturas l
            WHERE l.medidor_id = m.id
            AND (
                (l.año = 2023 AND l.mes = 12) OR
                (l.año = 2024) OR
                (l.año = 2025 AND l.mes <= 11)
            )
        ) < %s
    ''', (total_periodos,))

    rows = cursor.fetchall()
    conn.close()
    return [row[0] if isinstance(row, tuple) else row['cliente_id'] for row in rows]


def obtener_años_disponibles() -> List[int]:
    """Obtiene lista de años con lecturas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT año FROM lecturas ORDER BY año DESC')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def obtener_fechas_comunes_por_periodo(periodos: List[tuple]) -> Dict[tuple, Optional[int]]:
    """
    Obtiene el día más común de lectura para cada periodo.
    La fecha de lectura de un periodo (mes X, año Y) se toma en el mes siguiente.
    Por ejemplo: periodo marzo 2024 -> lectura tomada en abril 2024.

    Args:
        periodos: Lista de tuplas (año, mes) representando los periodos

    Returns:
        Dict con (año, mes) como key y el día más común como value (None si no hay datos)
    """
    if not periodos:
        return {}

    conn = get_connection()
    cursor = conn.cursor()

    resultado = {}

    for año, mes in periodos:
        # Calcular el mes de lectura (mes siguiente al periodo)
        if mes == 12:
            mes_lectura = 1
            año_lectura = año + 1
        else:
            mes_lectura = mes + 1
            año_lectura = año

        # Buscar el día más común en las lecturas de ese periodo
        # Formato de fecha: YYYY-MM-DD, extraemos el día
        cursor.execute('''
            SELECT CAST(SUBSTRING(fecha_lectura, 9, 2) AS INTEGER) as dia, COUNT(*) as cuenta
            FROM lecturas
            WHERE año = %s AND mes = %s
            AND SUBSTRING(fecha_lectura, 1, 7) = %s
            GROUP BY dia
            ORDER BY cuenta DESC
            LIMIT 1
        ''', (año, mes, f'{año_lectura:04d}-{mes_lectura:02d}'))

        row = cursor.fetchone()
        if row:
            resultado[(año, mes)] = row[0]
        else:
            resultado[(año, mes)] = None

    conn.close()
    return resultado


def crear_lecturas_multiple(medidor_id: int, lectura_m3: int, periodos_fechas: List[Dict]) -> Dict:
    """
    Crea múltiples lecturas para un medidor, omitiendo periodos que ya existen.

    Args:
        medidor_id: ID del medidor
        lectura_m3: Valor de lectura en m3 (igual para todas)
        periodos_fechas: Lista de dicts con {año, mes, fecha_lectura}

    Returns:
        Dict con 'creados' (lista de IDs), 'omitidos' (cantidad de omitidos)
    """
    conn = get_connection()
    cursor = conn.cursor()

    ids_creados = []
    omitidos = 0

    for pf in periodos_fechas:
        # Verificar si ya existe lectura para este medidor/periodo
        cursor.execute('''
            SELECT id FROM lecturas
            WHERE medidor_id = %s AND año = %s AND mes = %s
        ''', (medidor_id, pf['año'], pf['mes']))

        if cursor.fetchone():
            omitidos += 1
            continue

        cursor.execute('''
            INSERT INTO lecturas (medidor_id, lectura_m3, fecha_lectura, foto_path, foto_nombre, año, mes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (medidor_id, lectura_m3, pf['fecha_lectura'], '', 'sin_foto', pf['año'], pf['mes']))
        ids_creados.append(cursor.fetchone()[0])

    conn.commit()
    conn.close()
    return {'creados': ids_creados, 'omitidos': omitidos}


def obtener_estadisticas() -> Dict:
    """Obtiene estadísticas generales del sistema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM clientes')
    num_clientes = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM medidores')
    num_medidores = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM lecturas')
    num_lecturas = cursor.fetchone()[0]

    conn.close()

    return {
        'clientes': num_clientes,
        'medidores': num_medidores,
        'lecturas': num_lecturas
    }


def obtener_clientes_sin_lectura(año: int, mes: int) -> List[Dict]:
    """
    Filtrado AUTOMÁTICO de clientes pendientes.
    Retorna SOLO clientes con medidores activos que NO tienen lectura
    registrada en el período especificado.

    Args:
        año: Año del período
        mes: Mes del período (1-12)

    Returns:
        Lista de dicts con:
        - cliente_id: ID del cliente
        - cliente_nombre: Nombre del cliente
        - nombre_completo: Nombre completo del cliente
        - medidores: Lista de dicts con id, numero, direccion
        - num_medidores: Cantidad de medidores del cliente
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Query con LEFT JOIN para detectar ausencia de lectura
    query = '''
        SELECT DISTINCT
            c.id as cliente_id,
            c.nombre as cliente_nombre,
            c.nombre_completo,
            STRING_AGG(
                CAST(m.id AS TEXT) || '|' ||
                COALESCE(m.numero_medidor, 'S/N') || '|' ||
                COALESCE(m.direccion, ''),
                ';'
            ) as medidores_info
        FROM clientes c
        INNER JOIN medidores m ON c.id = m.cliente_id
        LEFT JOIN lecturas l ON m.id = l.medidor_id
            AND l.año = %s
            AND l.mes = %s
        WHERE m.activo = 1
            AND l.id IS NULL
        GROUP BY c.id, c.nombre, c.nombre_completo
        ORDER BY c.nombre
    '''

    cursor.execute(query, (año, mes))
    rows = cursor.fetchall()
    conn.close()

    # Procesar resultado para estructura más amigable
    resultado = []
    for row in rows:
        medidores_str = row['medidores_info']
        medidores_list = []

        if medidores_str:
            for med_info in medidores_str.split(';'):
                parts = med_info.split('|')
                if len(parts) == 3:
                    medidores_list.append({
                        'id': int(parts[0]),
                        'numero': parts[1],
                        'direccion': parts[2]
                    })

        resultado.append({
            'cliente_id': row['cliente_id'],
            'cliente_nombre': row['cliente_nombre'],
            'nombre_completo': row['nombre_completo'],
            'medidores': medidores_list,
            'num_medidores': len(medidores_list)
        })

    return resultado


def buscar_cliente_por_rut(rut: str) -> Optional[Dict]:
    """
    Busca un cliente por su RUT normalizado.

    Args:
        rut: RUT normalizado (sin puntos ni guiones, mayúsculas)

    Returns:
        Dict con datos del cliente o None si no existe
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE rut = %s', (rut,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None
