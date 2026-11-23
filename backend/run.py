"""Levanta la API.

    python run.py

Escucha en todas las interfaces (puerto 5000), así teléfonos y otros
computadores de la misma red pueden usarla. La primera vez crea
instancia/reservas.db con datos ficticios.
"""
import os

from reservas import create_app
from reservas.red import ip_local

app = create_app()

if __name__ == "__main__":
    host, puerto = app.config["HOST"], app.config["PORT"]
    print(f"\n  API local:      http://localhost:{puerto}/api/salud")
    if host == "0.0.0.0" and (ip := ip_local()):
        print(f"  API en la red:  http://{ip}:{puerto}/api/salud")
    print()
    app.run(host=host, port=puerto, debug=os.environ.get("FLASK_DEBUG") == "1", threaded=True)
