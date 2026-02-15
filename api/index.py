# api/index.py - API PURA para Vercel (Serverless)
import os
import hashlib
import secrets
import re
import json
import qrcode
import io
import base64
from flask import Flask, jsonify, request
from dotenv import load_dotenv
from datetime import datetime, date
from geopy.distance import geodesic


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-vercel-2026')

# ========== IMPORTAR DATABASE ==========
# Asegúrate de tener database.py con get_db() funcional
try:
    from database import get_db
except ImportError:
    from .database import get_db

# ========== FUNCIONES DE UTILERÍA ==========

def hash_password(password):
    """Hashea la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generar_token():
    """Genera un token único para sesiones"""
    return secrets.token_urlsafe(32)

def validar_matricula(matricula):
    """Valida formato de matrícula"""
    patron = r'^\d{4}-[A-Z0-9]{4,8}$'
    return bool(re.match(patron, matricula))

def validar_email(email):
    """Valida formato de email"""
    patron = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(patron, email))

# ========== RUTAS API PÚBLICAS ==========
@app.route('/api/test-db')
def test_db():
    """Prueba la conexión a Supabase"""
    try:
        db = get_db()
        if db:
            return jsonify({
                'status': 'success',
                'message': '✅ Conexión a Supabase OK',
                'timestamp': datetime.now().isoformat()
            })
        return jsonify({
            'status': 'error',
            'message': '❌ No hay conexión a Supabase'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'❌ Error: {str(e)}'
        }), 500

@app.route('/api/debug')
def debug():
    """Información de depuración"""
    return jsonify({
        'app': 'AsistenciaApp',
        'version': '2.0',
        'status': 'running',
        'database': 'connected' if get_db() else 'disconnected',
        'timestamp': datetime.now().isoformat(),
        'platform': 'vercel-serverless'
    })

# ========== API DE AUTENTICACIÓN ==========

@app.route('/api/register', methods=['POST'])
def api_register():
    """Registra un nuevo usuario"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        matricula = data.get('matricula', '').strip().upper()
        rol = data.get('rol', 'alumno').lower()
        telefono_id = data.get('telefono_id', '').strip()
        
        # Validaciones
        if not all([nombre, email, password, telefono_id]):
            return jsonify({'success': False, 'message': 'Faltan campos requeridos'}), 400
        
        if rol == 'alumno' and not matricula:
            return jsonify({'success': False, 'message': 'Matrícula requerida para alumnos'}), 400
        
        if rol == 'alumno' and not validar_matricula(matricula):
            return jsonify({'success': False, 'message': 'Formato de matrícula inválido (Ej: 2025-0145)'}), 400
        
        if not validar_email(email):
            return jsonify({'success': False, 'message': 'Email inválido'}), 400
        
        db = get_db()
        
        # Verificar email único
        existing = db.query('usuarios', params={'email': f'eq.{email}'})
        if existing and len(existing) > 0:
            return jsonify({'success': False, 'message': 'El email ya está registrado'}), 400
        
        # Verificar matrícula única (si es alumno)
        if rol == 'alumno':
            existing_mat = db.query('usuarios', params={'matricula': f'eq.{matricula}'})
            if existing_mat and len(existing_mat) > 0:
                return jsonify({'success': False, 'message': 'La matrícula ya está registrada'}), 400
        
        # Crear usuario
        nuevo_usuario = {
            'nombre': nombre,
            'email': email,
            'password_hash': hash_password(password),
            'matricula': matricula if rol == 'alumno' else None,
            'rol': rol,
            'activo': True
        }
        
        result = db.query('usuarios', method='POST', data=nuevo_usuario)
        
        if result and len(result) > 0:
            usuario = result[0]
            
            # Registrar dispositivo
            nuevo_dispositivo = {
                'telefono_id': telefono_id,
                'usuario_id': usuario['id'],
                'verificado': True
            }
            
            db.query('dispositivos', method='POST', data=nuevo_dispositivo)
            
            return jsonify({
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'usuario': {
                    'id': usuario['id'],
                    'nombre': usuario['nombre'],
                    'email': usuario['email'],
                    'matricula': usuario['matricula'],
                    'rol': usuario['rol']
                },
                'telefono_id': telefono_id
            })
        
        return jsonify({'success': False, 'message': 'Error al crear usuario'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Inicia sesión"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        telefono_id = data.get('telefono_id', '').strip()
        
        if not all([email, password, telefono_id]):
            return jsonify({'success': False, 'message': 'Faltan credenciales'}), 400
        
        db = get_db()
        
        # Buscar usuario
        usuarios = db.query('usuarios', params={
            'email': f'eq.{email}',
            'password_hash': f'eq.{hash_password(password)}'
        })
        
        if not usuarios or len(usuarios) == 0:
            return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401
        
        usuario = usuarios[0]
        
        if not usuario.get('activo'):
            return jsonify({'success': False, 'message': 'Usuario inactivo'}), 403
        
        # Verificar/registrar dispositivo
        dispositivo = db.query('dispositivos', params={
            'telefono_id': f'eq.{telefono_id}',
            'usuario_id': f'eq.{usuario["id"]}'
        })
        
        if not dispositivo or len(dispositivo) == 0:
            # Registrar nuevo dispositivo
            nuevo_dispositivo = {
                'telefono_id': telefono_id,
                'usuario_id': usuario['id'],
                'verificado': True
            }
            db.query('dispositivos', method='POST', data=nuevo_dispositivo)
        
        return jsonify({
            'success': True,
            'message': 'Login exitoso',
            'usuario': {
                'id': usuario['id'],
                'nombre': usuario['nombre'],
                'email': usuario['email'],
                'matricula': usuario.get('matricula'),
                'rol': usuario['rol']
            },
            'telefono_id': telefono_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error del servidor: {str(e)}'}), 500

@app.route('/api/verificar-dispositivo', methods=['POST'])
def verificar_dispositivo():
    """Verifica si un dispositivo está registrado"""
    try:
        data = request.json
        telefono_id = data.get('telefono_id', '').strip()
        
        if not telefono_id:
            return jsonify({'verificado': False, 'message': 'ID de dispositivo requerido'}), 400
        
        db = get_db()
        
        dispositivo = db.query('dispositivos', params={
            'telefono_id': f'eq.{telefono_id}',
            'verificado': 'eq.true'
        })
        
        if dispositivo and len(dispositivo) > 0:
            # Obtener datos del usuario
            usuario = db.query('usuarios', params={'id': f'eq.{dispositivo[0]["usuario_id"]}'})
            
            if usuario and len(usuario) > 0:
                return jsonify({
                    'verificado': True,
                    'usuario': {
                        'id': usuario[0]['id'],
                        'nombre': usuario[0]['nombre'],
                        'email': usuario[0]['email'],
                        'matricula': usuario[0].get('matricula'),
                        'rol': usuario[0]['rol']
                    }
                })
        
        return jsonify({'verificado': False, 'message': 'Dispositivo no verificado'})
        
    except Exception as e:
        return jsonify({'verificado': False, 'message': str(e)}), 500

# ========== API DE ASISTENCIAS ==========

@app.route('/api/registrar-asistencia', methods=['POST'])
def registrar_asistencia():
    """Registra asistencia de alumno mediante QR"""
    try:
        data = request.json
        qr_data_str = data.get('qr_data')
        telefono_id = data.get('telefono_id')
        latitud_escaneo = data.get('latitud')
        longitud_escaneo = data.get('longitud')
        
        if not all([qr_data_str, telefono_id]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
        
        # Parsear QR
        try:
            qr_data = json.loads(qr_data_str)
        except:
            return jsonify({'success': False, 'message': 'QR inválido'}), 400
        
        clase_id = qr_data.get('clase_id')
        latitud_clase = qr_data.get('latitud')
        longitud_clase = qr_data.get('longitud')
        
        if not clase_id:
            return jsonify({'success': False, 'message': 'QR no válido'}), 400
        
        db = get_db()
        
        # Verificar dispositivo
        dispositivo = db.query('dispositivos', params={
            'telefono_id': f'eq.{telefono_id}',
            'verificado': 'eq.true'
        })
        
        if not dispositivo or len(dispositivo) == 0:
            return jsonify({'success': False, 'message': 'Dispositivo no autorizado'}), 403
        
        alumno_id = dispositivo[0]['usuario_id']
        
        # Verificar clase activa
        clase = db.query('clases', params={
            'id': f'eq.{clase_id}',
            'activa': 'eq.true'
        })
        
        if not clase or len(clase) == 0:
            return jsonify({'success': False, 'message': 'Clase no activa'}), 400
        
        # Calcular distancia
        distancia_metros = None
        if latitud_escaneo and longitud_escaneo and latitud_clase and longitud_clase:
            distancia_metros = geodesic(
                (latitud_clase, longitud_clase),
                (latitud_escaneo, longitud_escaneo)
            ).meters
        
        valida = distancia_metros is None or distancia_metros <= 10
        
        # Registrar asistencia
        nueva_asistencia = {
            'clase_id': clase_id,
            'alumno_id': alumno_id,
            'fecha_escaneo': datetime.now().isoformat(),
            'latitud_escaneo': latitud_escaneo,
            'longitud_escaneo': longitud_escaneo,
            'distancia_metros': distancia_metros,
            'valida': valida
        }
        
        result = db.query('asistencias', method='POST', data=nueva_asistencia)
        
        if result and len(result) > 0:
            mensaje = '✅ Asistencia registrada' if valida else '⚠️ Asistencia registrada (fuera de rango)'
            return jsonify({
                'success': True,
                'message': mensaje,
                'asistencia': {
                    'id': result[0]['id'],
                    'valida': valida,
                    'distancia': distancia_metros
                }
            })
        
        return jsonify({'success': False, 'message': 'Error al registrar'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== API PARA ALUMNO ==========

@app.route('/api/alumno/<int:user_id>/estadisticas', methods=['GET'])
def get_estadisticas_alumno(user_id):
    """Obtiene estadísticas del alumno"""
    try:
        db = get_db()
        
        # Verificar alumno
        alumno = db.query('usuarios', params={
            'id': f'eq.{user_id}',
            'rol': 'eq.alumno'
        })
        
        if not alumno or len(alumno) == 0:
            return jsonify({'success': False, 'message': 'Alumno no encontrado'}), 404
        
        # Obtener asistencias
        asistencias = db.query('asistencias', params={'alumno_id': f'eq.{user_id}'})
        
        asistencias_count = 0
        justificadas_count = 0
        
        if asistencias:
            for a in asistencias:
                if a.get('valida') or a.get('justificada'):
                    asistencias_count += 1
                    if a.get('justificada'):
                        justificadas_count += 1
        
        # Total de clases (puedes ajustar esto según tu lógica)
        total_clases = db.query('clases', params={'select': 'count'})
        total = total_clases[0]['count'] if total_clases and len(total_clases) > 0 else 20
        
        faltas = total - asistencias_count
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'asistencias': asistencias_count,
                'faltas': faltas,
                'justificadas': justificadas_count,
                'total_clases': total
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/alumno/<int:user_id>/actividad', methods=['GET'])
def get_actividad_alumno(user_id):
    """Obtiene actividad reciente del alumno"""
    try:
        db = get_db()
        
        asistencias = db.query('asistencias', params={
            'alumno_id': f'eq.{user_id}',
            'order': 'fecha_escaneo.desc',
            'limit': '10'
        })
        
        actividades = []
        if asistencias:
            for a in asistencias:
                fecha_obj = datetime.fromisoformat(a['fecha_escaneo'])
                actividades.append({
                    'tipo': 'justificada' if a.get('justificada') else 'asistencia',
                    'fecha': fecha_obj.strftime('%d/%m/%Y %H:%M'),
                    'valida': a.get('valida', False)
                })
        
        return jsonify({
            'success': True,
            'actividades': actividades
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== API PARA PROFESOR ==========

@app.route('/api/profesor/<int:user_id>/dashboard', methods=['GET'])
def get_dashboard_profesor(user_id):
    """Obtiene datos para dashboard del profesor"""
    try:
        db = get_db()
        
        # Verificar profesor
        profesor = db.query('usuarios', params={
            'id': f'eq.{user_id}',
            'rol': 'eq.profesor'
        })
        
        if not profesor or len(profesor) == 0:
            return jsonify({'success': False, 'message': 'Profesor no encontrado'}), 404
        
        # Obtener alumnos
        alumnos = db.query('usuarios', params={'rol': 'eq.alumno'})
        
        # Total de clases
        clases = db.query('clases', params={'select': 'count'})
        total_clases = clases[0]['count'] if clases and len(clases) > 0 else 20
        
        verde = amarillo = naranja = rojo = 0
        alumnos_detalle = []
        
        if alumnos:
            for alumno in alumnos:
                asistencias = db.query('asistencias', params={'alumno_id': f'eq.{alumno["id"]}'})
                
                asistencias_count = sum(1 for a in asistencias if a.get('valida') or a.get('justificada')) if asistencias else 0
                porcentaje = round((asistencias_count / total_clases) * 100) if total_clases > 0 else 0
                
                if porcentaje >= 80: verde += 1
                elif porcentaje >= 50: amarillo += 1
                elif porcentaje >= 30: naranja += 1
                else: rojo += 1
                
                alumnos_detalle.append({
                    'id': alumno['id'],
                    'nombre': alumno['nombre'],
                    'matricula': alumno['matricula'],
                    'asistencias': asistencias_count,
                    'porcentaje': porcentaje
                })
        
        return jsonify({
            'success': True,
            'dashboard': {
                'total_alumnos': len(alumnos) if alumnos else 0,
                'total_clases': total_clases,
                'semaforo': {
                    'verde': verde,
                    'amarillo': amarillo,
                    'naranja': naranja,
                    'rojo': rojo
                },
                'alumnos': alumnos_detalle
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clase/activa', methods=['GET'])
def get_clase_activa():
    """Verifica si hay clase activa"""
    try:
        db = get_db()
        clase = db.query('clases', params={'activa': 'eq.true'})
        
        if clase and len(clase) > 0:
            return jsonify({
                'activa': True,
                'clase': {
                    'id': clase[0]['id'],
                    'fecha': clase[0]['fecha'],
                    'hora_inicio': clase[0]['hora_inicio'],
                    'profesor_id': clase[0]['profesor_id'],
                    'latitud_referencia': clase[0].get('latitud_referencia'),
                    'longitud_referencia': clase[0].get('longitud_referencia')
                }
            })
        
        return jsonify({'activa': False})
        
    except Exception as e:
        return jsonify({'activa': False, 'error': str(e)}), 500

@app.route('/api/clase/iniciar', methods=['POST'])
def iniciar_clase():
    """Inicia una nueva clase"""
    try:
        data = request.json
        profesor_id = data.get('profesor_id')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not profesor_id:
            return jsonify({'success': False, 'message': 'ID de profesor requerido'}), 400
        
        db = get_db()
        
        # Verificar que no haya clase activa
        activa = db.query('clases', params={'activa': 'eq.true'})
        if activa and len(activa) > 0:
            return jsonify({'success': False, 'message': 'Ya hay una clase activa'}), 400
        
        # Crear clase
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
            
            # Generar QR
            qr_data = {
                'clase_id': clase['id'],
                'profesor_id': profesor_id,
                'latitud': latitud,
                'longitud': longitud,
                'timestamp': datetime.now().isoformat()
            }
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            return jsonify({
                'success': True,
                'clase': {
                    'id': clase['id'],
                    'fecha': clase['fecha'],
                    'hora_inicio': clase['hora_inicio'],
                    'profesor_id': clase['profesor_id'],
                    'latitud_referencia': latitud,
                    'longitud_referencia': longitud,
                    'qr_base64': img_base64
                }
            })
        
        return jsonify({'success': False, 'message': 'Error al crear clase'}), 500
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clase/terminar', methods=['POST'])
def terminar_clase():
    """Termina una clase activa"""
    try:
        data = request.json
        clase_id = data.get('clase_id')
        
        if not clase_id:
            return jsonify({'success': False, 'message': 'ID de clase requerido'}), 400
        
        db = get_db()
        
        result = db.query('clases', method='PATCH',
                         data={'activa': False, 'hora_fin': datetime.now().time().isoformat()},
                         params={'id': f'eq.{clase_id}'})
        
        return jsonify({'success': True, 'message': 'Clase terminada'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clase/<int:clase_id>/asistencias', methods=['GET'])
def get_asistencias_clase(clase_id):
    """Obtiene asistencias de una clase"""
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
                        'latitud_escaneo': a.get('latitud_escaneo'),
                        'longitud_escaneo': a.get('longitud_escaneo'),
                        'distancia_metros': a.get('distancia_metros'),
                        'valida': a.get('valida', False),
                        'justificada': a.get('justificada', False)
                    })
        
        return jsonify({
            'success': True,
            'asistencias': resultado
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/asistencia/justificar', methods=['POST'])
def justificar_asistencia():
    """Justifica una falta"""
    try:
        data = request.json
        asistencia_id = data.get('asistencia_id')
        motivo = data.get('motivo')
        comentario = data.get('comentario', '')
        
        if not all([asistencia_id, motivo]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
        
        db = get_db()
        
        result = db.query('asistencias', method='PATCH',
                         data={
                             'justificada': True,
                             'motivo_justificacion': motivo,
                             'comentario_justificacion': comentario
                         },
                         params={'id': f'eq.{asistencia_id}'})
        
        return jsonify({'success': True, 'message': 'Falta justificada'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== HEALTH CHECK ==========

@app.route('/health')
def health():
    """Health check para Vercel"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': '404 Not Found',
        'message': 'Endpoint no existe',
        'available_endpoints': [
            '/api/login',
            '/api/register',
            '/api/clase/activa',
            '/api/test-db'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': '500 Internal Server Error',
        'message': 'Error del servidor'
    }), 500

# ========== CORS (importante para Vercel) ==========
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,PATCH,OPTIONS')
    return response

