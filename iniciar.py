"""Inicia backend y frontend con un solo comando y muestra cómo abrirlo en el teléfono.

    python iniciar.py

Requiere haber instalado backend/requirements.txt en el Python con que se ejecuta.
Los dos servidores siguen siendo independientes: la API corre en el puerto 5000
y el frontend en el 5500.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "frontend"))

from servidor import crear_servidor, ip_local  # noqa: E402

PUERTO_API = int(os.environ.get("PORT", "5000"))
PUERTO_WEB = int(os.environ.get("PUERTO_WEB", "5500"))


def mostrar_qr(url: str) -> None:
    try:
        import qrcode
    except ImportError:
        print("  (Instala 'qrcode' con pip para ver aquí un código QR de la dirección)")
        return
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    try:
        qr.print_ascii(invert=True)
        print("  Escanea el código con la cámara del teléfono.")
    except UnicodeEncodeError:
        print("  (Esta consola no puede dibujar el código QR; escribe la dirección en el teléfono)")


def main() -> None:
    try:
        import flask  # noqa: F401
    except ImportError:
        sys.exit(
            "Falta Flask en este Python. Activa el entorno e instala las dependencias:\n"
            "  python -m pip install -r backend/requirements.txt"
        )

    api = subprocess.Popen([sys.executable, "run.py"], cwd=RAIZ / "backend")
    web = crear_servidor(PUERTO_WEB)
    threading.Thread(target=web.serve_forever, daemon=True).start()
    time.sleep(1.5)

    ip = ip_local()
    print("\n" + "=" * 60)
    print("  Sistema de Reservas de Salas de Estudio")
    print("=" * 60)
    print(f"  En este computador:   http://localhost:{PUERTO_WEB}")
    if ip:
        url = f"http://{ip}:{PUERTO_WEB}"
        print(f"  Teléfono / otro PC:   {url}")
        print("  (deben estar conectados a la misma red Wi-Fi)\n")
        mostrar_qr(url)
    else:
        print("  No se detectó una red local: solo funcionará en este computador.")
    print("\n  Ctrl+C para detener los dos servidores.\n")

    try:
        while api.poll() is None:
            time.sleep(0.5)
        print("La API se detuvo. Revisa el error de arriba.")
    except KeyboardInterrupt:
        print("\nDeteniendo…")
    finally:
        web.shutdown()
        if api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api.kill()


if __name__ == "__main__":
    main()
