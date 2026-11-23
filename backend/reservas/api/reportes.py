"""RF09 · Reporte de uso · RF10 · Horas pico. Solo personal de biblioteca."""
from __future__ import annotations

from datetime import timedelta

from flask import Blueprint, jsonify, request

from .. import reloj
from ..db import get_db
from ..servicio import reportes as srv_reportes
from .sesion import parametro_entero, requiere_rol

bp = Blueprint("reportes", __name__)


def _rango_por_defecto() -> tuple[str, str]:
    hoy = reloj.ahora().date()
    desde = request.args.get("desde") or (hoy - timedelta(days=13)).isoformat()
    hasta = request.args.get("hasta") or hoy.isoformat()
    return desde, hasta


@bp.get("/reporte")
@requiere_rol("biblioteca")
def reporte():
    desde, hasta = _rango_por_defecto()
    return jsonify(srv_reportes.reporte_uso(get_db(), desde, hasta, parametro_entero("sala_id")))


@bp.get("/reporte/horas-pico")
@requiere_rol("biblioteca")
def horas_pico():
    desde, hasta = _rango_por_defecto()
    return jsonify(srv_reportes.horas_pico(get_db(), desde, hasta, parametro_entero("sala_id")))
