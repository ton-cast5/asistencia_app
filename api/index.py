# api/index.py - SOLO APIs, sin frontend
import os
import hashlib
import secrets
import re
import json
from datetime import datetime, date
from dotenv import load_dotenv
from database import init_db, get_db
from flask import Flask, request, jsonify

app = Flask(__name__)

# Cargar variables de entorno
load_dotenv()

# ========== FUNCIONES DE UTILERÍA ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generar_token():
    return secrets.token_urlsafe(32)

def validar_matricula(matricula):
    patron = r'^\d{4}-[A-Z0-9]{4,8}$'
    return bool(re.match(patron, matricula))

def validar_email(email):
    patron = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(patron, email))

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Fórmula de Haversine para distancia en metros"""
    if not all([lat1, lon1, lat2, lon2]):
        return None
    import math
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Inicializar BD (esto corre en cold start, pero es necesario)
init_db()

# ========== API DE REGISTRO ==========
def handler_register(request):
    """POST /api/register"""
    try:
        data = request.get_json()
        
        required_fields = ['matricula', 'nombre', 'email', 'password', 'rol', 'telefono_id']
        for field in required_fields:
            if field not in data:
                return {'success': False, 'message': f'Falta campo: {field}'}, 400
        
        if not validar_matricula(data['matricula']):
            return {'success': False, 'message': 'Matrícula inválida. Formato: 2024-1234'}, 400
        
        if not validar_email(data['email']):
            return {'success': False, 'message': 'Email inválido'}, 400
        
        if len(data['password']) < 8:
            return {'success': False, 'message': 'La contraseña debe tener al menos 8 caracteres'}, 400
        
        db = get_db()
        
        # Verificar duplicados
        for field in ['email', 'matricula', 'telefono_id']:
            existing = db.query('usuarios', params={field: f'eq.{data[field]}'})
            if existing and len(existing) > 0:
                return {'success': False, 'message': f'{field} ya está registrado'}, 400
        
        # Crear usuario
        new_user = {
            'matricula': data['matricula'],
            'nombre': data['nombre'],
            'email': data['email'],
            'password_hash': hash_password(data['password']),
            'rol': data['rol'],
            'telefono_id': data['telefono_id'],
            'created_at': datetime.now().isoformat()
        }
        
        result = db.query('usuarios', method='POST', data=new_user)
        
        if result and len(result) > 0:
            return {
                'success': True,
                'message': 'Usuario registrado',
                'user': result[0],
                'token': generar_token()
            }, 201
        
        return {'success': False, 'message': 'Error al registrar'}, 500
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE LOGIN ==========
def handler_login(request):
    """POST /api/login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        telefono_id = data.get('telefono_id')
        
        if not email or not password:
            return {'success': False, 'message': 'Email y contraseña requeridos'}, 400
        
        db = get_db()
        result = db.query('usuarios', params={'email': f'eq.{email}'})
        
        if not result or len(result) == 0:
            return {'success': False, 'message': 'Credenciales inválidas'}, 401
        
        user = result[0]
        
        if user['password_hash'] != hash_password(password):
            return {'success': False, 'message': 'Credenciales inválidas'}, 401
        
        # Actualizar teléfono si es necesario
        if telefono_id and user['telefono_id'] != telefono_id:
            db.query('usuarios', method='PATCH', 
                    data={'telefono_id': telefono_id},
                    params={'id': f'eq.{user["id"]}'})
        
        return {
            'success': True,
            'message': 'Login exitoso',
            'user': {
                'id': user['id'],
                'matricula': user['matricula'],
                'nombre': user['nombre'],
                'email': user['email'],
                'rol': user['rol'],
                'telefono_id': user['telefono_id']
            },
            'token': generar_token()
        }, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE VERIFICACIÓN ==========
def handler_verify(request):
    """POST /api/verify-session"""
    try:
        data = request.get_json()
        telefono_id = data.get('telefono_id')
        
        if not telefono_id:
            return {'valid': False}
        
        db = get_db()
        result = db.query('usuarios', params={'telefono_id': f'eq.{telefono_id}'})
        
        if result and len(result) > 0:
            user = result[0]
            return {
                'valid': True,
                'user': {
                    'id': user['id'],
                    'matricula': user['matricula'],
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'rol': user['rol']
                }
            }
        
        return {'valid': False}
        
    except Exception:
        return {'valid': False}

# ========== API DE ESTADÍSTICAS ==========
def handler_estadisticas(request, user_id):
    """GET /api/alumno/<user_id>/estadisticas"""
    try:
        db = get_db()
        
        alumno = db.query('usuarios', params={'id': f'eq.{user_id}', 'rol': 'eq.alumno'})
        if not alumno or len(alumno) == 0:
            return {'success': False, 'message': 'Alumno no encontrado'}, 404
        
        asistencias = db.query('asistencias', params={
            'alumno_id': f'eq.{user_id}',
            'select': 'id,valida,justificada'
        })
        
        asistencias_count = 0
        justificadas_count = 0
        
        if asistencias:
            for a in asistencias:
                if a.get('valida') or a.get('justificada'):
                    asistencias_count += 1
                if a.get('justificada'):
                    justificadas_count += 1
        
        clases = db.query('clases', params={'select': 'count'})
        total_clases = clases[0]['count'] if clases and len(clases) > 0 else 20
        
        faltas_count = total_clases - asistencias_count
        porcentaje = round((asistencias_count / total_clases) * 100) if total_clases > 0 else 0
        
        return {
            'success': True,
            'estadisticas': {
                'asistencias': asistencias_count,
                'faltas': faltas_count,
                'justificadas': justificadas_count,
                'total_clases': total_clases,
                'porcentaje': porcentaje
            }
        }, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE ACTIVIDAD ==========
def handler_actividad(request, user_id):
    """GET /api/alumno/<user_id>/actividad"""
    try:
        db = get_db()
        
        asistencias = db.query('asistencias', params={
            'alumno_id': f'eq.{user_id}',
            'order': 'fecha_escaneo.desc',
            'limit': 10
        })
        
        actividades = []
        if asistencias:
            for a in asistencias:
                fecha = datetime.fromisoformat(a['fecha_escaneo'].replace('Z', '+00:00'))
                fecha_str = fecha.strftime('%d %b, %H:%M')
                
                tipo = 'asistencia'
                if a.get('justificada'):
                    tipo = 'justificante'
                elif not a.get('valida'):
                    tipo = 'invalida'
                
                actividades.append({
                    'tipo': tipo,
                    'fecha': fecha_str
                })
        
        return {'success': True, 'actividades': actividades}, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE CLASES ==========
def handler_clase_activa(request):
    """GET /api/clase/activa"""
    try:
        db = get_db()
        clase = db.query('clases', params={
            'activa': 'eq.true',
            'order': 'created_at.desc',
            'limit': 1
        })
        
        if clase and len(clase) > 0:
            return {'activa': True, 'clase': clase[0]}, 200
        
        return {'activa': False}, 200
    except Exception as e:
        return {'activa': False, 'error': str(e)}, 500

def handler_iniciar_clase(request):
    """POST /api/clase/iniciar"""
    try:
        data = request.get_json()
        profesor_id = data.get('profesor_id')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not profesor_id:
            return {'success': False, 'message': 'ID de profesor requerido'}, 400
        
        db = get_db()
        
        activa = db.query('clases', params={'activa': 'eq.true'})
        if activa and len(activa) > 0:
            return {'success': False, 'message': 'Ya hay una clase activa'}, 400
        
        nueva_clase = {
            'profesor_id': profesor_id,
            'fecha': date.today().isoformat(),
            'hora_inicio': datetime.now().time().isoformat(),
            'activa': True,
            'latitud_referencia': latitud,
            'longitud_referencia': longitud
        }
        
        result = db.query('clases', method='POST', data=nueva_clase)
        
        if result and len(result) > 0:
            clase = result[0]
            return {
                'success': True,
                'clase': {
                    'id': clase['id'],
                    'fecha': clase['fecha'],
                    'hora_inicio': clase['hora_inicio'],
                    'latitud_referencia': clase['latitud_referencia'],
                    'longitud_referencia': clase['longitud_referencia']
                }
            }, 200
        
        return {'success': False, 'message': 'Error al crear clase'}, 500
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

def handler_asistencias_clase(request, clase_id):
    """GET /api/clase/<clase_id>/asistencias"""
    try:
        db = get_db()
        
        asistencias = db.query('asistencias', params={
            'clase_id': f'eq.{clase_id}',
            'order': 'fecha_escaneo.desc'
        })
        
        resultado = []
        if asistencias:
            for a in asistencias:
                alumno = db.query('usuarios', params={'id': f'eq.{a["alumno_id"]}'})
                if alumno and len(alumno) > 0:
                    resultado.append({
                        'id': a['id'],
                        'alumno_id': a['alumno_id'],
                        'matricula': alumno[0]['matricula'],
                        'nombre': alumno[0]['nombre'],
                        'fecha_escaneo': a['fecha_escaneo'],
                        'latitud_escaneo': a['latitud_escaneo'],
                        'longitud_escaneo': a['longitud_escaneo'],
                        'distancia_metros': a['distancia_metros'],
                        'valida': a['valida'],
                        'justificada': a['justificada']
                    })
        
        return {'success': True, 'asistencias': resultado}, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

def handler_terminar_clase(request):
    """POST /api/clase/terminar"""
    try:
        data = request.get_json()
        clase_id = data.get('clase_id')
        
        if not clase_id:
            return {'success': False, 'message': 'ID de clase requerido'}, 400
        
        db = get_db()
        
        db.query('clases', method='PATCH',
                data={'activa': False, 'hora_fin': datetime.now().time().isoformat()},
                params={'id': f'eq.{clase_id}'})
        
        return {'success': True, 'message': 'Clase terminada'}, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE REGISTRAR ASISTENCIA ==========
def handler_registrar_asistencia(request):
    """POST /api/registrar-asistencia"""
    try:
        data = request.get_json()
        qr_data = data.get('qr_data')
        telefono_id = data.get('telefono_id')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not qr_data or not telefono_id:
            return {'success': False, 'message': 'Datos incompletos'}, 400
        
        db = get_db()
        
        alumno = db.query('usuarios', params={
            'telefono_id': f'eq.{telefono_id}',
            'rol': 'eq.alumno'
        })
        
        if not alumno or len(alumno) == 0:
            return {'success': False, 'message': 'Alumno no encontrado'}, 404
        
        alumno_id = alumno[0]['id']
        
        try:
            qr_info = json.loads(qr_data)
            clase_id = qr_info.get('clase_id')
        except:
            clase_id = qr_data
        
        clase = db.query('clases', params={
            'id': f'eq.{clase_id}',
            'activa': 'eq.true'
        })
        
        if not clase or len(clase) == 0:
            return {'success': False, 'message': 'Clase no válida o inactiva'}, 400
        
        clase_info = clase[0]
        
        existente = db.query('asistencias', params={
            'clase_id': f'eq.{clase_id}',
            'alumno_id': f'eq.{alumno_id}'
        })
        
        if existente and len(existente) > 0:
            return {'success': False, 'message': 'Ya registraste asistencia'}, 400
        
        distancia = None
        valida = True
        
        if latitud and longitud and clase_info.get('latitud_referencia'):
            distancia = calcular_distancia(
                latitud, longitud,
                clase_info['latitud_referencia'],
                clase_info['longitud_referencia']
            )
            valida = distancia <= 7
        
        nueva_asistencia = {
            'clase_id': clase_id,
            'alumno_id': alumno_id,
            'fecha_escaneo': datetime.now().isoformat(),
            'latitud_escaneo': latitud,
            'longitud_escaneo': longitud,
            'distancia_metros': distancia,
            'valida': valida,
            'justificada': False
        }
        
        result = db.query('asistencias', method='POST', data=nueva_asistencia)
        
        if result and len(result) > 0:
            return {
                'success': True,
                'message': 'Asistencia registrada',
                'valida': valida,
                'distancia': distancia
            }, 201
        
        return {'success': False, 'message': 'Error al registrar'}, 500
            
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE DASHBOARD PROFESOR ==========
def handler_dashboard_profesor(request, user_id):
    """GET /api/profesor/<user_id>/dashboard"""
    try:
        db = get_db()
        
        profesor = db.query('usuarios', params={
            'id': f'eq.{user_id}',
            'rol': 'eq.profesor'
        })
        
        if not profesor or len(profesor) == 0:
            return {'success': False, 'message': 'Profesor no encontrado'}, 404
        
        alumnos = db.query('usuarios', params={'rol': 'eq.alumno'})
        
        clases = db.query('clases', params={'select': 'count'})
        total_clases = clases[0]['count'] if clases and len(clases) > 0 else 20
        
        verde = amarillo = naranja = rojo = 0
        alumnos_detalle = []
        
        if alumnos:
            for alumno in alumnos:
                asistencias = db.query('asistencias', params={
                    'alumno_id': f'eq.{alumno["id"]}'
                })
                
                asistencias_count = 0
                if asistencias:
                    for a in asistencias:
                        if a.get('valida') or a.get('justificada'):
                            asistencias_count += 1
                
                porcentaje = round((asistencias_count / total_clases) * 100) if total_clases > 0 else 0
                
                if porcentaje >= 80:
                    verde += 1
                elif porcentaje >= 50:
                    amarillo += 1
                elif porcentaje >= 30:
                    naranja += 1
                else:
                    rojo += 1
                
                alumnos_detalle.append({
                    'id': alumno['id'],
                    'nombre': alumno['nombre'],
                    'matricula': alumno['matricula'],
                    'asistencias': asistencias_count,
                    'porcentaje': porcentaje
                })
        
        return {
            'success': True,
            'dashboard': {
                'total_alumnos': len(alumnos) if alumnos else 0,
                'semaforo': {
                    'verde': verde,
                    'amarillo': amarillo,
                    'naranja': naranja,
                    'rojo': rojo
                },
                'alumnos': alumnos_detalle
            }
        }, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE JUSTIFICAR ==========
def handler_justificar(request):
    """POST /api/asistencia/justificar"""
    try:
        data = request.get_json()
        asistencia_id = data.get('asistencia_id')
        motivo = data.get('motivo')
        comentario = data.get('comentario')
        
        if not asistencia_id or not motivo:
            return {'success': False, 'message': 'Datos incompletos'}, 400
        
        db = get_db()
        
        db.query('asistencias', method='PATCH',
                data={'justificada': True, 'motivo_justificacion': motivo, 'comentario': comentario},
                params={'id': f'eq.{asistencia_id}'})
        
        return {'success': True, 'message': 'Falta justificada'}, 200
        
    except Exception as e:
        return {'success': False, 'message': str(e)}, 500

# ========== API DE CHECK EMAIL/MATRICULA ==========
def handler_check_email(request):
    """POST /api/check-email"""
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return {'exists': False}
        
        db = get_db()
        result = db.query('usuarios', params={'email': f'eq.{email}'})
        return {'exists': len(result) > 0 if result else False}
    except Exception:
        return {'exists': False}

def handler_check_matricula(request):
    """POST /api/check-matricula"""
    try:
        data = request.get_json()
        matricula = data.get('matricula')
        if not matricula:
            return {'exists': False}
        
        db = get_db()
        result = db.query('usuarios', params={'matricula': f'eq.{matricula}'})
        return {'exists': len(result) > 0 if result else False}
    except Exception:
        return {'exists': False}