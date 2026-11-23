"""Inicio de sesión simulado y control de roles (RNF03).

No hay contraseñas ni cuenta institucional: el frontend envía el id del
usuario elegido en la cabecera `X-Usuario-Id` y el backend comprueba que
exista y que su rol tenga permiso para la ruta.
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import g, request

from ..db import get_db
from ..errores import DatosInvalidos, NoAutenticado, SinPermiso
from ..servicio import usuarios as srv_usuarios

CABECERA = "X-Usuario-Id"


def usuario_actual() -> dict[str, Any]:
    if "usuario" in g:
        return g.usuario
    valor = request.headers.get(CABECERA, "").strip()
    if not valor.isdigit():
        raise NoAutenticado("Inicia sesión para continuar.", "SESION_REQUERIDA")
    usuario = get_db().execute("SELECT * FROM usuario WHERE id = ?", (int(valor),)).fetchone()
    if usuario is None:
        raise NoAutenticado("La sesión no es válida. Vuelve a iniciar sesión.", "SESION_INVALIDA")
    g.usuario = srv_usuarios.obtener_usuario(get_db(), usuario["id"])
    return g.usuario


def requiere_rol(*roles: str) -> Callable:
    """Decorador: exige sesión y, si se indican, uno de los roles."""

    def decorador(vista: Callable) -> Callable:
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if roles and usuario["rol"] not in roles:
                raise SinPermiso("Tu rol no tiene permiso para esta acción.", "ROL_SIN_PERMISO")
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def cuerpo_json() -> dict[str, Any]:
    datos = request.get_json(silent=True)
    if datos is None:
        if request.data:
            raise DatosInvalidos("El cuerpo debe ser JSON válido.", "JSON_INVALIDO")
        return {}
    if not isinstance(datos, dict):
        raise DatosInvalidos("El cuerpo debe ser un objeto JSON.", "JSON_INVALIDO")
    return datos


def parametro_entero(nombre: str) -> int | None:
    valor = request.args.get(nombre, "").strip()
    if not valor:
        return None
    if not valor.isdigit():
        raise DatosInvalidos(f"El parámetro «{nombre}» debe ser un número.", "PARAMETRO_INVALIDO", campo=nombre)
    return int(valor)
