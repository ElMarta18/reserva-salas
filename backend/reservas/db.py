"""Capa de acceso a datos: conexión a SQLite, esquema y transacciones.

Las funciones de este módulo no dependen de Flask salvo `get_db` y
`close_db`, que guardan una conexión por petición en `flask.g`.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from flask import current_app, g

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def conectar(ruta: str | Path) -> sqlite3.Connection:
    """Abre una conexión en modo autocommit con claves foráneas activas.

    Las transacciones se controlan de forma explícita con `transaccion()`.
    """
    con = sqlite3.connect(str(ruta), isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def crear_esquema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def esquema_existe(con: sqlite3.Connection) -> bool:
    fila = con.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'reserva'"
    ).fetchone()
    return fila[0] > 0


def borrar_todo(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        DROP TRIGGER IF EXISTS reserva_sin_traslape;
        DROP TABLE IF EXISTS reserva;
        DROP TABLE IF EXISTS sala;
        DROP TABLE IF EXISTS usuario;
        """
    )


@contextmanager
def transaccion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transacción de escritura exclusiva.

    `BEGIN IMMEDIATE` toma el bloqueo de escritura antes de validar, así dos
    peticiones simultáneas no pueden pasar la validación de choques a la vez.
    """
    if con.in_transaction:
        # Ya hay una transacción abierta (llamada anidada): se reutiliza.
        yield con
        return
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")


# --- Integración con Flask -------------------------------------------------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    con = g.pop("db", None)
    if con is not None:
        con.close()
