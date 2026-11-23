"""RF04 crear · RF05 cancelar · RF06 confirmar · RF08 mis reservas."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .. import reloj
from ..db import get_db
from ..errores import SinPermiso
from ..servicio import reservas as srv_reservas
from .sesion import cuerpo_json, parametro_entero, requiere_rol, usuario_actual

bp = Blueprint("reservas", __name__)


@bp.post("/reservas")
@requiere_rol("estudiante")
def crear():
    """201 si se guarda; 409 si una regla la rechaza; 400 si faltan datos."""
    reserva = srv_reservas.crear_reserva(get_db(), usuario_actual()["id"], cuerpo_json(), reloj.ahora())
    return jsonify(reserva), 201


@bp.get("/reservas/mias")
@requiere_rol("estudiante")
def mias():
    return jsonify(srv_reservas.mis_reservas(get_db(), usuario_actual()["id"], reloj.ahora()))


@bp.get("/reservas")
@requiere_rol("biblioteca")
def listar():
    return jsonify(
        srv_reservas.listar_reservas(
            get_db(),
            reloj.ahora(),
            desde=request.args.get("desde") or None,
            hasta=request.args.get("hasta") or None,
            sala_id=parametro_entero("sala_id"),
            estado=request.args.get("estado") or None,
        )
    )


@bp.get("/reservas/<int:reserva_id>")
@requiere_rol()
def obtener(reserva_id: int):
    usuario = usuario_actual()
    fila = srv_reservas.obtener_reserva(get_db(), reserva_id)
    if usuario["rol"] != "biblioteca" and fila["usuario_id"] != usuario["id"]:
        raise SinPermiso("Esta reserva no es tuya.", "RESERVA_AJENA")
    return jsonify(srv_reservas.a_dict(fila, reloj.ahora()))


@bp.post("/reservas/<int:reserva_id>/cancelar")
@requiere_rol("estudiante")
def cancelar(reserva_id: int):
    return jsonify(srv_reservas.cancelar_reserva(get_db(), reserva_id, usuario_actual()["id"], reloj.ahora()))


@bp.post("/reservas/<int:reserva_id>/confirmar")
@requiere_rol("estudiante")
def confirmar(reserva_id: int):
    return jsonify(srv_reservas.confirmar_llegada(get_db(), reserva_id, usuario_actual()["id"], reloj.ahora()))
