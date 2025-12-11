"""
Módulo de modelos - Funciones CRUD para clientes, medidores y lecturas
"""
from datetime import date
from typing import Optional, List, Dict
from .database import get_connection


# ============== CLIENTES ==============

def crear_cliente(nombre: str, nombre_completo: str = None, rut: str = None) -> int:
    """
    Crea un nuevo cliente.

    Args:
        nombre: Nombre normalizado del cliente
        nombre_completo: Nombre legal completo (opcional)
        rut: RUT del cliente (opcional)

    Returns:
        ID del cliente creado
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clientes (nombre, nombre_completo, rut)
        VALUES (?, ?, ?)
    ''', (nombre, nombre_completo, rut))
    conn.commit()
    cliente_id = cursor.lastrowid
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
    cursor.execute('SELECT * FROM clientes WHERE nombre = ?', (nombre,))
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


def listar_clientes() -> List[Dict]:
    """Lista todos los clientes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*,
               COUNT(m.id) as num_medidores
        FROM clientes c
        LEFT JOIN medidores m ON c.id = m.cliente_id
        GROUP BY c.id
        ORDER BY c.nombre
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def obtener_cliente(cliente_id: int) -> Optional[Dict]:
    """Obtiene un cliente por ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_cliente(cliente_id: int, nombre_completo: str = None, rut: str = None) -> bool:
    """Actualiza datos de un cliente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE clientes
        SET nombre_completo = COALESCE(?, nombre_completo),
            rut = COALESCE(?, rut)
        WHERE id = ?
    ''', (nombre_completo, rut, cliente_id))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ============== MEDIDORES ==============

def crear_medidor(cliente_id: int, numero_medidor: str = None, direccion: str = None) -> int:
    """
    Crea un nuevo medidor asociado a un cliente.

    Args:
        cliente_id: ID del cliente
        numero_medidor: Número/identificador del medidor (opcional)
        direccion: Dirección del medidor (opcional)

    Returns:
        ID del medidor creado
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO medidores (cliente_id, numero_medidor, direccion)
        VALUES (?, ?, ?)
    ''', (cliente_id, numero_medidor, direccion))
    conn.commit()
    medidor_id = cursor.lastrowid
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
    cursor.execute('SELECT * FROM medidores WHERE cliente_id = ?', (cliente_id,))
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


def listar_medidores() -> List[Dict]:
    """Lista todos los medidores con información del cliente."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.*, c.nombre as cliente_nombre,
               COUNT(l.id) as num_lecturas
        FROM medidores m
        JOIN clientes c ON m.cliente_id = c.id
        LEFT JOIN lecturas l ON m.id = l.medidor_id
        GROUP BY m.id
        ORDER BY c.nombre
    ''')
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
        WHERE m.id = ?
    ''', (medidor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


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
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (medidor_id, lectura_m3, fecha_lectura, foto_path, foto_nombre, año, mes))
    conn.commit()
    lectura_id = cursor.lastrowid
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
        WHERE medidor_id = ? AND año = ? AND mes = ?
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
        query += ' AND l.medidor_id = ?'
        params.append(medidor_id)
    if año:
        query += ' AND l.año = ?'
        params.append(año)
    if mes:
        query += ' AND l.mes = ?'
        params.append(mes)
    if cliente_id:
        query += ' AND c.id = ?'
        params.append(cliente_id)

    if solo_incompletos:
        medidores_inc = obtener_medidores_incompletos()
        if medidores_inc:
            placeholders = ','.join('?' * len(medidores_inc))
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

    query += ' LIMIT ? OFFSET ?'
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
        WHERE l.id = ?
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
        updates.append('lectura_m3 = ?')
        params.append(lectura_m3)
    if fecha_lectura is not None:
        updates.append('fecha_lectura = ?')
        params.append(fecha_lectura)

    if not updates:
        return False

    params.append(lectura_id)
    query = f'UPDATE lecturas SET {", ".join(updates)} WHERE id = ?'

    cursor.execute(query, params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_lectura(lectura_id: int) -> bool:
    """Elimina una lectura."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM lecturas WHERE id = ?', (lectura_id,))
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
        query += ' AND l.medidor_id = ?'
        params.append(medidor_id)
    if año:
        query += ' AND l.año = ?'
        params.append(año)
    if mes:
        query += ' AND l.mes = ?'
        params.append(mes)
    if cliente_id:
        query += ' AND c.id = ?'
        params.append(cliente_id)

    if solo_incompletos:
        medidores_inc = obtener_medidores_incompletos()
        if medidores_inc:
            placeholders = ','.join('?' * len(medidores_inc))
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
        ) < ?
    ''', (total_periodos,))

    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


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
        ) < ?
    ''', (total_periodos,))

    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def obtener_años_disponibles() -> List[int]:
    """Obtiene lista de años con lecturas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT año FROM lecturas ORDER BY año DESC')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


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
