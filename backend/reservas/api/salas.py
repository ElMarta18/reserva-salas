"""RF01 · Salas. Consultar: ambos roles. Administrar: biblioteca."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..db import get_db
from ..servicio import salas as srv_salas
from .sesion import cuerpo_json, requiere_rol, usuario_actual

bp = Blueprint("salas", __name__)


@bp.get("/salas")
@requiere_rol()
def listar():
    incluir = request.args.get("incluir_inactivas") == "1" and usuario_actual()["rol"] == "biblioteca"
    return jsonify(srv_salas.listar_salas(get_db(), incluir_inactivas=incluir))


@bp.get("/salas/<int:sala_id>")
@requiere_rol()
def obtener(sala_id: int):
    return jsonify(srv_salas.obtener_sala(get_db(), sala_id))


@bp.post("/salas")
@requiere_rol("biblioteca")
def crear():
    return jsonify(srv_salas.crear_sala(get_db(), cuerpo_json())), 201


@bp.put("/salas/<int:sala_id>")
@requiere_rol("biblioteca")
def actualizar(sala_id: int):
    return jsonify(srv_salas.actualizar_sala(get_db(), sala_id, cuerpo_json()))


@bp.delete("/salas/<int:sala_id>")
@requiere_rol("biblioteca")
def eliminar(sala_id: int):
    srv_salas.eliminar_sala(get_db(), sala_id)
    return "", 204
