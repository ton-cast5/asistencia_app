from database import get_db

class User:
    @staticmethod
    def find_by_email(email):
        db = get_db()
        result = db.query('usuarios', params={'email': f'eq.{email}'})
        return result[0] if result else None

from database import get_db
from models import validar_matricula, validar_email, Roles

class User:
    def __init__(self, data):
        self.id = data.get('id')
        self.matricula = data.get('matricula')
        self.nombre = data.get('nombre')
        self.email = data.get('email')
        self.rol = data.get('rol')
        self.telefono_id = data.get('telefono_id')
    
    @staticmethod
    def crear_alumno(matricula, nombre, email, telefono_id):
        # Validar datos
        if not validar_matricula(matricula):
            raise ValueError('Matrícula inválida')
        if not validar_email(email):
            raise ValueError('Email inválido')
        
        db = get_db()
        data = {
            'matricula': matricula,
            'nombre': nombre,
            'email': email,
            'rol': Roles.ALUMNO,
            'telefono_id': telefono_id
        }
        result = db.query('usuarios', method='POST', data=data)
        return User(result[0]) if result else None