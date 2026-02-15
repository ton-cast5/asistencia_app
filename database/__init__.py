# database/__init__.py
"""
Módulo de base de datos para Asistencia App
Maneja todas las conexiones y operaciones con Supabase
"""

from .supabase_client import SupabaseClient

# Instancia global del cliente (singleton)
_db_instance = None

def get_db():
    """
    Retorna una instancia única del cliente de Supabase
    Patrón Singleton para evitar múltiples conexiones
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = SupabaseClient()
    return _db_instance

def init_db():
    """
    Inicializa la conexión a la base de datos
    Verifica que la conexión sea exitosa
    """
    try:
        db = get_db()
        # Hacer una consulta simple para verificar conexión
        result = db.query('usuarios', params={'select': 'count', 'limit': 1})
        print("✅ Conexión a Supabase establecida correctamente")
        return True
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        return False

# Exportar todo lo necesario
__all__ = ['get_db', 'init_db', 'SupabaseClient']