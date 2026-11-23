"""Datos ficticios para demostración (RNF03: solo datos ficticios).

Crea salas, usuarios, un historial de las últimas dos semanas para que el
reporte de uso tenga contenido y algunas reservas futuras para que la
grilla de disponibilidad muestre bloques ocupados.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, datetime, timedelta

from .db import transaccion
from .servicio.reglas import HORA_APERTURA, HORA_CIERRE, hora_txt

SALAS = [
    ("Sala A", 4, "Biblioteca Central · Piso 1"),
    ("Sala B", 6, "Biblioteca Central · Piso 2"),
    ("Sala C", 8, "Biblioteca Central · Piso 2"),
    ("Sala D", 12, "Biblioteca Central · Piso 3 · Sala grupal"),
]
SALA_INACTIVA = ("Sala E", 2, "Biblioteca Central · Piso 1 · En mantención")

USUARIOS = [
    ("Paula Fernández", "biblioteca@demo.cl", "biblioteca"),
    ("Ana Muñoz", "ana.munoz@alumnos.demo.cl", "estudiante"),
    ("Benjamín Soto", "benjamin.soto@alumnos.demo.cl", "estudiante"),
    ("Camila Rojas", "camila.rojas@alumnos.demo.cl", "estudiante"),
    ("Diego Pérez", "diego.perez@alumnos.demo.cl", "estudiante"),
    ("Elena Castro", "elena.castro@alumnos.demo.cl", "estudiante"),
    ("Felipe Díaz", "felipe.diaz@alumnos.demo.cl", "estudiante"),
]

# Probabilidad de que un bloque esté reservado según la hora (horas pico al mediodía y la tarde)
DEMANDA = {8: .10, 9: .20, 10: .35, 11: .50, 12: .55, 13: .40, 14: .35,
           15: .50, 16: .55, 17: .45, 18: .30, 19: .20, 20: .10}


def _txt(m: datetime) -> str:
    return m.strftime("%Y-%m-%d %H:%M:%S")


def cargar(con: sqlite3.Connection, ahora: datetime | None = None, semilla: int = 2026) -> dict[str, int]:
    ahora = ahora or datetime.now().replace(microsecond=0)
    azar = random.Random(semilla)
    hoy = ahora.date()

    with transaccion(con):
        sala_ids = []
        for nombre, capacidad, ubicacion in SALAS:
            cur = con.execute(
                "INSERT INTO sala (nombre, capacidad, ubicacion, activa) VALUES (?, ?, ?, 1)",
                (nombre, capacidad, ubicacion),
            )
            sala_ids.append((cur.lastrowid, capacidad))
        con.execute(
            "INSERT INTO sala (nombre, capacidad, ubicacion, activa) VALUES (?, ?, ?, 0)",
            SALA_INACTIVA,
        )

        estudiantes = []
        for nombre, correo, rol in USUARIOS:
            cur = con.execute(
                "INSERT INTO usuario (nombre, correo, rol) VALUES (?, ?, ?)", (nombre, correo, rol)
            )
            if rol == "estudiante":
                estudiantes.append(cur.lastrowid)

        # --- Historial: 14 días hábiles hacia atrás ---------------------------
        historicas = 0
        dia = hoy - timedelta(days=1)
        dias_hechos = 0
        while dias_hechos < 14:
            if dia.weekday() < 5:
                historicas += _llenar_dia(con, azar, dia, sala_ids, estudiantes)
                dias_hechos += 1
            dia -= timedelta(days=1)

        # --- Reservas futuras (activas), respetando RN2 y RN4 -----------------
        futuras = _reservas_futuras(con, hoy, ahora, sala_ids, estudiantes)

    return {"salas": len(SALAS) + 1, "usuarios": len(USUARIOS),
            "historicas": historicas, "futuras": futuras}


def _llenar_dia(con, azar, dia: date, sala_ids, estudiantes) -> int:
    creadas = 0
    for sala_id, capacidad in sala_ids:
        h = HORA_APERTURA
        while h < HORA_CIERRE:
            if azar.random() >= DEMANDA[h]:
                h += 1
                continue
            duracion = 2 if (h + 2 <= HORA_CIERRE and azar.random() < .4) else 1
            inicio = datetime(dia.year, dia.month, dia.day, h)
            sorteo = azar.random()
            if sorteo < .68:
                estado = "finalizada"
                confirmada = _txt(inicio + timedelta(minutes=azar.randint(0, 14)))
            elif sorteo < .88:
                estado, confirmada = "liberada", None
            else:
                estado, confirmada = "cancelada", None
            con.execute(
                """
                INSERT INTO reserva (usuario_id, sala_id, fecha, hora_inicio, hora_fin,
                                     asistentes, estado, creada_en, confirmada_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (azar.choice(estudiantes), sala_id, dia.isoformat(), hora_txt(h),
                 hora_txt(h + duracion), azar.randint(1, capacidad), estado,
                 _txt(inicio - timedelta(days=azar.randint(1, 3), hours=azar.randint(0, 5))),
                 confirmada),
            )
            creadas += 1
            h += duracion
    return creadas


def _reservas_futuras(con, hoy: date, ahora: datetime, sala_ids, estudiantes) -> int:
    manana = hoy + timedelta(days=1)
    pasado = hoy + timedelta(days=2)
    (a, _), (b, _), (c, _), (d, _) = sala_ids[:4]
    ana, benjamin, camila, diego, elena, felipe = estudiantes[:6]
    # (usuario, sala, fecha, inicio, fin, asistentes)
    plan = [
        (ana, b, manana, 10, 12, 4),
        (benjamin, a, manana, 11, 12, 3),
        (benjamin, c, pasado, 15, 17, 6),
        (camila, a, manana, 15, 16, 2),
        (camila, d, manana, 12, 14, 10),
        (diego, c, manana, 9, 10, 5),
        (diego, b, pasado, 16, 18, 5),
        (elena, d, pasado, 11, 12, 8),
        (felipe, a, pasado, 10, 11, 4),
    ]
    # Si aún queda jornada hoy, dos reservas más tarde en el día
    siguiente = ahora.hour + 1
    if siguiente + 3 <= HORA_CIERRE:
        plan += [(elena, b, hoy, siguiente, siguiente + 1, 4),
                 (felipe, c, hoy, siguiente + 1, siguiente + 3, 5)]
    creadas = 0
    for usuario, sala, fecha, h_ini, h_fin, asistentes in plan:
        con.execute(
            """
            INSERT INTO reserva (usuario_id, sala_id, fecha, hora_inicio, hora_fin,
                                 asistentes, estado, creada_en)
            VALUES (?, ?, ?, ?, ?, ?, 'activa', ?)
            """,
            (usuario, sala, fecha.isoformat(), hora_txt(h_ini), hora_txt(h_fin), asistentes, _txt(ahora)),
        )
        creadas += 1
    return creadas
