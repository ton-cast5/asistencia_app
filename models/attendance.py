# models/attendance.py
import qrcode
import json
from datetime import datetime

def generar_qr_clase(clase_id, profesor_id, latitud, longitud):
    """Genera QR con datos de la clase"""
    data = {
        'clase_id': clase_id,
        'profesor_id': profesor_id,
        'latitud': str(latitud),
        'longitud': str(longitud),
        'timestamp': datetime.now().isoformat()
    }
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json.dumps(data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(f"static/qr_codes/clase_{clase_id}.png")
    
    return f"static/qr_codes/clase_{clase_id}.png"
from database import get_db

def registrar_asistencia(clase_id, alumno_id, latitud, longitud):
    db = get_db()
    data = {
        'clase_id': clase_id,
        'alumno_id': alumno_id,
        'latitud_escaneo': latitud,
        'longitud_escaneo': longitud,
        'valida': True
    }
    return db.query('asistencias', method='POST', data=data)