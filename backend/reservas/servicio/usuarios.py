"""RF02 · Registrar usuarios con su rol (inicio de sesión simulado)."""
from __future__ import annotations

import re
import sqlite3
from typing import Any

from ..db import transaccion
from ..errores import DatosInvalidos, NoEncontrado, ReglaIncumplida
from .reglas import ROLES

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _a_dict(fila: sqlite3.Row) -> dict[str, Any]:
    return {"id": fila["id"], "nombre": fila["nombre"], "correo": fila["correo"], "rol": fila["rol"]}


def listar_usuarios(con: sqlite3.Connection, rol: str | None = None) -> list[dict[str, Any]]:
    if rol:
        filas = con.execute(
            "SELECT * FROM usuario WHERE rol = ? ORDER BY nombre COLLATE NOCASE", (rol,)
        )
    else:
        filas = con.execute("SELECT * FROM usuario ORDER BY rol, nombre COLLATE NOCASE")
    return [_a_dict(f) for f in filas]


def obtener_usuario(con: sqlite3.Connection, usuario_id: int) -> dict[str, Any]:
    fila = con.execute("SELECT * FROM usuario WHERE id = ?", (usuario_id,)).fetchone()
    if fila is None:
        raise NoEncontrado("El usuario no existe.", "USUARIO_NO_EXISTE")
    return _a_dict(fila)


def buscar_por_correo(con: sqlite3.Connection, correo: str) -> dict[str, Any] | None:
    fila = con.execute(
        "SELECT * FROM usuario WHERE correo = ? COLLATE NOCASE", (correo.strip(),)
    ).fetchone()
    return _a_dict(fila) if fila else None


def _validar_campos(datos: dict[str, Any], parcial: bool) -> dict[str, Any]:
    limpios: dict[str, Any] = {}
    if "nombre" in datos or not parcial:
        nombre = str(datos.get("nombre") or "").strip()
        if not nombre:
            raise DatosInvalidos("Escribe el nombre.", "NOMBRE_REQUERIDO", campo="nombre")
        if len(nombre) > 80:
            raise DatosInvalidos("El nombre admite hasta 80 caracteres.", "NOMBRE_LARGO", campo="nombre")
        limpios["nombre"] = nombre
    if "correo" in datos or not parcial:
        correo = str(datos.get("correo") or "").strip().lower()
        if not PATRON_CORREO.match(correo):
            raise DatosInvalidos(
                "Escribe un correo válido, por ejemplo nombre@dominio.cl.", "CORREO_INVALIDO", campo="correo"
            )
        limpios["correo"] = correo
    if "rol" in datos or not parcial:
        rol = str(datos.get("rol") or "").strip().lower()
        if rol not in ROLES:
            raise DatosInvalidos(
                "El rol debe ser «estudiante» o «biblioteca».", "ROL_INVALIDO", campo="rol"
            )
        limpios["rol"] = rol
    return limpios


def crear_usuario(con: sqlite3.Connection, datos: dict[str, Any]) -> dict[str, Any]:
    campos = _validar_campos(datos, parcial=False)
    try:
        with transaccion(con):
            cur = con.execute(
                "INSERT INTO usuario (nombre, correo, rol) VALUES (?, ?, ?)",
                (campos["nombre"], campos["correo"], campos["rol"]),
            )
    except sqlite3.IntegrityError:
        raise ReglaIncumplida(
            f"Ya existe un usuario con el correo {campos['correo']}.", "CORREO_DUPLICADO", campo="correo"
        ) from None
    return obtener_usuario(con, cur.lastrowid)


def actualizar_usuario(con: sqlite3.Connection, usuario_id: int, datos: dict[str, Any]) -> dict[str, Any]:
    actual = obtener_usuario(con, usuario_id)
    campos = _validar_campos(datos, parcial=True)
    if not campos:
        raise DatosInvalidos("No hay cambios que guardar.", "SIN_CAMBIOS")
    if campos.get("rol") == "biblioteca" and actual["rol"] == "estudiante":
        vigentes = con.execute(
            "SELECT COUNT(*) FROM reserva WHERE usuario_id = ? AND estado IN ('activa','confirmada')",
            (usuario_id,),
        ).fetchone()[0]
        if vigentes:
            raise ReglaIncumplida(
                "El estudiante tiene reservas vigentes; espera a que terminen antes de cambiar su rol.",
                "USUARIO_CON_RESERVAS",
                campo="rol",
            )
    asignaciones = ", ".join(f"{k} = ?" for k in campos)
    try:
        with transaccion(con):
            con.execute(f"UPDATE usuario SET {asignaciones} WHERE id = ?", (*campos.values(), usuario_id))
    except sqlite3.IntegrityError:
        raise ReglaIncumplida(
            f"Ya existe un usuario con el correo {campos.get('correo')}.", "CORREO_DUPLICADO", campo="correo"
        ) from None
    return obtener_usuario(con, usuario_id)


def eliminar_usuario(con: sqlite3.Connection, usuario_id: int) -> None:
    obtener_usuario(con, usuario_id)
    vigentes = con.execute(
        "SELECT COUNT(*) FROM reserva WHERE usuario_id = ? AND estado IN ('activa','confirmada')",
        (usuario_id,),
    ).fetchone()[0]
    if vigentes:
        raise ReglaIncumplida(
            "El usuario tiene reservas vigentes; no se puede eliminar hasta que sean canceladas o finalizadas.",
            "USUARIO_CON_RESERVAS",
        )
    with transaccion(con):
        con.execute(
            "DELETE FROM reserva WHERE usuario_id = ? AND estado NOT IN ('activa','confirmada')",
            (usuario_id,),
        )
        con.execute("DELETE FROM usuario WHERE id = ?", (usuario_id,))
