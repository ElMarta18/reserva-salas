"""RF02 · Usuarios con su rol. Solo personal de biblioteca."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..errores import ReglaIncumplida
from ..servicio import usuarios as srv_usuarios
from .sesion import cuerpo_json, requiere_rol, usuario_actual

bp = Blueprint("usuarios", __name__)


@bp.get("/usuarios")
@requiere_rol("biblioteca")
def listar():
    return jsonify(srv_usuarios.listar_usuarios(get_db(), rol=request.args.get("rol") or None))


@bp.get("/usuarios/<int:usuario_id>")
@requiere_rol("biblioteca")
def obtener(usuario_id: int):
    return jsonify(srv_usuarios.obtener_usuario(get_db(), usuario_id))


@bp.post("/usuarios")
@requiere_rol("biblioteca")
def crear():
    return jsonify(srv_usuarios.crear_usuario(get_db(), cuerpo_json())), 201


@bp.put("/usuarios/<int:usuario_id>")
@requiere_rol("biblioteca")
def actualizar(usuario_id: int):
    datos = cuerpo_json()
    if usuario_id == usuario_actual()["id"] and datos.get("rol") not in (None, "biblioteca"):
        raise ReglaIncumplida("No puedes quitarte tu propio rol de biblioteca.", "AUTO_CAMBIO_ROL", campo="rol")
    return jsonify(srv_usuarios.actualizar_usuario(get_db(), usuario_id, datos))


@bp.delete("/usuarios/<int:usuario_id>")
@requiere_rol("biblioteca")
def eliminar(usuario_id: int):
    if usuario_id == usuario_actual()["id"]:
        raise ReglaIncumplida("No puedes eliminar tu propio usuario.", "AUTO_ELIMINACION")
    srv_usuarios.eliminar_usuario(get_db(), usuario_id)
    return "", 204
