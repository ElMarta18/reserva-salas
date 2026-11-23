"""RF03 · Consultar disponibilidad por fecha y sala (ambos roles)."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .. import reloj
from ..db import get_db
from ..servicio import disponibilidad as srv_disp
from ..servicio import reservas as srv_reservas
from ..servicio.reglas import parse_fecha
from .sesion import parametro_entero, requiere_rol, usuario_actual

bp = Blueprint("disponibilidad", __name__)


@bp.get("/disponibilidad")
@requiere_rol()
def disponibilidad():
    ahora = reloj.ahora()
    fecha = request.args.get("fecha") or ahora.date().isoformat()
    usuario = usuario_actual()
    return jsonify(
        srv_disp.disponibilidad(
            get_db(), fecha, ahora, usuario_id=usuario["id"], sala_id=parametro_entero("sala_id")
        )
    )


@bp.get("/disponibilidad/<int:sala_id>/bloques-libres")
@requiere_rol()
def bloques_libres(sala_id: int):
    """Inicios posibles para una duración dada (usado por «Nueva reserva»)."""
    ahora = reloj.ahora()
    fecha = request.args.get("fecha") or ahora.date().isoformat()
    duracion = parametro_entero("duracion") or 1
    dia = parse_fecha(fecha).isoformat()
    return jsonify(
        {"fecha": dia, "duracion": duracion,
         "bloques": srv_reservas.bloques_libres(
             get_db(), sala_id, dia, ahora, duracion, usuario_actual()["id"])}
    )
