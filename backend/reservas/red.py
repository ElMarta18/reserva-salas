"""Utilidades de red: IP local del computador y orígenes permitidos por CORS."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


def ip_local() -> str | None:
    """IP de este computador en la red Wi-Fi / LAN (la que usan los teléfonos)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))   # no envía nada: solo elige la interfaz de salida
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        return None if ip.startswith("127.") else ip
    except OSError:
        return None


def es_origen_de_red_local(origen: str) -> bool:
    """True si el origen (p. ej. http://192.168.1.20:5500) pertenece a la red local."""
    try:
        host = urlsplit(origen).hostname or ""
    except ValueError:
        return False
    if host in ("localhost",) or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def origen_permitido(origen: str, permitidos: list[str], red_local: bool) -> bool:
    if not origen:
        return False
    if "*" in permitidos or origen in permitidos:
        return True
    return red_local and es_origen_de_red_local(origen)
