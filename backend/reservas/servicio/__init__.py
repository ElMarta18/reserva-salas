"""Capa de negocio: reglas RN1–RN6 y casos de uso.

No depende de Flask: cada función recibe una conexión SQLite y, cuando
importa la hora, el instante `ahora`. Así se prueba sin levantar el servidor.
"""
from . import disponibilidad, reglas, reportes, reservas, salas, usuarios

__all__ = ["disponibilidad", "reglas", "reportes", "reservas", "salas", "usuarios"]
