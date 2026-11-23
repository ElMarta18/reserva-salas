"""RF03 · Consultar disponibilidad por fecha y sala."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from . import reglas
from .reglas import HORA_APERTURA, HORA_CIERRE, hora_txt, parse_fecha, parse_hora


def disponibilidad(
    con: sqlite3.Connection,
    fecha: Any,
    ahora: datetime,
    usuario_id: int | None = None,
    sala_id: int | None = None,
) -> dict[str, Any]:
    """Estado de cada bloque de 1 hora para cada sala activa.

    Estados posibles por bloque:
      · libre    → se puede reservar
      · ocupado  → otra persona lo tiene reservado (activa o confirmada)
      · propia   → reserva vigente del usuario que consulta
      · pasado   → el bloque ya comenzó y no se puede reservar
    """
    dia = parse_fecha(fecha).isoformat()

    sql_salas = "SELECT * FROM sala WHERE activa = 1"
    params: list[Any] = []
    if sala_id:
        sql_salas += " AND id = ?"
        params.append(int(sala_id))
    salas = con.execute(sql_salas + " ORDER BY nombre COLLATE NOCASE", params).fetchall()

    ocupacion: dict[tuple[int, int], int] = {}   # (sala_id, hora) -> usuario_id
    for fila in con.execute(
        """
        SELECT sala_id, usuario_id, hora_inicio, hora_fin FROM reserva
        WHERE fecha = ? AND estado IN ('activa', 'confirmada')
        """,
        (dia,),
    ):
        for h in range(parse_hora(fila["hora_inicio"]), parse_hora(fila["hora_fin"])):
            ocupacion[(fila["sala_id"], h)] = fila["usuario_id"]

    resultado = []
    for sala in salas:
        bloques = []
        libres = 0
        for h in range(HORA_APERTURA, HORA_CIERRE):
            dueno = ocupacion.get((sala["id"], h))
            if dueno is not None:
                estado = "propia" if usuario_id is not None and dueno == usuario_id else "ocupado"
            elif reglas.momento(dia, h) < ahora:
                estado = "pasado"
            else:
                estado = "libre"
                libres += 1
            bloques.append({"hora_inicio": hora_txt(h), "hora_fin": hora_txt(h + 1), "estado": estado})
        resultado.append(
            {
                "id": sala["id"],
                "nombre": sala["nombre"],
                "capacidad": sala["capacidad"],
                "ubicacion": sala["ubicacion"],
                "bloques_libres": libres,
                "bloques": bloques,
            }
        )

    return {
        "fecha": dia,
        "ahora": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "horas": [hora_txt(h) for h in range(HORA_APERTURA, HORA_CIERRE)],
        "salas": resultado,
    }
