"""Backend del Sistema de Reservas de Salas de Estudio.

Arquitectura en capas (cada capa solo habla con la siguiente):

    api/        Controlador · rutas Flask y API JSON
    servicio/   Negocio     · reglas RN1–RN6 y casos de uso
    db.py       Datos       · conexión y transacciones sqlite3
    schema.sql  Persistencia · 3 tablas con restricciones
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from flask import Flask

from . import db
from .api import registrar_api
from .config import Config


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.teardown_appcontext(db.close_db)

    registrar_api(app)
    _registrar_cli(app)

    if app.config.get("AUTO_INIT_DB"):
        _inicializar_si_falta(app)
    return app


def _inicializar_si_falta(app: Flask) -> None:
    ruta = app.config["DATABASE"]
    if ruta == ":memory:":
        return
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    con = db.conectar(ruta)
    try:
        if not db.esquema_existe(con):
            from .datos_ficticios import cargar

            db.crear_esquema(con)
            with app.app_context():
                from .reloj import ahora

                resumen = cargar(con, ahora())
            app.logger.info("Base creada con datos ficticios: %s", resumen)
    finally:
        con.close()


def _registrar_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    @click.option("--vacia", is_flag=True, help="Crea las tablas sin datos ficticios.")
    def init_db(vacia: bool) -> None:
        """Borra y vuelve a crear la base de datos."""
        from .datos_ficticios import cargar
        from .reloj import ahora

        ruta = app.config["DATABASE"]
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        con = db.conectar(ruta)
        try:
            db.borrar_todo(con)
            db.crear_esquema(con)
            if vacia:
                click.echo(f"Base vacía creada en {ruta}")
            else:
                resumen = cargar(con, ahora())
                click.echo(f"Base creada en {ruta} con datos ficticios: {resumen}")
        finally:
            con.close()
