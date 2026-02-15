# utils/helpers.py
from geopy.distance import geodesic

def validar_ubicacion(lat_escaneo, lon_escaneo, lat_clase, lon_clase):
    """
    Valida que la ubicación esté dentro del radio permitido
    Radio permitido: 5 metros (+2 metros de tolerancia = 7m máximo)
    """
    punto_escaneo = (lat_escaneo, lon_escaneo)
    punto_clase = (lat_clase, lon_clase)
    
    distancia = geodesic(punto_escaneo, punto_clase).meters
    
    # Radio permitido: 5m + 2m de tolerancia = 7m
    if distancia <= 7:
        return True, distancia
    else:
        return False, distancia

def calcular_porcentaje(asistencias, total_clases):
    """Calcula porcentaje de asistencia"""
    if total_clases == 0:
        return 0
    return (asistencias / total_clases) * 100

def obtener_color_semaforo(porcentaje):
    """Retorna color según el porcentaje"""
    if porcentaje >= 80:
        return 'verde'
    elif porcentaje >= 50:
        return 'amarillo'
    elif porcentaje >= 30:  # Umbral para naranja
        return 'naranja'
    else:
        return 'rojo'