"""Datos y utilidades compartidas por las pruebas.

Escenario base (fecha de la presentación: martes 24-11-2026):
  · Sala A (4 personas) · Sala B (6) · Sala C (8)
  · Estudiantes: Ana (id 1) y Beto (id 2) · Biblioteca: Paula (id 3)
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reservas import create_app, db  # noqa: E402
from reservas.servicio import reservas as srv  # noqa: E402

FECHA = "2026-11-24"
AHORA = datetime(2026, 11, 24, 8, 0)          # el día empieza: todo está en el futuro
SALA_A, SALA_B, SALA_C = 1, 2, 3
ANA, BETO, PAULA = 1, 2, 3


def poblar(con) -> None:
    con.executescript(
        """
        INSERT INTO sala (nombre, capacidad, ubicacion) VALUES
            ('Sala A', 4, 'Piso 1'), ('Sala B', 6, 'Piso 2'), ('Sala C', 8, 'Piso 2');
        INSERT INTO usuario (nombre, correo, rol) VALUES
            ('Ana', 'ana@demo.cl', 'estudiante'),
            ('Beto', 'beto@demo.cl', 'estudiante'),
            ('Paula', 'paula@demo.cl', 'biblioteca');
        """
    )


@pytest.fixture
def con():
    conexion = db.conectar(":memory:")
    db.crear_esquema(conexion)
    poblar(conexion)
    yield conexion
    conexion.close()


def reservar(con, usuario=ANA, sala=SALA_A, inicio="10:00", fin="11:00",
             asistentes=2, fecha=FECHA, ahora=AHORA):
    return srv.crear_reserva(
        con,
        usuario,
        {"sala_id": sala, "fecha": fecha, "hora_inicio": inicio, "hora_fin": fin, "asistentes": asistentes},
        ahora,
    )


def contar(con, **filtros) -> int:
    sql = "SELECT COUNT(*) FROM reserva"
    if filtros:
        sql += " WHERE " + " AND ".join(f"{k} = ?" for k in filtros)
    return con.execute(sql, tuple(filtros.values())).fetchone()[0]


# --- Fixtures de la API -----------------------------------------------------

@pytest.fixture
def app(tmp_path):
    ruta = tmp_path / "prueba.db"
    aplicacion = create_app(
        {
            "TESTING": True,
            "DATABASE": str(ruta),
            "AUTO_INIT_DB": False,
            "AHORA_FIJA": AHORA,
            "CORS_ORIGINS": ["http://localhost:5500"],
        }
    )
    conexion = db.conectar(ruta)
    db.crear_esquema(conexion)
    poblar(conexion)
    conexion.close()
    return aplicacion


@pytest.fixture
def cliente(app):
    return app.test_client()


def como(usuario_id: int) -> dict[str, str]:
    return {"X-Usuario-Id": str(usuario_id)}
