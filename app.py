# app.py - Versión COMPLETA con DATOS REALES
import os
import hashlib
import secrets
import re
import socket
import json
import qrcode
import io
import base64
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from dotenv import load_dotenv
from database import init_db, get_db
from datetime import datetime, date, time
from geopy.distance import geodesic

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-123')

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

def get_local_ip():
    """Obtiene la IP local de la máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Inicializar conexión a BD
if init_db():
    local_ip = get_local_ip()
    print("="*50)
    print("🚀 App lista para arrancar con DATOS REALES")
    print(f"📱 Local: http://localhost:5000")
    print(f"📱 Red: http://{local_ip}:5000")
    print(f"📱 Network info: http://{local_ip}:5000/network-info")
    print("="*50)
else:
    print("💥 Error fatal: No hay conexión a la base de datos")
    exit(1)

# ========== RUTAS PÚBLICAS ==========

@app.route('/')
def index():
    """Página principal - Login/Home"""
    return render_template('index.html')

@app.route('/register')
def register():
    """Página de registro"""
    return render_template('register.html')

# ========== RUTAS DE PROFESOR ==========

@app.route('/dashboard_profesor')
def dashboard_profesor():
    """Dashboard del profesor"""
    return render_template('dashboard_profesor.html')

@app.route('/asistencias')
def asistencias():
    """Página de asistencias en vivo"""
    return render_template('asistencias.html')

@app.route('/historial')
def historial():
    """Página de historial"""
    return render_template('historial.html')

@app.route('/dashboard_alumno')
def dashboard_alumno():
    """Dashboard del alumno"""
    return render_template('dashboard_alumno.html')

# ========== RUTAS API ==========

@app.route('/test-db')
def test_db():
    """Prueba la conexión a Supabase"""
    db = get_db()
    if db:
        return jsonify({
            "status": "success",
            "message": "✅ Conexión a Supabase funcionando",
            "timestamp": datetime.now().isoformat()
        })
    return jsonify({
        "status": "error",
        "message": "❌ No hay conexión a Supabase"
    })

@app.route('/debug')
def debug():
    """Información de depuración"""
    return jsonify({
        "app": "Asistencia App",
        "status": "running",
        "database": "connected" if get_db() else "disconnected",
        "routes": [str(rule) for rule in app.url_map.iter_rules()],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/network-info')
def network_info():
    """Muestra información de red para conectar otros dispositivos"""
    local_ip = get_local_ip()
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Conectar a la App</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 20px;
                padding: 40px;
                max-width: 500px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.5s ease;
            }}
            @keyframes slideUp {{
                from {{ opacity: 0; transform: translateY(30px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            h1 {{
                color: #4361ee;
                margin-bottom: 20px;
                font-size: 2rem;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .ip-box {{
                background: linear-gradient(135deg, #4361ee, #3a56d4);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin: 30px 0;
                font-size: 2rem;
                font-weight: bold;
                font-family: monospace;
                box-shadow: 0 10px 30px rgba(67, 97, 238, 0.3);
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.02); }}
                100% {{ transform: scale(1); }}
            }}
            .qr-container {{
                text-align: center;
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 15px;
            }}
            .qr-code {{
                width: 200px;
                height: 200px;
                margin: 0 auto;
                background: white;
                padding: 10px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .instructions {{
                text-align: left;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
            }}
            .instructions ol {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .instructions li {{
                margin: 10px 0;
                color: #2b2d42;
            }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #4361ee, #3a56d4);
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 10px;
                font-weight: 600;
                transition: transform 0.3s, box-shadow 0.3s;
                border: none;
                cursor: pointer;
                font-size: 1rem;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(67, 97, 238, 0.3);
            }}
            .btn-secondary {{
                background: linear-gradient(135deg, #6c757d, #5a6268);
            }}
            .port-info {{
                background: #e9ecef;
                padding: 10px;
                border-radius: 8px;
                font-family: monospace;
                margin: 10px 0;
            }}
            .copy-btn {{
                background: none;
                border: 2px solid #4361ee;
                color: #4361ee;
                padding: 8px 15px;
                border-radius: 5px;
                cursor: pointer;
                margin-left: 10px;
                transition: all 0.3s;
            }}
            .copy-btn:hover {{
                background: #4361ee;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1><i class="fas fa-wifi"></i> Conectar a la App</h1>
            <div class="ip-box">{local_ip}:5000</div>
            <div style="text-align: center; margin-bottom: 20px;">
                <button class="copy-btn" onclick="copyToClipboard()">
                    <i class="fas fa-copy"></i> Copiar Dirección
                </button>
            </div>
            <div class="qr-container">
                <div class="qr-code" id="qrCode"></div>
                <p style="margin-top: 15px; color: #6c757d;">
                    <i class="fas fa-camera"></i> Escanea para conectar desde tu celular
                </p>
            </div>
            <div class="instructions">
                <h3><i class="fas fa-info-circle"></i> Instrucciones:</h3>
                <ol>
                    <li><strong>Asegúrate de estar en la misma red WiFi</strong></li>
                    <li>En tu celular, abre el navegador</li>
                    <li>Escribe: <strong>{local_ip}:5000</strong></li>
                    <li>O escanea el código QR</li>
                </ol>
            </div>
            <div class="port-info"><i class="fas fa-plug"></i> Puerto: <strong>5000</strong></div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <a href="/" class="btn" style="flex: 1;">🏠 Ir a la App</a>
                <button class="btn btn-secondary" style="flex: 1;" onclick="window.print()">🖨️ Imprimir</button>
            </div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                new QRCode(document.getElementById('qrCode'), {{
                    text: 'http://{local_ip}:5000',
                    width: 180,
                    height: 180,
                    colorDark: '#4361ee',
                    colorLight: '#ffffff',
                    correctLevel: QRCode.CorrectLevel.H
                }});
            }});
            function copyToClipboard() {{
                navigator.clipboard.writeText('{local_ip}:5000').then(
                    () => alert('✅ Dirección copiada'),
                    () => alert('❌ No se pudo copiar')
                );
            }}
        </script>
    </body>
    </html>
    '''

# ========== API DE REGISTRO ==========

@app.route('/api/register', methods=['POST'])
def api_register():
    """Registra un nuevo usuario en Supabase"""
    try:
        data = request.json
        print("📝 Registrando:", data.get('email'))
        
        required_fields = ['matricula', 'nombre', 'email', 'password', 'rol', 'telefono_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Falta campo: {field}'}), 400
        
        if not validar_matricula(data['matricula']):
            return jsonify({'success': False, 'message': 'Matrícula inválida. Formato: 2024-1234'}), 400
        
        if not validar_email(data['email']):
            return jsonify({'success': False, 'message': 'Email inválido'}), 400
        
        if len(data['password']) < 8:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 8 caracteres'}), 400
        
        db = get_db()
        if not db:
            return jsonify({'success': False, 'message': 'Error de conexión'}), 500
        
        # Verificar duplicados
        for field in ['email', 'matricula', 'telefono_id']:
            existing = db.query('usuarios', params={field: f'eq.{data[field]}'})
            if existing and len(existing) > 0:
                return jsonify({'success': False, 'message': f'{field} ya está registrado'}), 400
        
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
            return jsonify({
                'success': True,
                'message': 'Usuario registrado',
                'user': result[0],
                'token': generar_token()
            }), 201
        
        return jsonify({'success': False, 'message': 'Error al registrar'}), 500
            
    except Exception as e:
        print(f"Error en registro: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/check-email', methods=['POST'])
def check_email():
    """Verifica si email existe"""
    try:
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({'exists': False})
        
        db = get_db()
        result = db.query('usuarios', params={'email': f'eq.{email}'})
        return jsonify({'exists': len(result) > 0 if result else False})
    except Exception as e:
        return jsonify({'exists': False, 'error': str(e)})

@app.route('/api/check-matricula', methods=['POST'])
def check_matricula():
    """Verifica si matrícula existe"""
    try:
        data = request.json
        matricula = data.get('matricula')
        if not matricula:
            return jsonify({'exists': False})
        
        db = get_db()
        result = db.query('usuarios', params={'matricula': f'eq.{matricula}'})
        return jsonify({'exists': len(result) > 0 if result else False})
    except Exception as e:
        return jsonify({'exists': False, 'error': str(e)})

# ========== API DE LOGIN ==========

@app.route('/api/login', methods=['POST'])
def api_login():
    """Inicia sesión con email y contraseña"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        telefono_id = data.get('telefono_id')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email y contraseña requeridos'}), 400
        
        db = get_db()
        result = db.query('usuarios', params={'email': f'eq.{email}'})
        
        if not result or len(result) == 0:
            return jsonify({'success': False, 'message': 'Credenciales inválidas'}), 401
        
        user = result[0]
        
        if user['password_hash'] != hash_password(password):
            return jsonify({'success': False, 'message': 'Credenciales inválidas'}), 401
        
        # Actualizar teléfono si es necesario
        if telefono_id and user['telefono_id'] != telefono_id:
            db.query('usuarios', method='PATCH', 
                    data={'telefono_id': telefono_id},
                    params={'id': f'eq.{user["id"]}'})
        
        return jsonify({
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
        })
        
    except Exception as e:
        print(f"Error en login: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== API DE VERIFICACIÓN DE SESIÓN ==========

@app.route('/api/verify-session', methods=['POST'])
def verify_session():
    """Verifica sesión por teléfono_id"""
    try:
        data = request.json
        telefono_id = data.get('telefono_id')
        
        if not telefono_id:
            return jsonify({'valid': False})
        
        db = get_db()
        result = db.query('usuarios', params={'telefono_id': f'eq.{telefono_id}'})
        
        if result and len(result) > 0:
            user = result[0]
            return jsonify({
                'valid': True,
                'user': {
                    'id': user['id'],
                    'matricula': user['matricula'],
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'rol': user['rol']
                }
            })
        
        return jsonify({'valid': False})
        
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

# ========== API DE LOGOUT ==========

@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Cierra sesión"""
    return jsonify({'success': True, 'message': 'Sesión cerrada'})

# ========== API DE ESTADÍSTICAS PARA ALUMNO (DATOS REALES) ==========

@app.route('/api/alumno/<int:user_id>/estadisticas', methods=['GET'])
def get_estadisticas_alumno(user_id):
    """Obtiene estadísticas REALES del alumno"""
    try:
        db = get_db()
        
        # Verificar que el alumno existe
        alumno = db.query('usuarios', params={'id': f'eq.{user_id}', 'rol': 'eq.alumno'})
        if not alumno or len(alumno) == 0:
            return jsonify({'success': False, 'message': 'Alumno no encontrado'}), 404
        
        # Obtener todas las asistencias del alumno
        asistencias = db.query('asistencias', params={
            'alumno_id': f'eq.{user_id}',
            'select': 'id,valida,justificada'
        })
        
        # Calcular estadísticas
        asistencias_count = 0
        justificadas_count = 0
        
        if asistencias:
            for a in asistencias:
                if a.get('valida') or a.get('justificada'):
                    asistencias_count += 1
                if a.get('justificada'):
                    justificadas_count += 1
        
        # Obtener total de clases (podrías calcularlo de otra tabla)
        # Por ahora usamos un valor fijo o lo calculamos de las clases
        clases = db.query('clases', params={'select': 'count'})
        total_clases = clases[0]['count'] if clases and len(clases) > 0 else 20
        
        faltas_count = total_clases - asistencias_count
        porcentaje = round((asistencias_count / total_clases) * 100) if total_clases > 0 else 0
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'asistencias': asistencias_count,
                'faltas': faltas_count,
                'justificadas': justificadas_count,
                'total_clases': total_clases,
                'porcentaje': porcentaje
            }
        })
        
    except Exception as e:
        print(f"Error en estadísticas: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/alumno/<int:user_id>/actividad', methods=['GET'])
def get_actividad_alumno(user_id):
    """Obtiene actividad RECIENTE REAL del alumno"""
    try:
        db = get_db()
        
        # Obtener últimas 10 asistencias
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
                    'fecha': fecha_str,
                    'clase': f"Clase {a.get('clase_id', '')}"
                })
        
        return jsonify({
            'success': True,
            'actividades': actividades
        })
        
    except Exception as e:
        print(f"Error en actividad: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== API PARA REGISTRAR ASISTENCIA (ESCANEO QR) ==========

@app.route('/api/registrar-asistencia', methods=['POST'])
def registrar_asistencia():
    """Registra asistencia desde QR con geolocalización"""
    try:
        data = request.json
        qr_data = data.get('qr_data')
        telefono_id = data.get('telefono_id')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not qr_data or not telefono_id:
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
        
        db = get_db()
        
        # Identificar al alumno
        alumno = db.query('usuarios', params={
            'telefono_id': f'eq.{telefono_id}',
            'rol': 'eq.alumno'
        })
        
        if not alumno or len(alumno) == 0:
            return jsonify({'success': False, 'message': 'Alumno no encontrado'}), 404
        
        alumno_id = alumno[0]['id']
        
        # Decodificar QR
        try:
            qr_info = json.loads(qr_data)
            clase_id = qr_info.get('clase_id')
        except:
            clase_id = qr_data
        
        # Verificar clase activa
        clase = db.query('clases', params={
            'id': f'eq.{clase_id}',
            'activa': 'eq.true'
        })
        
        if not clase or len(clase) == 0:
            return jsonify({'success': False, 'message': 'Clase no válida o inactiva'}), 400
        
        clase_info = clase[0]
        
        # Verificar si ya registró
        existente = db.query('asistencias', params={
            'clase_id': f'eq.{clase_id}',
            'alumno_id': f'eq.{alumno_id}'
        })
        
        if existente and len(existente) > 0:
            return jsonify({'success': False, 'message': 'Ya registraste asistencia'}), 400
        
        # Calcular distancia
        distancia = None
        valida = True
        
        if latitud and longitud and clase_info.get('latitud_referencia'):
            punto_escaneo = (latitud, longitud)
            punto_clase = (clase_info['latitud_referencia'], clase_info['longitud_referencia'])
            distancia = geodesic(punto_escaneo, punto_clase).meters
            valida = distancia <= 7  # 5m + 2m tolerancia
        
        # Registrar asistencia
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
            return jsonify({
                'success': True,
                'message': 'Asistencia registrada',
                'valida': valida,
                'distancia': distancia
            }), 201
        
        return jsonify({'success': False, 'message': 'Error al registrar'}), 500
            
    except Exception as e:
        print(f"Error registrando asistencia: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== API PARA CLASES (PROFESOR) ==========

@app.route('/api/clase/activa', methods=['GET'])
def clase_activa():
    """Verifica si hay clase activa"""
    try:
        db = get_db()
        clase = db.query('clases', params={
            'activa': 'eq.true',
            'order': 'created_at.desc',
            'limit': 1
        })
        
        if clase and len(clase) > 0:
            return jsonify({
                'activa': True,
                'clase': clase[0]
            })
        
        return jsonify({'activa': False})
    except Exception as e:
        return jsonify({'activa': False, 'error': str(e)}), 500

@app.route('/api/clase/iniciar', methods=['POST'])
def iniciar_clase():
    """Inicia una nueva clase (profesor)"""
    try:
        data = request.json
        profesor_id = data.get('profesor_id')
        latitud = data.get('latitud')
        longitud = data.get('longitud')
        
        if not profesor_id:
            return jsonify({'success': False, 'message': 'ID de profesor requerido'}), 400
        
        db = get_db()
        
        # Verificar que no haya otra clase activa
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
                    'qr_base64': img_base64
                }
            })
        
        return jsonify({'success': False, 'message': 'Error al crear clase'}), 500
            
    except Exception as e:
        print(f"Error iniciando clase: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clase/<int:clase_id>/asistencias', methods=['GET'])
def get_asistencias_clase(clase_id):
    """Obtiene asistencias de una clase"""
    try:
        db = get_db()
        
        # Esta consulta puede ser compleja, mejor hacer varias
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
                        'matricula': alumno[0]['matricula'],
                        'nombre': alumno[0]['nombre'],
                        'fecha_escaneo': a['fecha_escaneo'],
                        'latitud': a['latitud_escaneo'],
                        'longitud': a['longitud_escaneo'],
                        'distancia': a['distancia_metros'],
                        'valida': a['valida'],
                        'justificada': a['justificada']
                    })
        
        return jsonify({
            'success': True,
            'asistencias': resultado
        })
        
    except Exception as e:
        print(f"Error obteniendo asistencias: {e}")
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

# ========== API PARA PROFESOR (DASHBOARD) ==========

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
        
        # Obtener todos los alumnos
        alumnos = db.query('usuarios', params={'rol': 'eq.alumno'})
        
        # Obtener total de clases
        clases = db.query('clases', params={'select': 'count'})
        total_clases = clases[0]['count'] if clases and len(clases) > 0 else 20
        
        verde = amarillo = naranja = rojo = 0
        alumnos_detalle = []
        
        if alumnos:
            for alumno in alumnos:
                # Obtener asistencias del alumno
                asistencias = db.query('asistencias', params={
                    'alumno_id': f'eq.{alumno["id"]}'
                })
                
                asistencias_count = 0
                if asistencias:
                    for a in asistencias:
                        if a.get('valida') or a.get('justificada'):
                            asistencias_count += 1
                
                porcentaje = round((asistencias_count / total_clases) * 100) if total_clases > 0 else 0
                
                # Clasificar
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
        
        return jsonify({
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
        })
        
    except Exception as e:
        print(f"Error en dashboard profesor: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ========== ERROR HANDLERS ==========

@app.errorhandler(404)
def not_found(error):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>404</title>
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
            .error-card { background: white; border-radius: 20px; padding: 40px; max-width: 500px; text-align: center; }
            .btn { background: #4361ee; color: white; padding: 12px 30px; text-decoration: none; border-radius: 10px; display: inline-block; }
        </style>
    </head>
    <body>
        <div class="error-card">
            <h1>🔍 404</h1>
            <p>Página no encontrada</p>
            <a href="/" class="btn">🏠 Inicio</a>
        </div>
    </body>
    </html>
    ''', 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)