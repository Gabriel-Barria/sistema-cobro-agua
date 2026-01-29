"""
Módulo de parseo - Extrae información del nombre de archivos de fotos
Formato esperado: nombre_lectura_fecha.jpg
Ejemplo: carlos aguero_150_07-02-2025.jpg
"""
import os
import re
from datetime import datetime
from typing import Optional, Tuple


def parsear_nombre_archivo(nombre_archivo: str) -> Optional[dict]:
    """
    Parsea el nombre de un archivo de foto y extrae la información.

    Args:
        nombre_archivo: Nombre del archivo (ej: 'carlos aguero_150_07-02-2025.jpg')

    Returns:
        Dict con: nombre, lectura, fecha, o None si no se pudo parsear
    """
    # Remover extensión
    nombre_sin_ext = os.path.splitext(nombre_archivo)[0]

    # Patrón: nombre_lectura_fecha
    # La fecha puede ser DD-MM-YYYY
    patron = r'^(.+)_(\d+)_(\d{2}-\d{2}-\d{4})$'
    match = re.match(patron, nombre_sin_ext)

    if not match:
        return None

    nombre_cliente = match.group(1).strip().lower()
    lectura = int(match.group(2))
    fecha_str = match.group(3)

    # Parsear fecha (formato DD-MM-YYYY)
    try:
        fecha = datetime.strptime(fecha_str, '%d-%m-%Y').date()
    except ValueError:
        return None

    return {
        'nombre': nombre_cliente,
        'lectura': lectura,
        'fecha': fecha,
        'fecha_str': fecha_str
    }


def extraer_periodo_de_ruta(ruta_archivo: str) -> Optional[Tuple[int, int]]:
    """
    Extrae el anio y mes del periodo de la ruta del archivo.

    Args:
        ruta_archivo: Ruta completa al archivo
        Ejemplo: .../2024/06_junio/archivo.jpg o .../2023/diciembre/archivo.jpg

    Returns:
        Tupla (anio, mes) o None si no se pudo extraer
    """
    # Mapa de nombres de mes a número
    meses_nombres = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    # Normalizar separadores
    ruta = ruta_archivo.replace('\\', '/')
    partes = ruta.split('/')

    anio = None
    mes = None

    for i, parte in enumerate(partes):
        # Buscar anio (4 dígitos)
        if re.match(r'^\d{4}$', parte):
            anio = int(parte)
            # El siguiente elemento debería ser el mes
            if i + 1 < len(partes):
                siguiente = partes[i + 1].lower()
                # Formato: 01_enero, 02_febrero, etc.
                match_mes = re.match(r'^(\d{2})_', siguiente)
                if match_mes:
                    mes = int(match_mes.group(1))
                else:
                    # Intentar con nombre de mes sin prefijo (ej: "diciembre")
                    for nombre, num in meses_nombres.items():
                        if nombre in siguiente:
                            mes = num
                            break

    if anio and mes:
        return (anio, mes)
    return None


def normalizar_nombre(nombre: str) -> str:
    """
    Normaliza un nombre de cliente para evitar duplicados.
    - Convierte a minúsculas
    - Elimina espacios extra
    """
    return ' '.join(nombre.lower().split())


if __name__ == '__main__':
    # Tests
    test_casos = [
        'carlos aguero_150_07-02-2025.jpg',
        'maría ñanco_43_07-04-2024.jpg',
        'guido quintuy fruteria_117_07-02-2025.jpg',
        'archivo_invalido.jpg',
    ]

    for caso in test_casos:
        resultado = parsear_nombre_archivo(caso)
        print(f"{caso} -> {resultado}")

    # Test de ruta
    ruta_test = 'C:/Users/ibarr/Documents/comprobantes/lecturas/2024/06_junio/test.jpg'
    periodo = extraer_periodo_de_ruta(ruta_test)
    print(f"\nRuta: {ruta_test}")
    print(f"Periodo: {periodo}")
