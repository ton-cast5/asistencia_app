# api/index.py — AttendanceApp Backend
# Vercel Serverless Function — Python Flask

import os
import hashlib
import secrets
import re
import json
import math
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# DATABASE CLIENT
# ─────────────────────────────────────────────
import requests as req

class DB:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_KEY", "")
        if not self.url or not self.key:
            raise RuntimeError("SUPABASE_URL y SUPABASE_KEY son requeridos")
        self.h = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _url(self, table):
        return f"{self.url}/rest/v1/{table}"

    def select(self, table, params=None):
        r = req.get(self._url(table), headers=self.h, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def insert(self, table, data):
        r = req.post(self._url(table), headers=self.h, json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def update(self, table, data, params):
        r = req.patch(self._url(table), headers=self.h, json=data, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def delete(self, table, params):
        r = req.delete(self._url(table), headers=self.h, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def rpc(self, fn, payload=None):
        r = req.post(f"{self.url}/rest/v1/rpc/{fn}", headers=self.h, json=payload or {}, timeout=10)
        r.raise_for_status()
        return r.json()

_db = None
def get_db():
    global _db
    if _db is None:
        _db = DB()
    return _db

# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────
def hp(password: str) -> str:
    """Hash de contraseña con SHA-256 + salt fijo de env"""
    salt = os.getenv("PASSWORD_SALT", "attendanceapp_salt_2024")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def token() -> str:
    return secrets.token_urlsafe(32)

def valid_matricula(m: str) -> bool:
    # Formato: 9 chars alfanuméricos (ej. 232H17024)
    return bool(re.match(r'^[A-Z0-9]{9}$', m.upper()))

def valid_email(e: str) -> bool:
    return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', e))

def haversine(lat1, lon1, lat2, lon2) -> float | None:
    """Distancia en metros entre dos coordenadas GPS"""
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def cors():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

def ok(data: dict, status=200):
    return (json.dumps(data), status, {"Content-Type": "application/json", **cors()})

def err(msg: str, status=400):
    return (json.dumps({"success": False, "message": msg}), status, {"Content-Type": "application/json", **cors()})

# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

# ── AUTH ──────────────────────────────────────

def h_register(req_obj):
    """POST /api/register"""
    data = req_obj.get_json() or {}
    required = ["matricula", "nombre", "apellido_paterno", "apellido_materno",
                "email", "password", "rol", "telefono_id"]
    
    for f in required:
        if not data.get(f):
            return err(f"Campo requerido: {f}")

    if not valid_matricula(data["matricula"]):
        return err("Matrícula inválida. Formato: 9 caracteres (ej: 232H17024)")

    if not valid_email(data["email"]):
        return err("Email inválido")

    if len(data["password"]) < 8:
        return err("La contraseña debe tener mínimo 8 caracteres")

    if data["rol"] not in ("alumno", "profesor"):
        return err("Rol inválido")

    db = get_db()

    # Verificar duplicados
    for field, val in [("email", data["email"]),
                       ("matricula", data["matricula"].upper()),
                       ("telefono_id", data["telefono_id"])]:
        existing = db.select("usuarios", {field: f"eq.{val}"})
        if existing:
            labels = {"email": "correo electrónico", "matricula": "matrícula", "telefono_id": "dispositivo"}
            return err(f"El {labels.get(field, field)} ya está registrado")

    nombre_completo = f"{data['nombre']} {data['apellido_paterno']} {data['apellido_materno']}".strip()

    new_user = {
        "matricula": data["matricula"].upper(),
        "nombre": nombre_completo,
        "nombre_corto": data["nombre"],
        "apellido_paterno": data["apellido_paterno"],
        "apellido_materno": data["apellido_materno"],
        "email": data["email"],
        "password_hash": hp(data["password"]),
        "rol": data["rol"],
        "telefono_id": data["telefono_id"],
        "created_at": datetime.now().isoformat(),
    }

    result = db.insert("usuarios", new_user)
    if not result:
        return err("Error al crear el usuario", 500)

    user = result[0]
    return ok({
        "success": True,
        "message": "Registro exitoso",
        "user": _safe_user(user),
        "token": token(),
    }, 201)


def h_login(req_obj):
    """POST /api/login"""
    data = req_obj.get_json() or {}
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    telefono_id = data.get("telefono_id", "")

    if not email or not password:
        return err("Email y contraseña requeridos")

    db = get_db()
    users = db.select("usuarios", {"email": f"eq.{email}"})

    if not users:
        return err("Credenciales inválidas", 401)

    user = users[0]

    if user["password_hash"] != hp(password):
        return err("Credenciales inválidas", 401)

    # ── VERIFICACIÓN DE DISPOSITIVO ──────────────────
    # Si el usuario ya tiene telefono_id registrado y no coincide → bloquear
    if user.get("telefono_id") and telefono_id and user["telefono_id"] != telefono_id:
        return err("Esta cuenta no pertenece a este dispositivo", 403)

    # Si no tenía telefono_id, asignar este
    if telefono_id and not user.get("telefono_id"):
        db.update("usuarios", {"telefono_id": telefono_id}, {"id": f"eq.{user['id']}"})
        user["telefono_id"] = telefono_id

    # Actualizar last_login
    db.update("usuarios", {"last_login": datetime.now().isoformat()}, {"id": f"eq.{user['id']}"})

    return ok({
        "success": True,
        "message": "Login exitoso",
        "user": _safe_user(user),
        "token": token(),
    })


def h_verify(req_obj):
    """POST /api/verify-session — verificar sesión por telefono_id"""
    data = req_obj.get_json() or {}
    telefono_id = data.get("telefono_id", "")

    if not telefono_id:
        return ok({"valid": False})

    db = get_db()
    users = db.select("usuarios", {"telefono_id": f"eq.{telefono_id}"})

    if not users:
        return ok({"valid": False})

    return ok({"valid": True, "user": _safe_user(users[0])})


# ── ALUMNO ────────────────────────────────────

def h_alumno_stats(req_obj, user_id: int):
    """GET /api/alumno/<id>/estadisticas"""
    db = get_db()
    alumnos = db.select("usuarios", {"id": f"eq.{user_id}", "rol": "eq.alumno"})
    if not alumnos:
        return err("Alumno no encontrado", 404)

    asistencias = db.select("asistencias", {
        "alumno_id": f"eq.{user_id}",
        "select": "id,valida,justificada,clase_id"
    }) or []

    total_clases_query = db.select("clases", {"select": "count"})
    total_clases = total_clases_query[0]["count"] if total_clases_query else 0

    presentes = sum(1 for a in asistencias if a.get("valida"))
    justificadas = sum(1 for a in asistencias if a.get("justificada"))
    faltas = max(0, total_clases - presentes - justificadas)
    porcentaje = round((presentes / total_clases) * 100) if total_clases > 0 else 0

    return ok({
        "success": True,
        "stats": {
            "presentes": presentes,
            "justificadas": justificadas,
            "faltas": faltas,
            "total_clases": total_clases,
            "porcentaje": porcentaje,
        }
    })


def h_alumno_actividad(req_obj, user_id: int):
    """GET /api/alumno/<id>/actividad"""
    db = get_db()
    asistencias = db.select("asistencias", {
        "alumno_id": f"eq.{user_id}",
        "select": "id,fecha_escaneo,valida,justificada,clase_id,distancia_metros",
        "order": "fecha_escaneo.desc",
        "limit": "20"
    }) or []

    result = []
    for a in asistencias:
        clase = None
        if a.get("clase_id"):
            clases = db.select("clases", {
                "id": f"eq.{a['clase_id']}",
                "select": "id,fecha,hora_inicio,titulo,materia_id"
            })
            clase = clases[0] if clases else None

        result.append({
            "id": a["id"],
            "fecha": a.get("fecha_escaneo"),
            "valida": a.get("valida", False),
            "justificada": a.get("justificada", False),
            "distancia": float(a["distancia_metros"]) if a.get("distancia_metros") else None,
            "clase": clase,
        })

    return ok({"success": True, "actividad": result})


def h_alumno_horario(req_obj, user_id: int):
    """GET /api/alumno/<id>/horario"""
    db = get_db()
    horarios = db.select("horarios", {
        "alumno_id": f"eq.{user_id}",
        "select": "id,dia_semana,hora_inicio,hora_fin,aula,materia_id"
    }) or []

    result = []
    for h in horarios:
        materia = None
        if h.get("materia_id"):
            materias = db.select("materias", {
                "id": f"eq.{h['materia_id']}",
                "select": "id,nombre,codigo"
            })
            materia = materias[0] if materias else None

        result.append({**h, "materia": materia})

    return ok({"success": True, "horario": result})


# ── CLASE / QR ────────────────────────────────

def h_clase_activa(req_obj):
    """GET /api/clase/activa?profesor_id=X"""
    profesor_id = req_obj.args.get("profesor_id")
    if not profesor_id:
        return err("profesor_id requerido")

    db = get_db()
    clases = db.select("clases", {
        "profesor_id": f"eq.{profesor_id}",
        "activa": "eq.true",
        "order": "created_at.desc",
        "limit": "1"
    })

    if not clases:
        return ok({"success": True, "clase": None})

    clase = clases[0]
    # Traer asistencias de esta clase
    asistencias = db.select("asistencias", {
        "clase_id": f"eq.{clase['id']}",
        "select": "id,alumno_id,fecha_escaneo,valida",
        "order": "fecha_escaneo.desc"
    }) or []

    # Enriquecer con nombre
    for a in asistencias:
        if a.get("alumno_id"):
            alumnos = db.select("usuarios", {
                "id": f"eq.{a['alumno_id']}",
                "select": "matricula,nombre,apellido_paterno,apellido_materno"
            })
            a["alumno"] = alumnos[0] if alumnos else None

    return ok({"success": True, "clase": clase, "asistencias": asistencias})


def h_clase_iniciar(req_obj):
    """POST /api/clase/iniciar"""
    data = req_obj.get_json() or {}
    profesor_id = data.get("profesor_id")
    latitud = data.get("latitud")
    longitud = data.get("longitud")
    titulo = data.get("titulo", "Clase")
    materia_id = data.get("materia_id")

    if not profesor_id:
        return err("profesor_id requerido")

    db = get_db()

    # Terminar cualquier clase activa anterior del mismo profe
    clases_activas = db.select("clases", {
        "profesor_id": f"eq.{profesor_id}",
        "activa": "eq.true"
    }) or []
    for c in clases_activas:
        db.update("clases", {"activa": False, "hora_fin": datetime.now().strftime("%H:%M:%S")},
                  {"id": f"eq.{c['id']}"})

    # Generar token único para el QR
    qr_token = token()
    ahora = datetime.now()

    nueva_clase = {
        "profesor_id": int(profesor_id),
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora_inicio": ahora.strftime("%H:%M:%S"),
        "activa": True,
        "qr_code": qr_token,
        "latitud_referencia": latitud,
        "longitud_referencia": longitud,
        "titulo": titulo,
        "materia_id": materia_id,
        "created_at": ahora.isoformat(),
    }

    result = db.insert("clases", nueva_clase)
    if not result:
        return err("Error al iniciar clase", 500)

    clase = result[0]
    return ok({"success": True, "clase": clase, "qr_token": qr_token}, 201)


def h_clase_terminar(req_obj):
    """POST /api/clase/terminar"""
    data = req_obj.get_json() or {}
    clase_id = data.get("clase_id")
    if not clase_id:
        return err("clase_id requerido")

    db = get_db()
    result = db.update("clases", {
        "activa": False,
        "hora_fin": datetime.now().strftime("%H:%M:%S"),
        "qr_code": None,  # Invalidar QR al terminar
    }, {"id": f"eq.{clase_id}"})

    return ok({"success": True, "message": "Clase terminada"})


# ── ASISTENCIA ────────────────────────────────

def h_registrar_asistencia(req_obj):
    """POST /api/registrar-asistencia"""
    data = req_obj.get_json() or {}
    qr_token = data.get("qr_token")
    alumno_id = data.get("alumno_id")
    latitud = data.get("latitud")
    longitud = data.get("longitud")
    telefono_id = data.get("telefono_id")

    if not qr_token or not alumno_id:
        return err("qr_token y alumno_id requeridos")

    db = get_db()

    # 1. Buscar clase activa con ese QR
    clases = db.select("clases", {
        "qr_code": f"eq.{qr_token}",
        "activa": "eq.true"
    })
    if not clases:
        return err("QR inválido o clase ya finalizada", 400)

    clase = clases[0]

    # 2. Verificar dispositivo del alumno
    alumnos = db.select("usuarios", {"id": f"eq.{alumno_id}"})
    if not alumnos:
        return err("Alumno no encontrado", 404)

    alumno = alumnos[0]
    if alumno.get("telefono_id") and telefono_id and alumno["telefono_id"] != telefono_id:
        return err("Esta cuenta no pertenece a este dispositivo", 403)

    # 3. Verificar que no haya registrado ya en esta clase
    existente = db.select("asistencias", {
        "clase_id": f"eq.{clase['id']}",
        "alumno_id": f"eq.{alumno_id}"
    })
    if existente:
        return err("Ya registraste asistencia en esta clase", 409)

    # 4. Calcular distancia si hay coordenadas
    distancia = None
    valida = True
    RADIO_MAX = 50  # metros (GPS es impreciso en interiores, usamos 50m)

    if latitud and longitud and clase.get("latitud_referencia") and clase.get("longitud_referencia"):
        distancia = haversine(
            float(latitud), float(longitud),
            float(clase["latitud_referencia"]), float(clase["longitud_referencia"])
        )
        if distancia is not None and distancia > RADIO_MAX:
            return err(f"Estás demasiado lejos del aula ({distancia:.0f}m). Máximo permitido: {RADIO_MAX}m", 400)

    # 5. Registrar asistencia
    nueva = {
        "clase_id": clase["id"],
        "alumno_id": int(alumno_id),
        "fecha_escaneo": datetime.now().isoformat(),
        "latitud_escaneo": latitud,
        "longitud_escaneo": longitud,
        "distancia_metros": round(distancia, 2) if distancia is not None else None,
        "valida": valida,
        "justificada": False,
    }

    result = db.insert("asistencias", nueva)
    if not result:
        return err("Error al registrar asistencia", 500)

    return ok({
        "success": True,
        "message": "✅ Asistencia registrada",
        "asistencia": result[0],
        "distancia": distancia,
        "clase": {
            "id": clase["id"],
            "titulo": clase.get("titulo"),
            "fecha": clase.get("fecha"),
        },
        "alumno": {
            "nombre": alumno.get("nombre"),
            "matricula": alumno.get("matricula"),
        }
    }, 201)


# ── PROFESOR DASHBOARD ────────────────────────

def h_profesor_dashboard(req_obj, user_id: int):
    """GET /api/profesor/<id>/dashboard"""
    db = get_db()

    profesores = db.select("usuarios", {"id": f"eq.{user_id}", "rol": "eq.profesor"})
    if not profesores:
        return err("Profesor no encontrado", 404)

    alumnos = db.select("usuarios", {"rol": "eq.alumno", "select": "id,matricula,nombre,apellido_paterno,apellido_materno"}) or []
    total_clases_q = db.select("clases", {"profesor_id": f"eq.{user_id}", "select": "count"})
    total_clases = total_clases_q[0]["count"] if total_clases_q else 0

    categorias = {"excelente": 0, "riesgo": 0, "sin_ordinario": 0, "sin_extraordinario": 0}
    alumnos_info = []

    for alumno in alumnos:
        asis = db.select("asistencias", {
            "alumno_id": f"eq.{alumno['id']}",
            "valida": "eq.true",
            "select": "id"
        }) or []
        presentes = len(asis)
        pct = round((presentes / total_clases) * 100) if total_clases > 0 else 0

        if pct >= 90:
            categorias["excelente"] += 1
            estado = "excelente"
        elif pct >= 80:
            categorias["riesgo"] += 1
            estado = "riesgo"
        elif pct >= 60:
            categorias["sin_ordinario"] += 1
            estado = "sin_ordinario"
        else:
            categorias["sin_extraordinario"] += 1
            estado = "sin_extraordinario"

        alumnos_info.append({
            "id": alumno["id"],
            "matricula": alumno["matricula"],
            "nombre": alumno.get("nombre"),
            "apellido_paterno": alumno.get("apellido_paterno"),
            "apellido_materno": alumno.get("apellido_materno"),
            "asistencias": presentes,
            "porcentaje": pct,
            "estado": estado,
        })

    return ok({
        "success": True,
        "dashboard": {
            "total_alumnos": len(alumnos),
            "total_clases": total_clases,
            "categorias": categorias,
            "alumnos": sorted(alumnos_info, key=lambda x: x.get("apellido_paterno",""))
        }
    })


def h_clase_asistencias(req_obj, clase_id: int):
    """GET /api/clase/<id>/asistencias"""
    db = get_db()
    asistencias = db.select("asistencias", {
        "clase_id": f"eq.{clase_id}",
        "select": "id,alumno_id,fecha_escaneo,valida,distancia_metros",
        "order": "fecha_escaneo.asc"
    }) or []

    result = []
    for a in asistencias:
        alumno = None
        if a.get("alumno_id"):
            alumnos = db.select("usuarios", {
                "id": f"eq.{a['alumno_id']}",
                "select": "matricula,nombre,apellido_paterno,apellido_materno"
            })
            alumno = alumnos[0] if alumnos else None
        result.append({**a, "alumno": alumno})

    return ok({"success": True, "asistencias": result})


def h_reporte_pdf_data(req_obj, user_id: int):
    """GET /api/profesor/<id>/reporte — datos para generar PDF
       Query param opcional: ?materia_id=X para filtrar por materia
    """
    db = get_db()
    materia_id = req_obj.args.get("materia_id")

    alumnos = db.select("usuarios", {
        "rol": "eq.alumno",
        "select": "id,matricula,nombre,apellido_paterno,apellido_materno",
        "order": "apellido_paterno.asc"
    }) or []

    # Clases del profesor, filtradas por materia si se especifica
    clases_params = {
        "profesor_id": f"eq.{user_id}",
        "select": "id,fecha,hora_inicio,titulo,activa,materia_id",
        "order": "fecha.asc"
    }
    if materia_id:
        clases_params["materia_id"] = f"eq.{materia_id}"

    clases = db.select("clases", clases_params) or []

    tabla = []
    for alumno in alumnos:
        fila = {
            "id": alumno["id"],
            "matricula": alumno["matricula"],
            "nombre": alumno.get("nombre",""),
            "apellido_paterno": alumno.get("apellido_paterno",""),
            "apellido_materno": alumno.get("apellido_materno",""),
            "clases": {}
        }
        asis_alumno = db.select("asistencias", {
            "alumno_id": f"eq.{alumno['id']}",
            "select": "clase_id,valida,justificada"
        }) or []

        asis_por_clase = {a["clase_id"]: a for a in asis_alumno}
        for clase in clases:
            a = asis_por_clase.get(clase["id"])
            if a:
                fila["clases"][clase["id"]] = "P" if a.get("valida") else ("J" if a.get("justificada") else "F")
            else:
                fila["clases"][clase["id"]] = "F"

        tabla.append(fila)

    return ok({
        "success": True,
        "reporte": {
            "clases": clases,
            "alumnos": tabla,
            "generado": datetime.now().isoformat()
        }
    })


def h_materias(req_obj, user_id: int):
    """GET /api/profesor/<id>/materias"""
    db = get_db()
    materias = db.select("materias", {
        "profesor_id": f"eq.{user_id}",
        "select": "id,nombre,codigo",
        "order": "nombre.asc"
    }) or []
    return ok({"success": True, "materias": materias})


def h_materia_create(req_obj, user_id: int):
    """POST /api/profesor/<id>/materias"""
    data = req_obj.get_json() or {}
    nombre = data.get("nombre", "").strip()
    codigo = data.get("codigo", "").strip()

    if not nombre:
        return err("El nombre de la materia es requerido")

    db = get_db()
    result = db.insert("materias", {
        "nombre": nombre,
        "codigo": codigo or None,
        "profesor_id": user_id,
        "created_at": datetime.now().isoformat(),
    })
    if not result:
        return err("Error al crear la materia", 500)

    return ok({"success": True, "materia": result[0]}, 201)


def h_materia_update(req_obj, user_id: int, materia_id: int):
    """PATCH /api/profesor/<id>/materias/<mid>"""
    data = req_obj.get_json() or {}
    nombre = data.get("nombre", "").strip()
    codigo = data.get("codigo", "").strip()

    if not nombre:
        return err("El nombre es requerido")

    db = get_db()
    result = db.update("materias",
        {"nombre": nombre, "codigo": codigo or None},
        {"id": f"eq.{materia_id}", "profesor_id": f"eq.{user_id}"}
    )
    return ok({"success": True, "materia": result[0] if result else {}})


def h_materia_delete(req_obj, user_id: int, materia_id: int):
    """DELETE /api/profesor/<id>/materias/<mid>"""
    db = get_db()
    # Verificar que la materia pertenece al profesor
    m = db.select("materias", {"id": f"eq.{materia_id}", "profesor_id": f"eq.{user_id}"})
    if not m:
        return err("Materia no encontrada o no autorizada", 404)
    db.delete("materias", {"id": f"eq.{materia_id}"})
    return ok({"success": True})


def h_check_field(req_obj, field: str):
    """POST /api/check/<field>"""
    data = req_obj.get_json() or {}
    val = data.get(field, "")
    if not val:
        return ok({"exists": False})
    db = get_db()
    result = db.select("usuarios", {field: f"eq.{val}"})
    return ok({"exists": bool(result)})


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _safe_user(u: dict) -> dict:
    """Usuario sin password_hash"""
    return {k: v for k, v in u.items() if k != "password_hash"}


# ─────────────────────────────────────────────
# ROUTER — ENTRY POINT VERCEL
# ─────────────────────────────────────────────

def handler(request, **kwargs):
    if request.method == "OPTIONS":
        return ("", 204, cors())

    path = request.path.rstrip("/")
    method = request.method

    try:
        # ── AUTH ──────────────────────────────
        if path == "/api/register" and method == "POST":
            return h_register(request)

        if path == "/api/login" and method == "POST":
            return h_login(request)

        if path == "/api/verify-session" and method == "POST":
            return h_verify(request)

        # ── CHECK DUPLICADOS ──────────────────
        if path == "/api/check/email" and method == "POST":
            return h_check_field(request, "email")

        if path == "/api/check/matricula" and method == "POST":
            return h_check_field(request, "matricula")

        # ── CLASE ─────────────────────────────
        if path == "/api/clase/activa" and method == "GET":
            return h_clase_activa(request)

        if path == "/api/clase/iniciar" and method == "POST":
            return h_clase_iniciar(request)

        if path == "/api/clase/terminar" and method == "POST":
            return h_clase_terminar(request)

        # ── ASISTENCIA ────────────────────────
        if path == "/api/registrar-asistencia" and method == "POST":
            return h_registrar_asistencia(request)

        # ── ALUMNO ────────────────────────────
        parts = path.split("/")
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "alumno":
            uid = int(parts[3])
            if len(parts) == 5:
                endpoint = parts[4]
                if endpoint == "estadisticas" and method == "GET":
                    return h_alumno_stats(request, uid)
                if endpoint == "actividad" and method == "GET":
                    return h_alumno_actividad(request, uid)
                if endpoint == "horario" and method == "GET":
                    return h_alumno_horario(request, uid)

        # ── PROFESOR ──────────────────────────
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "profesor":
            uid = int(parts[3])
            if len(parts) == 5:
                endpoint = parts[4]
                if endpoint == "dashboard" and method == "GET":
                    return h_profesor_dashboard(request, uid)
                if endpoint == "reporte" and method == "GET":
                    return h_reporte_pdf_data(request, uid)
                if endpoint == "materias":
                    if method == "GET":
                        return h_materias(request, uid)
                    if method == "POST":
                        return h_materia_create(request, uid)
            # /api/profesor/<id>/materias/<mid>
            if len(parts) == 6 and parts[4] == "materias":
                mid = int(parts[5])
                if method == "PATCH":
                    return h_materia_update(request, uid, mid)
                if method == "DELETE":
                    return h_materia_delete(request, uid, mid)

        # ── CLASE ASISTENCIAS ─────────────────
        if len(parts) == 5 and parts[1] == "api" and parts[2] == "clase" and parts[4] == "asistencias":
            clase_id = int(parts[3])
            if method == "GET":
                return h_clase_asistencias(request, clase_id)

        return err("Ruta no encontrada", 404)

    except ValueError as e:
        return err(f"Parámetro inválido: {e}", 400)
    except Exception as e:
        print(f"ERROR: {e}")
        return err(f"Error interno del servidor", 500)