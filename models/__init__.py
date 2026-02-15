# models/__init__.py (Versión PRO)
"""
Módulo de modelos para Asistencia App
Contiene toda la lógica de negocio y manipulación de datos
"""

from .user import User, Alumno, Profesor
from .attendance import Clase, Asistencia, QRGenerator
from datetime import datetime
import re

# Instancias globales
_current_user = None
_current_class = None

# ========== Getters/Setters ==========
def get_current_user():
    """Retorna el usuario actualmente logueado"""
    global _current_user
    return _current_user

def set_current_user(user):
    """Establece el usuario actual"""
    global _current_user
    _current_user = user

def get_current_class():
    """Retorna la clase actualmente activa"""
    global _current_class
    return _current_class

def set_current_class(clase):
    """Establece la clase activa"""
    global _current_class
    _current_class = clase

def clear_current_data():
    """Limpia todos los datos de sesión actual"""
    global _current_user, _current_class
    _current_user = None
    _current_class = None

# ========== Validadores ==========
def validar_matricula(matricula):
    """
    Valida formato de matrícula
    Ejemplo: 2023-1234 o 2023-ABCD
    """
    patron = r'^\d{4}-[A-Z0-9]{4,8}$'
    return bool(re.match(patron, matricula))

def validar_email(email):
    """Valida formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))

def validar_telefono_id(telefono_id):
    """Valida que el ID del teléfono tenga formato correcto"""
    # Ejemplo: device_abc123 o android_12345 o ios_67890
    patron = r'^(device|android|ios)_[a-zA-Z0-9]{6,}$'
    return bool(re.match(patron, telefono_id))

# ========== Helpers de fechas ==========
def fecha_actual():
    """Retorna fecha actual formateada"""
    return datetime.now().strftime('%Y-%m-%d')

def hora_actual():
    """Retorna hora actual formateada"""
    return datetime.now().strftime('%H:%M:%S')

def timestamp_actual():
    """Retorna timestamp completo"""
    return datetime.now().isoformat()

# ========== Constantes ==========
class ColoresSemaforo:
    """Constantes para los colores del semáforo"""
    VERDE = 'verde'
    AMARILLO = 'amarillo'
    NARANJA = 'naranja'
    ROJO = 'rojo'
    
    @classmethod
    def obtener_color(cls, porcentaje):
        """Retorna color según porcentaje"""
        if porcentaje >= 80:
            return cls.VERDE
        elif porcentaje >= 50:
            return cls.AMARILLO
        elif porcentaje >= 30:
            return cls.NARANJA
        else:
            return cls.ROJO

class Roles:
    """Constantes para roles de usuario"""
    ALUMNO = 'alumno'
    PROFESOR = 'profesor'
    
    @classmethod
    def es_valido(cls, rol):
        """Valida si un rol es correcto"""
        return rol in [cls.ALUMNO, cls.PROFESOR]

# ========== Exportaciones ==========
__all__ = [
    # Modelos principales
    'User', 
    'Alumno', 
    'Profesor',
    'Clase', 
    'Asistencia', 
    'QRGenerator',
    
    # Getters/Setters
    'get_current_user',
    'set_current_user',
    'get_current_class',
    'set_current_class',
    'clear_current_data',
    
    # Validadores
    'validar_matricula',
    'validar_email',
    'validar_telefono_id',
    
    # Helpers de fecha
    'fecha_actual',
    'hora_actual',
    'timestamp_actual',
    
    # Constantes
    'ColoresSemaforo',
    'Roles'
]