"""
Módulo de validación de fechas
Valida y corrige fechas inconsistentes en las fotos de una carpeta
"""
import os
from collections import Counter
from datetime import date
from typing import List, Dict, Optional, Tuple
from .parser import parsear_nombre_archivo, extraer_periodo_de_ruta


def obtener_carpeta_fotos(carpeta: str) -> str:
    """
    Obtiene la carpeta real donde están las fotos.
    Algunas carpetas tienen las fotos directamente, otras en una subcarpeta 'lecturas/'.
    """
    subcarpeta = os.path.join(carpeta, 'lecturas')
    if os.path.isdir(subcarpeta):
        return subcarpeta
    return carpeta


def obtener_fechas_carpeta(carpeta: str) -> List[Tuple[str, date]]:
    """
    Obtiene todas las fechas de las fotos en una carpeta.

    Args:
        carpeta: Ruta a la carpeta con fotos

    Returns:
        Lista de tuplas (nombre_archivo, fecha)
    """
    fechas = []
    carpeta_fotos = obtener_carpeta_fotos(carpeta)

    if not os.path.exists(carpeta_fotos):
        return fechas

    for archivo in os.listdir(carpeta_fotos):
        if archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            datos = parsear_nombre_archivo(archivo)
            if datos and datos['fecha']:
                fechas.append((archivo, datos['fecha']))

    return fechas


def obtener_fecha_mas_frecuente(fechas: List[Tuple[str, date]]) -> Optional[date]:
    """
    Determina la fecha más frecuente (moda) en una lista de fechas.

    Args:
        fechas: Lista de tuplas (nombre_archivo, fecha)

    Returns:
        La fecha más frecuente o None si la lista está vacía
    """
    if not fechas:
        return None

    solo_fechas = [f[1] for f in fechas]
    contador = Counter(solo_fechas)
    fecha_comun, _ = contador.most_common(1)[0]
    return fecha_comun


def fecha_es_coherente(fecha: date, anio_periodo: int, mes_periodo: int) -> bool:
    """
    Valida si una fecha es coherente con el periodo de la carpeta.

    Regla: La fecha de lectura debe ser del mismo mes o mes siguiente al periodo.
    Ejemplo: Si el periodo es junio (06), la fecha puede ser de junio o julio.

    Args:
        fecha: Fecha a validar
        anio_periodo: Año del periodo (de la carpeta)
        mes_periodo: Mes del periodo (de la carpeta)

    Returns:
        True si la fecha es coherente, False si no
    """
    # Meses válidos: el mes del periodo o el siguiente
    meses_validos = [mes_periodo]
    if mes_periodo == 12:
        # Si es diciembre, el siguiente es enero del anio siguiente
        meses_validos.append(1)
    else:
        meses_validos.append(mes_periodo + 1)

    # Años válidos
    anios_validos = [anio_periodo]
    if mes_periodo == 12:
        anios_validos.append(anio_periodo + 1)

    # Verificar coherencia
    if fecha.year in anios_validos and fecha.month in meses_validos:
        return True

    # Caso especial: si es enero del periodo, también aceptar diciembre del anio anterior
    if mes_periodo == 1 and fecha.month == 12 and fecha.year == anio_periodo - 1:
        return True

    return False


def validar_fechas_carpeta(carpeta: str) -> Dict:
    """
    Valida todas las fechas de una carpeta y genera correcciones.

    Args:
        carpeta: Ruta a la carpeta con fotos

    Returns:
        Dict con:
        - 'periodo': (anio, mes) del periodo
        - 'fecha_correcta': fecha más frecuente
        - 'validas': lista de archivos con fecha válida
        - 'corregidas': lista de tuplas (archivo, fecha_original, fecha_corregida)
        - 'sin_parsear': archivos que no se pudieron parsear
    """
    resultado = {
        'periodo': None,
        'fecha_correcta': None,
        'validas': [],
        'corregidas': [],
        'sin_parsear': []
    }

    # Obtener periodo de la ruta
    periodo = extraer_periodo_de_ruta(carpeta)
    if not periodo:
        return resultado

    anio_periodo, mes_periodo = periodo
    resultado['periodo'] = periodo

    # Obtener todas las fechas
    fechas = obtener_fechas_carpeta(carpeta)

    # Determinar fecha más frecuente
    fecha_correcta = obtener_fecha_mas_frecuente(fechas)
    resultado['fecha_correcta'] = fecha_correcta

    if not fecha_correcta:
        return resultado

    # Validar cada archivo
    for archivo in os.listdir(carpeta):
        if not archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        datos = parsear_nombre_archivo(archivo)
        if not datos:
            resultado['sin_parsear'].append(archivo)
            continue

        fecha_archivo = datos['fecha']

        if fecha_es_coherente(fecha_archivo, anio_periodo, mes_periodo):
            resultado['validas'].append(archivo)
        else:
            # La fecha no es coherente, se debe corregir
            resultado['corregidas'].append({
                'archivo': archivo,
                'fecha_original': fecha_archivo,
                'fecha_corregida': fecha_correcta
            })

    return resultado


def generar_reporte_correcciones(carpetas: List[str], archivo_log: str = None) -> str:
    """
    Genera un reporte de todas las correcciones necesarias.

    Args:
        carpetas: Lista de carpetas a validar
        archivo_log: Ruta opcional para guardar el log

    Returns:
        String con el reporte
    """
    lineas = ["# Reporte de Validación de Fechas", ""]

    total_validas = 0
    total_corregidas = 0
    total_sin_parsear = 0

    for carpeta in carpetas:
        resultado = validar_fechas_carpeta(carpeta)

        if resultado['periodo']:
            anio, mes = resultado['periodo']
            lineas.append(f"## Carpeta: {carpeta}")
            lineas.append(f"Periodo: {anio}/{mes:02d}")
            lineas.append(f"Fecha correcta detectada: {resultado['fecha_correcta']}")
            lineas.append(f"Archivos válidos: {len(resultado['validas'])}")
            lineas.append(f"Archivos corregidos: {len(resultado['corregidas'])}")

            total_validas += len(resultado['validas'])
            total_corregidas += len(resultado['corregidas'])
            total_sin_parsear += len(resultado['sin_parsear'])

            if resultado['corregidas']:
                lineas.append("\n### Correcciones:")
                for corr in resultado['corregidas']:
                    lineas.append(f"  - {corr['archivo']}: {corr['fecha_original']} -> {corr['fecha_corregida']}")

            lineas.append("")

    lineas.append("## Resumen")
    lineas.append(f"Total archivos válidos: {total_validas}")
    lineas.append(f"Total archivos corregidos: {total_corregidas}")
    lineas.append(f"Total sin parsear: {total_sin_parsear}")

    reporte = "\n".join(lineas)

    if archivo_log:
        with open(archivo_log, 'w', encoding='utf-8') as f:
            f.write(reporte)

    return reporte


if __name__ == '__main__':
    # Test básico
    print("Test de validación de fechas")
    print(fecha_es_coherente(date(2024, 7, 5), 2024, 6))  # True (julio para junio)
    print(fecha_es_coherente(date(2024, 3, 10), 2024, 6))  # False (marzo para junio)
