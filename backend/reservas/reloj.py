"""Hora actual del sistema.

La capa de negocio recibe `ahora` como parámetro, así las pruebas pueden
fijar cualquier instante. En la API la hora sale de aquí: es la hora local
del servidor, salvo que se fije con la variable RESERVAS_AHORA
(útil para demostrar la confirmación y la liberación a los 15 minutos).
"""
from __future__ import annotations

from datetime import datetime

from flask import current_app

FORMATO = "%Y-%m-%d %H:%M:%S"


def parsear(valor: str) -> datetime:
    valor = valor.strip().replace("T", " ")
    for formato in (FORMATO, "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue
    raise ValueError(f"Fecha y hora inválida: {valor!r} (usa AAAA-MM-DD HH:MM)")


def ahora() -> datetime:
    fija = current_app.config.get("AHORA_FIJA")
    if fija:
        return fija if isinstance(fija, datetime) else parsear(str(fija))
    return datetime.now().replace(microsecond=0)


def formatear(momento: datetime) -> str:
    return momento.strftime(FORMATO)
