"""Configuración del backend. Todo se puede cambiar con variables de entorno."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # Archivo SQLite
    DATABASE = os.environ.get("RESERVAS_DB", str(BASE_DIR / "instancia" / "reservas.db"))

    # Interfaz y puerto donde escucha la API.
    # 0.0.0.0 = acepta conexiones de otros equipos de la red (teléfonos, otros PC).
    # Usa 127.0.0.1 para que solo funcione en este computador.
    HOST = os.environ.get("RESERVAS_HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))

    # Orígenes extra del frontend que pueden llamar a la API (separados por coma; "*" = cualquiera)
    CORS_ORIGINS = [o.strip() for o in os.environ.get("RESERVAS_CORS", "").split(",") if o.strip()]

    # Permite automáticamente cualquier origen de la red local
    # (localhost, 127.x, 10.x, 172.16–31.x, 192.168.x y nombres .local)
    CORS_RED_LOCAL = os.environ.get("RESERVAS_CORS_RED_LOCAL", "1") == "1"

    # Fija la hora del sistema para demostraciones, p. ej. "2026-11-24 10:10"
    AHORA_FIJA = os.environ.get("RESERVAS_AHORA") or None

    # Crea la base con datos ficticios si el archivo no existe
    AUTO_INIT_DB = os.environ.get("RESERVAS_AUTO_INIT", "1") == "1"

    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
