"""RF09 · Reporte de uso por sala y rango de fechas · RF10 · Horas pico.

Definiciones de las métricas:
  · reservas     → todas las reservas del rango salvo las canceladas
  · usadas       → confirmadas o finalizadas (alguien llegó)
  · no_usadas    → liberadas (nadie confirmó en 15 minutos)
  · pendientes   → activas que aún no ocurren
  · canceladas   → canceladas por su titular antes del inicio
  · tasa_uso     → usadas / (usadas + no_usadas), en %
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..errores import DatosInvalidos
from .reglas import HORA_APERTURA, HORA_CIERRE, hora_txt, parse_fecha, parse_hora

MAX_DIAS_REPORTE = 366


def _rango(desde: Any, hasta: Any) -> tuple[str, str]:
    d = parse_fecha(desde, "desde")
    h = parse_fecha(hasta, "hasta")
    if d > h:
        raise DatosInvalidos(
            "La fecha «desde» debe ser anterior o igual a «hasta».", "RANGO_INVALIDO", campo="desde"
        )
    if (h - d).days > MAX_DIAS_REPORTE:
        raise DatosInvalidos(
            f"El rango puede abarcar como máximo {MAX_DIAS_REPORTE} días.", "RANGO_LARGO", campo="hasta"
        )
    return d.isoformat(), h.isoformat()


def _tasa(usadas: int, no_usadas: int) -> float | None:
    resueltas = usadas + no_usadas
    return round(100 * usadas / resueltas, 1) if resueltas else None


def reporte_uso(
    con: sqlite3.Connection, desde: Any, hasta: Any, sala_id: int | None = None
) -> dict[str, Any]:
    d, h = _rango(desde, hasta)
    filtro_sala = ""
    params: list[Any] = [d, h]
    if sala_id:
        filtro_sala = " AND s.id = ?"
        params.append(int(sala_id))

    filas = con.execute(
        f"""
        SELECT s.id AS sala_id, s.nombre, s.capacidad, s.ubicacion, s.activa,
            COALESCE(SUM(r.estado <> 'cancelada'), 0)                    AS reservas,
            COALESCE(SUM(r.estado IN ('confirmada', 'finalizada')), 0)   AS usadas,
            COALESCE(SUM(r.estado = 'liberada'), 0)                      AS no_usadas,
            COALESCE(SUM(r.estado = 'activa'), 0)                        AS pendientes,
            COALESCE(SUM(r.estado = 'cancelada'), 0)                     AS canceladas,
            COALESCE(SUM(CASE WHEN r.estado IN ('confirmada', 'finalizada')
                 THEN CAST(substr(r.hora_fin, 1, 2) AS INTEGER)
                    - CAST(substr(r.hora_inicio, 1, 2) AS INTEGER) END), 0) AS horas_usadas
        FROM sala s
        LEFT JOIN reserva r ON r.sala_id = s.id AND r.fecha BETWEEN ? AND ?
        WHERE 1 = 1 {filtro_sala}
        GROUP BY s.id
        ORDER BY s.nombre COLLATE NOCASE
        """,
        params,
    ).fetchall()

    por_sala = []
    totales = {k: 0 for k in ("reservas", "usadas", "no_usadas", "pendientes", "canceladas", "horas_usadas")}
    for f in filas:
        # Las salas inactivas sin movimiento en el rango no aportan al reporte.
        if not f["activa"] and f["reservas"] == 0 and f["canceladas"] == 0:
            continue
        item = {
            "sala_id": f["sala_id"],
            "nombre": f["nombre"],
            "capacidad": f["capacidad"],
            "ubicacion": f["ubicacion"],
            "activa": bool(f["activa"]),
        }
        for clave in totales:
            item[clave] = int(f[clave])
            totales[clave] += int(f[clave])
        item["tasa_uso"] = _tasa(item["usadas"], item["no_usadas"])
        por_sala.append(item)

    totales["tasa_uso"] = _tasa(totales["usadas"], totales["no_usadas"])
    return {"desde": d, "hasta": h, "sala_id": int(sala_id) if sala_id else None,
            "totales": totales, "por_sala": por_sala}


def horas_pico(
    con: sqlite3.Connection, desde: Any, hasta: Any, sala_id: int | None = None
) -> dict[str, Any]:
    """Cuántas reservas (no canceladas) ocupan cada bloque horario del rango."""
    d, h = _rango(desde, hasta)
    sql = """
        SELECT hora_inicio, hora_fin, estado FROM reserva
        WHERE fecha BETWEEN ? AND ? AND estado <> 'cancelada'
    """
    params: list[Any] = [d, h]
    if sala_id:
        sql += " AND sala_id = ?"
        params.append(int(sala_id))

    conteo = {hh: {"reservas": 0, "usadas": 0} for hh in range(HORA_APERTURA, HORA_CIERRE)}
    for fila in con.execute(sql, params):
        usada = fila["estado"] in ("confirmada", "finalizada")
        for hh in range(parse_hora(fila["hora_inicio"]), parse_hora(fila["hora_fin"])):
            if hh in conteo:
                conteo[hh]["reservas"] += 1
                conteo[hh]["usadas"] += int(usada)

    bloques = [
        {"hora_inicio": hora_txt(hh), "hora_fin": hora_txt(hh + 1), **valores}
        for hh, valores in conteo.items()
    ]
    maximo = max((b["reservas"] for b in bloques), default=0)
    pico = [b["hora_inicio"] for b in bloques if maximo and b["reservas"] == maximo]
    return {"desde": d, "hasta": h, "sala_id": int(sala_id) if sala_id else None,
            "bloques": bloques, "maximo": maximo, "horas_pico": pico}
