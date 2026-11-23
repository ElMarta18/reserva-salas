"""Reglas de negocio RN1–RN6 y utilidades de fecha y hora.

Funciones puras o de solo lectura: no escriben en la base. Las operaciones
que cambian datos (crear, cancelar, confirmar, liberar) están en
`reservas.py` y usan estas reglas.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Mapping

from ..errores import DatosInvalidos

# --- Parámetros de las reglas ------------------------------------------------
HORA_APERTURA = 8            # RN2: primer bloque 08:00
HORA_CIERRE = 21             # RN2: último bloque termina 21:00
MAX_HORAS_SEGUIDAS = 2       # RN2
MAX_RESERVAS_VIGENTES = 2    # RN4
MINUTOS_CONFIRMACION = 15    # RN5

ESTADOS = ("activa", "confirmada", "cancelada", "liberada", "finalizada")
ESTADOS_QUE_OCUPAN = ("activa", "confirmada")   # solo estos cuentan para choques
ROLES = ("estudiante", "biblioteca")


# --- Fechas y horas ---------------------------------------------------------

def parse_fecha(valor: Any, campo: str = "fecha") -> date:
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if not valor:
        raise DatosInvalidos("Indica la fecha.", "FECHA_REQUERIDA", campo=campo)
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        raise DatosInvalidos(
            "La fecha debe tener el formato AAAA-MM-DD.", "FECHA_INVALIDA", campo=campo
        ) from None


def parse_hora(valor: Any, campo: str = "hora_inicio") -> int:
    """Convierte '10:00' (o 10) en 10. Los bloques empiezan en hora exacta."""
    if valor is None or valor == "":
        raise DatosInvalidos("Indica la hora.", "HORA_REQUERIDA", campo=campo)
    if isinstance(valor, int):
        hora, minutos = valor, 0
    else:
        texto = str(valor).strip()
        try:
            partes = texto.split(":")
            hora = int(partes[0])
            minutos = int(partes[1]) if len(partes) > 1 else 0
        except (ValueError, IndexError):
            raise DatosInvalidos(
                "La hora debe tener el formato HH:00.", "HORA_INVALIDA", campo=campo
            ) from None
    if minutos != 0:
        raise DatosInvalidos(
            "Los bloques son de 1 hora y empiezan en hora exacta (por ejemplo 10:00).",
            "RN2_BLOQUE",
            campo=campo,
        )
    if not 0 <= hora <= 24:
        raise DatosInvalidos("La hora no es válida.", "HORA_INVALIDA", campo=campo)
    return hora


def hora_txt(hora: int) -> str:
    return f"{hora:02d}:00"


def momento(fecha: str | date, hora: str | int) -> datetime:
    """Fecha + hora del bloque como datetime."""
    f = parse_fecha(fecha)
    h = hora if isinstance(hora, int) else parse_hora(hora)
    return datetime(f.year, f.month, f.day) + timedelta(hours=h)


def bloques_del_dia() -> list[tuple[str, str]]:
    return [(hora_txt(h), hora_txt(h + 1)) for h in range(HORA_APERTURA, HORA_CIERRE)]


# --- RN1 · Sin traslapes ------------------------------------------------------

def hay_choque(
    con: sqlite3.Connection,
    sala_id: int,
    fecha: str,
    inicio: str,
    fin: str,
    excluir_id: int | None = None,
) -> bool:
    """Dos reservas chocan si inicio < fin_otro y fin > inicio_otro.

    Un bloque que termina a las 11:00 no choca con uno que empieza a las 11:00.
    """
    sql = """
        SELECT COUNT(*) FROM reserva
        WHERE sala_id = ? AND fecha = ?
          AND estado IN ('activa', 'confirmada')
          AND hora_inicio < ? AND hora_fin > ?
    """
    params: list[Any] = [sala_id, fecha, fin, inicio]
    if excluir_id is not None:
        sql += " AND id <> ?"
        params.append(excluir_id)
    fila = con.execute(sql, params).fetchone()
    return fila[0] > 0


def choque_propio(
    con: sqlite3.Connection, usuario_id: int, fecha: str, inicio: str, fin: str
) -> bool:
    """El estudiante ya tiene otra reserva (en cualquier sala) en ese horario."""
    fila = con.execute(
        """
        SELECT COUNT(*) FROM reserva
        WHERE usuario_id = ? AND fecha = ?
          AND estado IN ('activa', 'confirmada')
          AND hora_inicio < ? AND hora_fin > ?
        """,
        (usuario_id, fecha, fin, inicio),
    ).fetchone()
    return fila[0] > 0


# --- RN2 · Bloques de 1 hora, máximo 2 horas seguidas -------------------------

def validar_bloque(hora_inicio: int, hora_fin: int) -> str | None:
    """Devuelve el motivo del rechazo o None si el bloque es válido."""
    if hora_fin <= hora_inicio:
        return "La hora de término debe ser posterior a la de inicio."
    if hora_inicio < HORA_APERTURA or hora_fin > HORA_CIERRE:
        return (
            f"Las salas se reservan entre las {hora_txt(HORA_APERTURA)} "
            f"y las {hora_txt(HORA_CIERRE)}."
        )
    if hora_fin - hora_inicio > MAX_HORAS_SEGUIDAS:
        return f"Puedes reservar como máximo {MAX_HORAS_SEGUIDAS} horas seguidas."
    return None


def horas_seguidas_con_propias(
    con: sqlite3.Connection, usuario_id: int, fecha: str, hora_inicio: int, hora_fin: int
) -> int:
    """Largo del tramo continuo que formaría la nueva reserva junto con las
    reservas vigentes del mismo estudiante ese día (en cualquier sala).

    Evita encadenar 10–12 y 12–14 para sumar 4 horas seguidas.
    """
    filas = con.execute(
        """
        SELECT hora_inicio, hora_fin FROM reserva
        WHERE usuario_id = ? AND fecha = ? AND estado IN ('activa', 'confirmada')
        """,
        (usuario_id, fecha),
    ).fetchall()
    ocupadas = set(range(hora_inicio, hora_fin))
    for fila in filas:
        ocupadas.update(range(parse_hora(fila["hora_inicio"]), parse_hora(fila["hora_fin"])))
    desde = hora_inicio
    while desde - 1 in ocupadas:
        desde -= 1
    hasta = hora_fin
    while hasta in ocupadas:
        hasta += 1
    return hasta - desde


# --- RN3 · Capacidad ----------------------------------------------------------

def excede_capacidad(sala: Mapping[str, Any], asistentes: int) -> bool:
    return asistentes > int(sala["capacidad"])


# --- RN4 · Límite por estudiante ------------------------------------------------

def contar_vigentes(con: sqlite3.Connection, usuario_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) FROM reserva WHERE usuario_id = ? AND estado IN ('activa', 'confirmada')",
        (usuario_id,),
    ).fetchone()
    return fila[0]


# --- RN5 · Confirmación y RN6 · Cancelación ----------------------------------

def ventana_confirmacion(reserva: Mapping[str, Any]) -> tuple[datetime, datetime]:
    inicio = momento(reserva["fecha"], reserva["hora_inicio"])
    return inicio, inicio + timedelta(minutes=MINUTOS_CONFIRMACION)


def puede_confirmar(reserva: Mapping[str, Any], ahora: datetime) -> bool:
    if reserva["estado"] != "activa":
        return False
    desde, hasta = ventana_confirmacion(reserva)
    return desde <= ahora <= hasta


def puede_cancelar(reserva: Mapping[str, Any], ahora: datetime) -> bool:
    if reserva["estado"] != "activa":
        return False
    return ahora < momento(reserva["fecha"], reserva["hora_inicio"])
