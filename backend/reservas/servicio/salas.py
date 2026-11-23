"""RF01 · Registrar y administrar salas."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..db import transaccion
from ..errores import DatosInvalidos, NoEncontrado, ReglaIncumplida

CAPACIDAD_MAXIMA = 50


def _a_dict(fila: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": fila["id"],
        "nombre": fila["nombre"],
        "capacidad": fila["capacidad"],
        "ubicacion": fila["ubicacion"],
        "activa": bool(fila["activa"]),
    }


def listar_salas(con: sqlite3.Connection, incluir_inactivas: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM sala"
    if not incluir_inactivas:
        sql += " WHERE activa = 1"
    sql += " ORDER BY nombre COLLATE NOCASE"
    return [_a_dict(f) for f in con.execute(sql)]


def obtener_sala(con: sqlite3.Connection, sala_id: int) -> dict[str, Any]:
    fila = con.execute("SELECT * FROM sala WHERE id = ?", (sala_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("La sala no existe.", "SALA_NO_EXISTE")
    return _a_dict(fila)


def _validar_campos(datos: dict[str, Any], parcial: bool) -> dict[str, Any]:
    limpios: dict[str, Any] = {}

    if "nombre" in datos or not parcial:
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise DatosInvalidos("Escribe el nombre de la sala.", "NOMBRE_REQUERIDO", campo="nombre")
        if len(nombre) > 60:
            raise DatosInvalidos("El nombre admite hasta 60 caracteres.", "NOMBRE_LARGO", campo="nombre")
        limpios["nombre"] = nombre

    if "capacidad" in datos or not parcial:
        try:
            capacidad = int(datos.get("capacidad"))
        except (TypeError, ValueError):
            raise DatosInvalidos(
                "La capacidad debe ser un número entero.", "CAPACIDAD_INVALIDA", campo="capacidad"
            ) from None
        if not 1 <= capacidad <= CAPACIDAD_MAXIMA:
            raise DatosInvalidos(
                f"La capacidad debe estar entre 1 y {CAPACIDAD_MAXIMA} personas.",
                "CAPACIDAD_INVALIDA",
                campo="capacidad",
            )
        limpios["capacidad"] = capacidad

    if "ubicacion" in datos or not parcial:
        ubicacion = str(datos.get("ubicacion") or "").strip()
        if len(ubicacion) > 120:
            raise DatosInvalidos(
                "La ubicación admite hasta 120 caracteres.", "UBICACION_LARGA", campo="ubicacion"
            )
        limpios["ubicacion"] = ubicacion

    if "activa" in datos:
        limpios["activa"] = 1 if datos.get("activa") in (True, 1, "1", "true", "si", "sí") else 0

    return limpios


def crear_sala(con: sqlite3.Connection, datos: dict[str, Any]) -> dict[str, Any]:
    campos = _validar_campos(datos, parcial=False)
    campos.setdefault("activa", 1)
    try:
        with transaccion(con):
            cur = con.execute(
                "INSERT INTO sala (nombre, capacidad, ubicacion, activa) VALUES (?, ?, ?, ?)",
                (campos["nombre"], campos["capacidad"], campos["ubicacion"], campos["activa"]),
            )
    except sqlite3.IntegrityError:
        raise ReglaIncumplida(
            f"Ya existe una sala llamada «{campos['nombre']}».", "SALA_DUPLICADA", campo="nombre"
        ) from None
    return obtener_sala(con, cur.lastrowid)


def actualizar_sala(con: sqlite3.Connection, sala_id: int, datos: dict[str, Any]) -> dict[str, Any]:
    obtener_sala(con, sala_id)
    campos = _validar_campos(datos, parcial=True)
    if not campos:
        raise DatosInvalidos("No hay cambios que guardar.", "SIN_CAMBIOS")
    asignaciones = ", ".join(f"{k} = ?" for k in campos)
    try:
        with transaccion(con):
            con.execute(f"UPDATE sala SET {asignaciones} WHERE id = ?", (*campos.values(), sala_id))
    except sqlite3.IntegrityError:
        raise ReglaIncumplida(
            f"Ya existe una sala llamada «{campos.get('nombre')}».", "SALA_DUPLICADA", campo="nombre"
        ) from None
    return obtener_sala(con, sala_id)


def eliminar_sala(con: sqlite3.Connection, sala_id: int) -> None:
    obtener_sala(con, sala_id)
    with transaccion(con):
        con.execute("DELETE FROM reserva WHERE sala_id = ?", (sala_id,))
        con.execute("DELETE FROM sala WHERE id = ?", (sala_id,))
