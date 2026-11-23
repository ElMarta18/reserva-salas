"""Ciclo de vida de una reserva.

RF04 crear (valida RN1–RN4) · RF05 cancelar (RN6) · RF06 confirmar (RN5)
RF07 liberar automáticamente · RF08 «Mis reservas».

Estados: activa → confirmada → finalizada
         activa → cancelada   (el titular, antes del inicio)
         activa → liberada    (sin confirmar a inicio + 15 min)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from ..db import transaccion
from ..errores import DatosInvalidos, NoEncontrado, ReglaIncumplida, SinPermiso
from . import reglas
from .reglas import (
    HORA_APERTURA,
    HORA_CIERRE,
    MAX_HORAS_SEGUIDAS,
    MAX_RESERVAS_VIGENTES,
    MINUTOS_CONFIRMACION,
    hora_txt,
    parse_fecha,
    parse_hora,
)

_SELECT_RESERVA = """
    SELECT r.*, s.nombre AS sala_nombre, s.ubicacion AS sala_ubicacion,
           s.capacidad AS sala_capacidad, u.nombre AS usuario_nombre
    FROM reserva r
    JOIN sala s ON s.id = r.sala_id
    JOIN usuario u ON u.id = r.usuario_id
"""


def _txt(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%d %H:%M:%S")


def a_dict(fila: sqlite3.Row, ahora: datetime | None = None) -> dict[str, Any]:
    datos = {
        "id": fila["id"],
        "usuario_id": fila["usuario_id"],
        "sala_id": fila["sala_id"],
        "fecha": fila["fecha"],
        "hora_inicio": fila["hora_inicio"],
        "hora_fin": fila["hora_fin"],
        "asistentes": fila["asistentes"],
        "estado": fila["estado"],
        "creada_en": fila["creada_en"],
        "confirmada_en": fila["confirmada_en"],
    }
    claves = fila.keys()
    if "sala_nombre" in claves:
        datos["sala"] = {
            "id": fila["sala_id"],
            "nombre": fila["sala_nombre"],
            "ubicacion": fila["sala_ubicacion"],
            "capacidad": fila["sala_capacidad"],
        }
    if "usuario_nombre" in claves:
        datos["usuario_nombre"] = fila["usuario_nombre"]
    desde, hasta = reglas.ventana_confirmacion(fila)
    datos["confirmar_desde"] = _txt(desde)
    datos["confirmar_hasta"] = _txt(hasta)
    if ahora is not None:
        datos["puede_confirmar"] = reglas.puede_confirmar(fila, ahora)
        datos["puede_cancelar"] = reglas.puede_cancelar(fila, ahora)
    return datos


# --- RF07 · Liberación automática ---------------------------------------------

def actualizar_estados(con: sqlite3.Connection, ahora: datetime) -> dict[str, int]:
    """Se ejecuta antes de atender cada petición.

    · RN5: toda reserva «activa» cuyo inicio + 15 min ya pasó queda «liberada».
    · Toda reserva «confirmada» cuyo bloque terminó queda «finalizada».
    """
    limite = ahora - timedelta(minutes=MINUTOS_CONFIRMACION)
    with transaccion(con):
        liberadas = con.execute(
            """
            UPDATE reserva SET estado = 'liberada'
            WHERE estado = 'activa'
              AND fecha <= ?
              AND (fecha || ' ' || hora_inicio || ':00') < ?
            """,
            (limite.date().isoformat(), _txt(limite)),
        ).rowcount
        finalizadas = con.execute(
            """
            UPDATE reserva SET estado = 'finalizada'
            WHERE estado = 'confirmada'
              AND fecha <= ?
              AND (fecha || ' ' || hora_fin || ':00') <= ?
            """,
            (ahora.date().isoformat(), _txt(ahora)),
        ).rowcount
    return {"liberadas": liberadas, "finalizadas": finalizadas}


# --- Consultas -----------------------------------------------------------------

def obtener_reserva(con: sqlite3.Connection, reserva_id: int) -> sqlite3.Row:
    fila = con.execute(_SELECT_RESERVA + " WHERE r.id = ?", (reserva_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("La reserva no existe.", "RESERVA_NO_EXISTE")
    return fila


def mis_reservas(con: sqlite3.Connection, usuario_id: int, ahora: datetime) -> list[dict[str, Any]]:
    filas = con.execute(
        _SELECT_RESERVA + " WHERE r.usuario_id = ? ORDER BY r.fecha DESC, r.hora_inicio DESC",
        (usuario_id,),
    ).fetchall()
    return [a_dict(f, ahora) for f in filas]


def listar_reservas(
    con: sqlite3.Connection,
    ahora: datetime,
    *,
    desde: str | None = None,
    hasta: str | None = None,
    sala_id: int | None = None,
    estado: str | None = None,
    limite: int = 500,
) -> list[dict[str, Any]]:
    condiciones, params = [], []
    if desde:
        condiciones.append("r.fecha >= ?")
        params.append(parse_fecha(desde, "desde").isoformat())
    if hasta:
        condiciones.append("r.fecha <= ?")
        params.append(parse_fecha(hasta, "hasta").isoformat())
    if sala_id:
        condiciones.append("r.sala_id = ?")
        params.append(int(sala_id))
    if estado:
        if estado not in reglas.ESTADOS:
            raise DatosInvalidos("Estado desconocido.", "ESTADO_INVALIDO", campo="estado")
        condiciones.append("r.estado = ?")
        params.append(estado)
    sql = _SELECT_RESERVA
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY r.fecha, r.hora_inicio, s.nombre LIMIT ?"
    params.append(limite)
    return [a_dict(f, ahora) for f in con.execute(sql, params)]


def bloques_libres(
    con: sqlite3.Connection,
    sala_id: int,
    fecha: str,
    ahora: datetime,
    duracion: int = 1,
    usuario_id: int | None = None,
) -> list[dict[str, str]]:
    """Inicios posibles en esa sala y fecha para una reserva de `duracion` horas.

    Si se indica `usuario_id`, también descarta los horarios en que ese
    estudiante ya tiene otra reserva vigente (en cualquier sala) y los que
    sumarían más de 2 horas seguidas con sus reservas (RN2).
    """
    ocupadas: set[int] = set()   # horas tomadas en la sala o por el estudiante
    propias: set[int] = set()    # horas tomadas por el estudiante
    for fila in con.execute(
        """
        SELECT sala_id, usuario_id, hora_inicio, hora_fin FROM reserva
        WHERE fecha = ? AND estado IN ('activa', 'confirmada')
          AND (sala_id = ? OR usuario_id = ?)
        """,
        (fecha, sala_id, usuario_id if usuario_id is not None else -1),
    ):
        horas = range(parse_hora(fila["hora_inicio"]), parse_hora(fila["hora_fin"]))
        ocupadas.update(horas)
        if fila["usuario_id"] == usuario_id:
            propias.update(horas)
    libres = []
    for h in range(HORA_APERTURA, HORA_CIERRE - duracion + 1):
        horas = set(range(h, h + duracion))
        if horas & ocupadas:
            continue
        if reglas.momento(fecha, h) < ahora:
            continue
        if propias and _tramo_continuo(propias | horas, h) > MAX_HORAS_SEGUIDAS:
            continue
        libres.append({"hora_inicio": hora_txt(h), "hora_fin": hora_txt(h + duracion)})
    return libres


def _tramo_continuo(horas: set[int], desde: int) -> int:
    inicio = fin = desde
    while inicio - 1 in horas:
        inicio -= 1
    while fin in horas:
        fin += 1
    return fin - inicio


def salas_alternativas(
    con: sqlite3.Connection, fecha: str, inicio: str, fin: str, asistentes: int, excluir_sala: int
) -> list[dict[str, Any]]:
    """Salas activas con capacidad suficiente y libres en ese horario (flujo A2)."""
    filas = con.execute(
        """
        SELECT s.id, s.nombre, s.capacidad, s.ubicacion FROM sala s
        WHERE s.activa = 1 AND s.capacidad >= ? AND s.id <> ?
          AND NOT EXISTS (
              SELECT 1 FROM reserva r
              WHERE r.sala_id = s.id AND r.fecha = ?
                AND r.estado IN ('activa', 'confirmada')
                AND r.hora_inicio < ? AND r.hora_fin > ?)
        ORDER BY s.capacidad, s.nombre
        """,
        (asistentes, excluir_sala, fecha, fin, inicio),
    ).fetchall()
    return [dict(f) for f in filas]


# --- RF04 · Crear reserva ------------------------------------------------------

def _leer_entero(valor: Any, campo: str, mensaje: str) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise DatosInvalidos(mensaje, f"{campo.upper()}_INVALIDO", campo=campo) from None
    if isinstance(valor, float) and not valor.is_integer():
        raise DatosInvalidos(mensaje, f"{campo.upper()}_INVALIDO", campo=campo)
    return numero


def crear_reserva(
    con: sqlite3.Connection, usuario_id: int, datos: dict[str, Any], ahora: datetime
) -> dict[str, Any]:
    """Valida RN1–RN4 y guarda la reserva en estado «activa»."""
    # 1 · Datos de entrada
    sala_id = _leer_entero(datos.get("sala_id"), "sala_id", "Elige una sala.")
    fecha = parse_fecha(datos.get("fecha")).isoformat()
    h_ini = parse_hora(datos.get("hora_inicio"), "hora_inicio")
    if datos.get("hora_fin") not in (None, ""):
        h_fin = parse_hora(datos.get("hora_fin"), "hora_fin")
    else:
        duracion = _leer_entero(
            datos.get("duracion", 1), "duracion", "La duración debe ser 1 o 2 horas."
        )
        h_fin = h_ini + duracion
    asistentes = _leer_entero(
        datos.get("asistentes"), "asistentes", "Indica cuántas personas asistirán."
    )
    if asistentes < 1:
        raise DatosInvalidos(
            "Debe asistir al menos una persona.", "ASISTENTES_INVALIDO", campo="asistentes"
        )

    usuario = con.execute("SELECT * FROM usuario WHERE id = ?", (usuario_id,)).fetchone()
    if usuario is None:
        raise NoEncontrado("El usuario no existe.", "USUARIO_NO_EXISTE")
    if usuario["rol"] != "estudiante":
        raise SinPermiso("Solo los estudiantes pueden reservar salas.", "SOLO_ESTUDIANTES")

    sala = con.execute("SELECT * FROM sala WHERE id = ?", (sala_id,)).fetchone()
    if sala is None:
        raise NoEncontrado("La sala no existe.", "SALA_NO_EXISTE", campo="sala_id")
    if not sala["activa"]:
        raise ReglaIncumplida(
            f"La {sala['nombre']} no está disponible para reservas.", "SALA_INACTIVA", campo="sala_id"
        )

    # 2 · RN2: bloques de 1 hora entre 08:00 y 21:00, máximo 2 horas seguidas
    motivo = reglas.validar_bloque(h_ini, h_fin)
    if motivo:
        raise ReglaIncumplida(motivo, "RN2_BLOQUE", campo="hora_fin")
    inicio, fin = hora_txt(h_ini), hora_txt(h_fin)
    if reglas.momento(fecha, h_ini) < ahora:
        raise ReglaIncumplida(
            "Ese bloque ya comenzó o ya pasó. Elige un horario futuro.",
            "BLOQUE_PASADO",
            campo="hora_inicio",
        )

    try:
        with transaccion(con):
            # 3 · RN1: sin traslapes (flujo alternativo A1)
            if reglas.hay_choque(con, sala_id, fecha, inicio, fin):
                raise ReglaIncumplida(
                    "La sala ya está reservada en ese horario.",
                    "RN1_CHOQUE",
                    campo="hora_inicio",
                    sugerencias={
                        "bloques_libres": bloques_libres(
                            con, sala_id, fecha, ahora, h_fin - h_ini, usuario_id
                        )
                    },
                )
            if reglas.choque_propio(con, usuario_id, fecha, inicio, fin):
                raise ReglaIncumplida(
                    "Ya tienes otra reserva en ese mismo horario.",
                    "RN1_CHOQUE_PROPIO",
                    campo="hora_inicio",
                )

            # 4 · RN3: capacidad (flujo alternativo A2)
            if reglas.excede_capacidad(sala, asistentes):
                raise ReglaIncumplida(
                    f"La {sala['nombre']} admite hasta {sala['capacidad']} personas "
                    f"y pediste {asistentes}.",
                    "RN3_CAPACIDAD",
                    campo="asistentes",
                    sugerencias={
                        "salas": salas_alternativas(con, fecha, inicio, fin, asistentes, sala_id)
                    },
                )

            # 5 · RN4: máximo 2 reservas vigentes (flujo alternativo A3)
            vigentes = reglas.contar_vigentes(con, usuario_id)
            if vigentes >= MAX_RESERVAS_VIGENTES:
                raise ReglaIncumplida(
                    f"Ya tienes {vigentes} reservas vigentes. Cancela o usa una antes de reservar otra.",
                    "RN4_LIMITE",
                )

            # RN2 también entre reservas propias: no encadenar más de 2 horas seguidas
            seguidas = reglas.horas_seguidas_con_propias(con, usuario_id, fecha, h_ini, h_fin)
            if seguidas > MAX_HORAS_SEGUIDAS:
                raise ReglaIncumplida(
                    f"Con tus otras reservas sumarías {seguidas} horas seguidas; "
                    f"el máximo es {MAX_HORAS_SEGUIDAS}.",
                    "RN2_HORAS_SEGUIDAS",
                    campo="hora_inicio",
                )

            # 6 · Guardar en estado «activa»
            cur = con.execute(
                """
                INSERT INTO reserva
                    (usuario_id, sala_id, fecha, hora_inicio, hora_fin, asistentes, estado, creada_en)
                VALUES (?, ?, ?, ?, ?, ?, 'activa', ?)
                """,
                (usuario_id, sala_id, fecha, inicio, fin, asistentes, _txt(ahora)),
            )
    except sqlite3.IntegrityError as exc:
        # El disparador de la base es la última defensa de RN1.
        if "RN1" in str(exc):
            raise ReglaIncumplida(
                "La sala ya está reservada en ese horario.", "RN1_CHOQUE", campo="hora_inicio"
            ) from None
        raise
    return a_dict(obtener_reserva(con, cur.lastrowid), ahora)


# --- RF05 · Cancelar (RN6) -------------------------------------------------------

def cancelar_reserva(
    con: sqlite3.Connection, reserva_id: int, usuario_id: int, ahora: datetime
) -> dict[str, Any]:
    with transaccion(con):
        reserva = obtener_reserva(con, reserva_id)
        if reserva["usuario_id"] != usuario_id:
            raise SinPermiso("Solo el titular puede cancelar esta reserva.", "RN6_TITULAR")
        if reserva["estado"] != "activa":
            raise ReglaIncumplida(
                f"La reserva está «{reserva['estado']}» y ya no se puede cancelar.", "RN6_ESTADO"
            )
        if ahora >= reglas.momento(reserva["fecha"], reserva["hora_inicio"]):
            raise ReglaIncumplida(
                "El bloque ya comenzó; solo se puede cancelar antes del inicio.", "RN6_INICIADA"
            )
        con.execute("UPDATE reserva SET estado = 'cancelada' WHERE id = ?", (reserva_id,))
    return a_dict(obtener_reserva(con, reserva_id), ahora)


# --- RF06 · Confirmar llegada (RN5) ------------------------------------------------

def confirmar_llegada(
    con: sqlite3.Connection, reserva_id: int, usuario_id: int, ahora: datetime
) -> dict[str, Any]:
    with transaccion(con):
        reserva = obtener_reserva(con, reserva_id)
        if reserva["usuario_id"] != usuario_id:
            raise SinPermiso("Solo el titular puede confirmar esta reserva.", "RN5_TITULAR")
        if reserva["estado"] == "liberada":
            raise ReglaIncumplida(
                f"La reserva se liberó porque no se confirmó en los primeros "
                f"{MINUTOS_CONFIRMACION} minutos.",
                "RN5_VENCIDA",
            )
        if reserva["estado"] != "activa":
            raise ReglaIncumplida(
                f"La reserva está «{reserva['estado']}» y no se puede confirmar.", "RN5_ESTADO"
            )
        desde, hasta = reglas.ventana_confirmacion(reserva)
        if ahora < desde:
            raise ReglaIncumplida(
                f"Aún no comienza. Podrás confirmar entre las {desde:%H:%M} y las {hasta:%H:%M} "
                f"del {desde:%d-%m-%Y}.",
                "RN5_ANTICIPADA",
            )
        if ahora > hasta:
            # Caso borde: la liberación aún no corrió; la próxima petición la marcará.
            raise ReglaIncumplida(
                f"Pasaron más de {MINUTOS_CONFIRMACION} minutos desde el inicio; la sala se liberó.",
                "RN5_VENCIDA",
            )
        con.execute(
            "UPDATE reserva SET estado = 'confirmada', confirmada_en = ? WHERE id = ?",
            (_txt(ahora), reserva_id),
        )
    return a_dict(obtener_reserva(con, reserva_id), ahora)
