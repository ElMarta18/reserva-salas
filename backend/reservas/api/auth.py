"""Salud del servicio e inicio de sesión simulado."""
from __future__ import annotations

from flask import Blueprint, jsonify

from .. import reloj
from ..db import get_db
from ..errores import DatosInvalidos, NoEncontrado
from ..servicio import reglas
from ..servicio import usuarios as srv_usuarios
from .sesion import cuerpo_json, requiere_rol, usuario_actual

bp = Blueprint("auth", __name__)


@bp.get("/salud")
def salud():
    return jsonify(
        {
            "estado": "ok",
            "ahora": reloj.formatear(reloj.ahora()),
            "reglas": {
                "hora_apertura": reglas.hora_txt(reglas.HORA_APERTURA),
                "hora_cierre": reglas.hora_txt(reglas.HORA_CIERRE),
                "max_horas_seguidas": reglas.MAX_HORAS_SEGUIDAS,
                "max_reservas_vigentes": reglas.MAX_RESERVAS_VIGENTES,
                "minutos_confirmacion": reglas.MINUTOS_CONFIRMACION,
            },
        }
    )


@bp.get("/auth/usuarios-demo")
def usuarios_demo():
    """Lista de usuarios para el selector del inicio de sesión simulado."""
    return jsonify(srv_usuarios.listar_usuarios(get_db()))


@bp.post("/auth/login")
def login():
    datos = cuerpo_json()
    correo = str(datos.get("correo") or "").strip()
    if not correo:
        raise DatosInvalidos("Escribe tu correo.", "CORREO_REQUERIDO", campo="correo")
    usuario = srv_usuarios.buscar_por_correo(get_db(), correo)
    if usuario is None:
        raise NoEncontrado("No hay un usuario registrado con ese correo.", "USUARIO_NO_EXISTE", campo="correo")
    return jsonify(usuario)


@bp.get("/auth/yo")
@requiere_rol()
def yo():
    return jsonify(usuario_actual())


@bp.post("/auth/registro")
def registro():
    datos = cuerpo_json()
    datos["rol"] = "estudiante"
    usuario = srv_usuarios.crear_usuario(get_db(), datos)
    return jsonify(usuario), 201
