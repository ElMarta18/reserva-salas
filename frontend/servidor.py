"""Servidor del frontend (sin dependencias).

    python servidor.py            # puerto 5500
    python servidor.py 8080       # otro puerto

Sirve esta carpeta a todos los equipos de la red y desactiva la caché,
para que los teléfonos vean siempre la última versión de los archivos.
"""
from __future__ import annotations

import socket
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CARPETA = Path(__file__).resolve().parent


class SinCache(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".webmanifest": "application/manifest+json",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, formato: str, *args) -> None:  # menos ruido en la consola
        if len(args) > 1 and str(args[1]).startswith(("4", "5")):
            super().log_message(formato, *args)


def ip_local() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            return None if ip.startswith("127.") else ip
    except OSError:
        return None


def crear_servidor(puerto: int = 5500, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    manejador = partial(SinCache, directory=str(CARPETA))
    return ThreadingHTTPServer((host, puerto), manejador)


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
    servidor = crear_servidor(puerto)
    print(f"\n  Frontend en este computador:  http://localhost:{puerto}")
    if ip := ip_local():
        print(f"  Frontend en la red (teléfono): http://{ip}:{puerto}")
    print("  Ctrl+C para detener\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
