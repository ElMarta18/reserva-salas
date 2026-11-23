"""Capa de controlador: API JSON bajo /api.

· Antes de cada petición se ejecuta RF07 (liberar reservas no confirmadas).
· Los errores de negocio se devuelven como {"error": {codigo, mensaje, ...}}.
· CORS permite que el frontend, servido aparte, consuma la API.
"""
from __future__ import annotations

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from .. import reloj
from ..db import get_db
from ..errores import ErrorNegocio
from ..red import origen_permitido
from ..servicio import reservas as srv_reservas
from . import auth, disponibilidad, reportes, reservas, salas, usuarios

BLUEPRINTS = (auth.bp, salas.bp, usuarios.bp, disponibilidad.bp, reservas.bp, reportes.bp)


def registrar_api(app: Flask) -> None:
    for bp in BLUEPRINTS:
        app.register_blueprint(bp, url_prefix="/api")

    @app.get("/")
    def indice():
        return jsonify(
            {
                "nombre": "API · Sistema de Reservas de Salas de Estudio",
                "version": "1.0",
                "salud": "/api/salud",
                "nota": "El frontend se sirve por separado (carpeta frontend/).",
            }
        )

    @app.before_request
    def liberar_vencidas():
        # RF07: antes de atender cada consulta, liberar y finalizar lo que corresponda.
        if request.method == "OPTIONS" or not request.path.startswith("/api"):
            return None
        srv_reservas.actualizar_estados(get_db(), reloj.ahora())
        return None

    @app.after_request
    def cors(respuesta):
        origen = request.headers.get("Origin", "")
        if origen_permitido(origen, app.config.get("CORS_ORIGINS", []), app.config.get("CORS_RED_LOCAL", True)):
            respuesta.headers["Access-Control-Allow-Origin"] = origen
            respuesta.headers["Vary"] = "Origin"
            respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Usuario-Id"
            respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            respuesta.headers["Access-Control-Max-Age"] = "600"
        return respuesta

    @app.errorhandler(ErrorNegocio)
    def error_negocio(exc: ErrorNegocio):
        return jsonify(exc.a_dict()), exc.status

    @app.errorhandler(HTTPException)
    def error_http(exc: HTTPException):
        mensajes = {
            404: "La ruta no existe.",
            405: "Método no permitido en esta ruta.",
            400: "La petición no es válida.",
        }
        cuerpo = {"error": {"codigo": f"HTTP_{exc.code}", "mensaje": mensajes.get(exc.code, exc.description)}}
        return jsonify(cuerpo), exc.code

    @app.errorhandler(Exception)
    def error_inesperado(exc: Exception):
        app.logger.exception("Error no controlado")
        cuerpo = {"error": {"codigo": "ERROR_INTERNO", "mensaje": "Ocurrió un error inesperado en el servidor."}}
        return jsonify(cuerpo), 500
