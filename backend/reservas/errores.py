"""Errores de negocio.

Cada error sabe qué código HTTP le corresponde y qué decirle al usuario.
La capa de API los transforma en JSON; la capa de negocio solo los lanza.
"""
from __future__ import annotations

from typing import Any


class ErrorNegocio(Exception):
    status = 409

    def __init__(
        self,
        mensaje: str,
        codigo: str = "REGLA",
        *,
        campo: str | None = None,
        sugerencias: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.campo = campo
        self.sugerencias = sugerencias or {}

    def a_dict(self) -> dict[str, Any]:
        cuerpo: dict[str, Any] = {"codigo": self.codigo, "mensaje": self.mensaje}
        if self.campo:
            cuerpo["campo"] = self.campo
        if self.sugerencias:
            cuerpo["sugerencias"] = self.sugerencias
        return {"error": cuerpo}


class ReglaIncumplida(ErrorNegocio):
    """Una regla de negocio (RN1–RN6) rechazó la operación."""
    status = 409


class DatosInvalidos(ErrorNegocio):
    """Faltan datos o vienen con un formato incorrecto."""
    status = 400


class NoEncontrado(ErrorNegocio):
    status = 404


class NoAutenticado(ErrorNegocio):
    status = 401


class SinPermiso(ErrorNegocio):
    status = 403
