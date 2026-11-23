"""RNF04 · Respuesta en menos de 2 s con 1.000 reservas de prueba.
RNF01 · 0 reservas superpuestas después de la carga.
"""
from __future__ import annotations

import random
import time
from datetime import date, datetime, timedelta

from reservas import db
from reservas.servicio import reservas as srv

from conftest import ANA, PAULA, como

TOTAL = 1000


def _cargar_lote(ruta) -> int:
    """Inserta 1.000 reservas en 40 días pasando por las validaciones del servicio."""
    con = db.conectar(ruta)
    azar = random.Random(7)
    with db.transaccion(con):
        # más estudiantes para no chocar con RN4 (máximo 2 vigentes por persona)
        for i in range(600):
            con.execute(
                "INSERT INTO usuario (nombre, correo, rol) VALUES (?, ?, 'estudiante')",
                (f"Estudiante {i}", f"e{i}@carga.demo.cl"),
            )
    estudiantes = [f[0] for f in con.execute("SELECT id FROM usuario WHERE rol = 'estudiante'")]
    ahora = datetime(2026, 11, 24, 7, 0)
    creadas, intentos = 0, 0
    while creadas < TOTAL:
        intentos += 1
        dia = date(2026, 11, 24) + timedelta(days=azar.randrange(40))
        h = azar.randrange(8, 21)
        try:
            srv.crear_reserva(
                con,
                estudiantes[creadas // 2 % len(estudiantes)],
                {"sala_id": azar.randint(1, 3), "fecha": dia.isoformat(), "hora_inicio": f"{h:02d}:00",
                 "duracion": 1, "asistentes": 2},
                ahora,
            )
            creadas += 1
        except Exception:
            continue
    con.close()
    return intentos


def test_RNF04_y_RNF01_con_1000_reservas(app, cliente):
    _cargar_lote(app.config["DATABASE"])

    con = db.conectar(app.config["DATABASE"])
    assert con.execute("SELECT COUNT(*) FROM reserva").fetchone()[0] == TOTAL
    superpuestas = con.execute(
        """
        SELECT COUNT(*) FROM reserva a JOIN reserva b
          ON a.sala_id = b.sala_id AND a.fecha = b.fecha AND a.id < b.id
         AND a.hora_inicio < b.hora_fin AND a.hora_fin > b.hora_inicio
        WHERE a.estado IN ('activa','confirmada') AND b.estado IN ('activa','confirmada')
        """
    ).fetchone()[0]
    con.close()
    assert superpuestas == 0

    consultas = [
        ("/api/disponibilidad?fecha=2026-11-30", ANA),
        ("/api/reservas/mias", ANA),
        ("/api/reporte?desde=2026-11-24&hasta=2027-01-03", PAULA),
        ("/api/reporte/horas-pico?desde=2026-11-24&hasta=2027-01-03", PAULA),
    ]
    for ruta, usuario in consultas:
        inicio = time.perf_counter()
        r = cliente.get(ruta, headers=como(usuario))
        duracion = time.perf_counter() - inicio
        assert r.status_code == 200, ruta
        assert duracion < 2.0, f"{ruta} tardó {duracion:.2f} s"
