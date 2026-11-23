"""Pruebas de la capa de negocio (sin levantar el servidor).

Los criterios de aceptación CA01–CA06 de la presentación están escritos como
Dado / Cuando / Entonces; el resto cubre las reglas RN1–RN6 y sus casos límite.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from reservas.errores import DatosInvalidos, NoEncontrado, ReglaIncumplida, SinPermiso
from reservas.servicio import disponibilidad as srv_disp
from reservas.servicio import reportes as srv_rep
from reservas.servicio import reservas as srv
from reservas.servicio import salas as srv_salas
from reservas.servicio import usuarios as srv_usuarios

from conftest import AHORA, ANA, BETO, FECHA, PAULA, SALA_A, SALA_B, SALA_C, contar, reservar


def a_las(hora: int, minuto: int = 0, segundo: int = 0) -> datetime:
    return datetime(2026, 11, 24, hora, minuto, segundo)


def estado(con, reserva_id: int) -> str:
    return con.execute("SELECT estado FROM reserva WHERE id = ?", (reserva_id,)).fetchone()[0]


# ============================================================================
# Criterios de aceptación de la presentación
# ============================================================================

def test_CA01_choque_se_rechaza_y_no_se_guarda(con):
    # Dado: Sala A reservada de 10:00 a 11:00
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    # Cuando: otro pide 10:00 a 12:00
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, BETO, SALA_A, "10:00", "12:00")
    # Entonces: se rechaza y no se guarda nada
    assert exc.value.codigo == "RN1_CHOQUE"
    assert contar(con) == 1


def test_CA02_bloques_contiguos_no_chocan(con):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    nueva = reservar(con, BETO, SALA_A, "11:00", "12:00")
    assert nueva["estado"] == "activa"
    assert contar(con, sala_id=SALA_A) == 2


def test_CA03_capacidad_excedida_se_rechaza(con):
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_A, asistentes=5)
    assert exc.value.codigo == "RN3_CAPACIDAD"
    assert contar(con) == 0


def test_CA04_cancelar_deja_el_bloque_libre(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    cancelada = srv.cancelar_reserva(con, r["id"], ANA, a_las(9))
    assert cancelada["estado"] == "cancelada"
    # el bloque vuelve a estar libre: otra persona puede reservarlo
    assert reservar(con, BETO, SALA_A, "10:00", "11:00", ahora=a_las(9))["estado"] == "activa"


def test_CA05_confirmar_a_las_10_10(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    confirmada = srv.confirmar_llegada(con, r["id"], ANA, a_las(10, 10))
    assert confirmada["estado"] == "confirmada"
    assert confirmada["confirmada_en"] == "2026-11-24 10:10:00"


def test_CA06_sin_confirmar_a_las_10_16_se_libera(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    srv.actualizar_estados(con, a_las(10, 16))
    assert estado(con, r["id"]) == "liberada"
    # y el bloque se ve libre (aunque ya pasó su hora de inicio, la sala no figura ocupada)
    sala_a = srv_disp.disponibilidad(con, FECHA, a_las(10, 16))["salas"][0]
    bloque_10 = next(b for b in sala_a["bloques"] if b["hora_inicio"] == "10:00")
    assert bloque_10["estado"] != "ocupado"
    assert not srv.reglas.hay_choque(con, SALA_A, FECHA, "10:00", "11:00")


# ============================================================================
# RN1 · Sin traslapes
# ============================================================================

@pytest.mark.parametrize(
    "inicio, fin, choca",
    [
        ("10:00", "11:00", True),    # idéntico
        ("09:00", "11:00", True),    # termina dentro
        ("10:00", "12:00", True),    # empieza dentro
        ("09:00", "10:00", False),   # contiguo antes
        ("11:00", "12:00", False),   # contiguo después
        ("08:00", "09:00", False),   # lejos
    ],
)
def test_RN1_condicion_de_traslape(con, inicio, fin, choca):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    assert srv.reglas.hay_choque(con, SALA_A, FECHA, inicio, fin) is choca


def test_RN1_reserva_que_envuelve_a_otra(con):
    reservar(con, ANA, SALA_B, "11:00", "12:00")
    with pytest.raises(ReglaIncumplida):
        reservar(con, BETO, SALA_B, "10:00", "12:00")


def test_RN1_canceladas_y_liberadas_no_ocupan(con):
    r1 = reservar(con, ANA, SALA_A, "10:00", "11:00")
    srv.cancelar_reserva(con, r1["id"], ANA, a_las(9))
    r2 = reservar(con, BETO, SALA_A, "12:00", "13:00")
    srv.actualizar_estados(con, a_las(12, 20))
    assert estado(con, r2["id"]) == "liberada"
    assert not srv.reglas.hay_choque(con, SALA_A, FECHA, "10:00", "11:00")
    assert not srv.reglas.hay_choque(con, SALA_A, FECHA, "12:00", "13:00")


def test_RN1_otra_sala_al_mismo_tiempo_no_choca(con):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    assert reservar(con, BETO, SALA_B, "10:00", "11:00")["estado"] == "activa"


def test_RN1_un_estudiante_no_puede_estar_en_dos_salas_a_la_vez(con):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_B, "10:00", "11:00")
    assert exc.value.codigo == "RN1_CHOQUE_PROPIO"


def test_RN1_la_base_rechaza_traslapes_aunque_se_salte_el_servicio(con):
    """RNF01: el disparador de la base es la última línea de defensa."""
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO reserva (usuario_id, sala_id, fecha, hora_inicio, hora_fin, asistentes, creada_en)"
            " VALUES (?, ?, ?, '10:00', '12:00', 2, 'x')",
            (BETO, SALA_A, FECHA),
        )


def test_A1_choque_sugiere_bloques_libres_de_esa_sala(con):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, BETO, SALA_A, "10:00", "11:00")
    sugeridos = [b["hora_inicio"] for b in exc.value.sugerencias["bloques_libres"]]
    assert "10:00" not in sugeridos
    assert {"09:00", "11:00"} <= set(sugeridos)


# ============================================================================
# RN2 · Bloques de 1 hora entre 08:00 y 21:00, máximo 2 horas seguidas
# ============================================================================

@pytest.mark.parametrize(
    "inicio, fin",
    [("07:00", "08:00"), ("20:00", "22:00"), ("10:00", "13:00"), ("11:00", "10:00")],
)
def test_RN2_bloques_invalidos(con, inicio, fin):
    with pytest.raises((ReglaIncumplida, DatosInvalidos)):
        reservar(con, ANA, SALA_A, inicio, fin)
    assert contar(con) == 0


def test_RN2_limites_validos(con):
    assert reservar(con, ANA, SALA_A, "08:00", "10:00")["estado"] == "activa"
    assert reservar(con, BETO, SALA_A, "19:00", "21:00")["estado"] == "activa"


def test_RN2_solo_horas_exactas(con):
    with pytest.raises(DatosInvalidos) as exc:
        reservar(con, ANA, SALA_A, "10:30", "11:30")
    assert exc.value.codigo == "RN2_BLOQUE"


def test_RN2_no_se_pueden_encadenar_reservas_propias(con):
    reservar(con, ANA, SALA_A, "10:00", "12:00")
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_B, "12:00", "13:00")
    assert exc.value.codigo == "RN2_HORAS_SEGUIDAS"
    # las sugerencias de horario tampoco ofrecen bloques que encadenarían más de 2 horas
    sugeridos = [b["hora_inicio"] for b in srv.bloques_libres(con, SALA_B, FECHA, AHORA, 1, ANA)]
    assert "12:00" not in sugeridos and "09:00" not in sugeridos and "13:00" in sugeridos
    # con una hora de separación sí se puede
    assert reservar(con, ANA, SALA_B, "13:00", "14:00")["estado"] == "activa"


def test_no_se_reserva_un_bloque_que_ya_empezo(con):
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_A, "10:00", "11:00", ahora=a_las(10, 5))
    assert exc.value.codigo == "BLOQUE_PASADO"


# ============================================================================
# RN3 · Capacidad
# ============================================================================

def test_RN3_capacidad_exacta_se_acepta(con):
    assert reservar(con, ANA, SALA_A, asistentes=4)["asistentes"] == 4


def test_A2_capacidad_sugiere_salas_mas_grandes_y_libres(con):
    reservar(con, BETO, SALA_B, "10:00", "11:00")      # B ocupada a esa hora
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_A, "10:00", "11:00", asistentes=5)
    sugeridas = [s["nombre"] for s in exc.value.sugerencias["salas"]]
    assert sugeridas == ["Sala C"]


def test_sala_inactiva_no_admite_reservas(con):
    srv_salas.actualizar_sala(con, SALA_C, {"activa": False})
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_C)
    assert exc.value.codigo == "SALA_INACTIVA"


# ============================================================================
# RN4 · Máximo 2 reservas vigentes
# ============================================================================

def test_RN4_tercera_reserva_se_rechaza_hasta_cancelar(con):
    r1 = reservar(con, ANA, SALA_A, "09:00", "10:00")
    reservar(con, ANA, SALA_A, "14:00", "15:00")
    with pytest.raises(ReglaIncumplida) as exc:
        reservar(con, ANA, SALA_B, "17:00", "18:00")
    assert exc.value.codigo == "RN4_LIMITE"
    srv.cancelar_reserva(con, r1["id"], ANA, AHORA)
    assert reservar(con, ANA, SALA_B, "17:00", "18:00")["estado"] == "activa"


def test_RN4_las_reservas_usadas_ya_no_cuentan(con):
    r1 = reservar(con, ANA, SALA_A, "09:00", "10:00")
    reservar(con, ANA, SALA_A, "14:00", "15:00")
    srv.confirmar_llegada(con, r1["id"], ANA, a_las(9, 5))
    srv.actualizar_estados(con, a_las(10, 0))           # el bloque terminó
    assert estado(con, r1["id"]) == "finalizada"
    assert reservar(con, ANA, SALA_B, "17:00", "18:00", ahora=a_las(10))["estado"] == "activa"


def test_solo_estudiantes_reservan(con):
    with pytest.raises(SinPermiso):
        reservar(con, PAULA, SALA_A)


# ============================================================================
# RN5 · Confirmación entre el inicio y 15 minutos después
# ============================================================================

def test_RN5_no_se_confirma_antes_del_inicio(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    with pytest.raises(ReglaIncumplida) as exc:
        srv.confirmar_llegada(con, r["id"], ANA, a_las(9, 59))
    assert exc.value.codigo == "RN5_ANTICIPADA"


def test_RN5_limite_exacto_de_15_minutos(con):
    r1 = reservar(con, ANA, SALA_A, "10:00", "11:00")
    r2 = reservar(con, BETO, SALA_B, "10:00", "11:00")
    srv.actualizar_estados(con, a_las(10, 15))
    assert estado(con, r1["id"]) == "activa"             # 10:15:00 aún dentro
    assert srv.confirmar_llegada(con, r1["id"], ANA, a_las(10, 15))["estado"] == "confirmada"
    srv.actualizar_estados(con, a_las(10, 15, 1))
    assert estado(con, r2["id"]) == "liberada"           # 10:15:01 ya vencida


def test_RN5_confirmar_una_reserva_liberada_explica_el_motivo(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    srv.actualizar_estados(con, a_las(10, 30))
    with pytest.raises(ReglaIncumplida) as exc:
        srv.confirmar_llegada(con, r["id"], ANA, a_las(10, 30))
    assert exc.value.codigo == "RN5_VENCIDA"


def test_confirmada_pasa_a_finalizada_al_terminar(con):
    r = reservar(con, ANA, SALA_A, "10:00", "12:00")
    srv.confirmar_llegada(con, r["id"], ANA, a_las(10, 1))
    srv.actualizar_estados(con, a_las(11, 59))
    assert estado(con, r["id"]) == "confirmada"
    srv.actualizar_estados(con, a_las(12, 0))
    assert estado(con, r["id"]) == "finalizada"


# ============================================================================
# RN6 · Cancelación: solo el titular y antes del inicio
# ============================================================================

def test_RN6_solo_el_titular_cancela(con):
    r = reservar(con, ANA, SALA_A)
    with pytest.raises(SinPermiso):
        srv.cancelar_reserva(con, r["id"], BETO, AHORA)
    assert estado(con, r["id"]) == "activa"


def test_RN6_no_se_cancela_despues_del_inicio(con):
    r = reservar(con, ANA, SALA_A, "10:00", "11:00")
    with pytest.raises(ReglaIncumplida) as exc:
        srv.cancelar_reserva(con, r["id"], ANA, a_las(10, 0))
    assert exc.value.codigo == "RN6_INICIADA"


def test_banderas_de_acciones_en_mis_reservas(con):
    reservar(con, ANA, SALA_A, "10:00", "11:00")
    antes = srv.mis_reservas(con, ANA, a_las(9))[0]
    assert antes["puede_cancelar"] and not antes["puede_confirmar"]
    durante = srv.mis_reservas(con, ANA, a_las(10, 5))[0]
    assert durante["puede_confirmar"] and not durante["puede_cancelar"]


# ============================================================================
# RF03 · Disponibilidad
# ============================================================================

def test_disponibilidad_marca_libre_ocupado_propia_y_pasado(con):
    reservar(con, ANA, SALA_A, "10:00", "12:00")
    datos = srv_disp.disponibilidad(con, FECHA, a_las(9, 30), usuario_id=BETO)
    sala_a = {b["hora_inicio"]: b["estado"] for b in datos["salas"][0]["bloques"]}
    assert sala_a["08:00"] == "pasado"
    assert sala_a["10:00"] == sala_a["11:00"] == "ocupado"
    assert sala_a["12:00"] == "libre"
    propia = srv_disp.disponibilidad(con, FECHA, a_las(9, 30), usuario_id=ANA)
    assert propia["salas"][0]["bloques"][2]["estado"] == "propia"
    assert len(datos["salas"][0]["bloques"]) == 13          # 08:00 a 21:00


# ============================================================================
# RF09 / RF10 · Reporte de uso y horas pico
# ============================================================================

def test_reporte_usadas_y_no_usadas_por_sala(con):
    r1 = reservar(con, ANA, SALA_A, "09:00", "10:00")
    reservar(con, BETO, SALA_A, "11:00", "12:00")
    r3 = reservar(con, BETO, SALA_C, "09:00", "10:00")
    srv.confirmar_llegada(con, r1["id"], ANA, a_las(9, 3))
    srv.cancelar_reserva(con, r3["id"], BETO, a_las(8, 30))
    srv.actualizar_estados(con, a_las(12, 30))
    rep = srv_rep.reporte_uso(con, FECHA, FECHA)
    sala_a = next(s for s in rep["por_sala"] if s["nombre"] == "Sala A")
    assert (sala_a["reservas"], sala_a["usadas"], sala_a["no_usadas"]) == (2, 1, 1)
    assert sala_a["tasa_uso"] == 50.0
    assert rep["totales"]["canceladas"] == 1


def test_horas_pico_cuenta_cada_hora_ocupada(con):
    reservar(con, ANA, SALA_A, "10:00", "12:00")
    reservar(con, BETO, SALA_B, "11:00", "12:00")
    pico = srv_rep.horas_pico(con, FECHA, FECHA)
    por_hora = {b["hora_inicio"]: b["reservas"] for b in pico["bloques"]}
    assert por_hora["10:00"] == 1 and por_hora["11:00"] == 2
    assert pico["horas_pico"] == ["11:00"]


def test_reporte_valida_el_rango(con):
    with pytest.raises(DatosInvalidos):
        srv_rep.reporte_uso(con, "2026-11-30", "2026-11-01")


# ============================================================================
# RF01 / RF02 · Administración
# ============================================================================

def test_sala_con_nombre_duplicado_o_capacidad_invalida(con):
    with pytest.raises(ReglaIncumplida):
        srv_salas.crear_sala(con, {"nombre": "sala a", "capacidad": 3})
    with pytest.raises(DatosInvalidos):
        srv_salas.crear_sala(con, {"nombre": "Sala Z", "capacidad": 0})
    nueva = srv_salas.crear_sala(con, {"nombre": "Sala Z", "capacidad": 3, "ubicacion": "Piso 4"})
    assert nueva["activa"] is True


def test_usuario_con_correo_duplicado_o_rol_invalido(con):
    with pytest.raises(ReglaIncumplida):
        srv_usuarios.crear_usuario(con, {"nombre": "Otra Ana", "correo": "ANA@demo.cl", "rol": "estudiante"})
    with pytest.raises(DatosInvalidos):
        srv_usuarios.crear_usuario(con, {"nombre": "X", "correo": "x@demo.cl", "rol": "admin"})


def test_no_se_elimina_un_usuario_con_historial(con):
    reservar(con, ANA, SALA_A)
    with pytest.raises(ReglaIncumplida):
        srv_usuarios.eliminar_usuario(con, ANA)


def test_se_elimina_un_usuario_con_reserva_cancelada(con):
    reserva = reservar(con, ANA, SALA_A)
    srv.cancelar_reserva(con, reserva["id"], ANA, a_las(8, 30))
    srv_usuarios.eliminar_usuario(con, ANA)
    assert contar(con, usuario_id=ANA) == 0
    with pytest.raises(NoEncontrado):
        srv_usuarios.obtener_usuario(con, ANA)


def test_se_elimina_una_sala_con_todo_su_historial(con):
    reservar(con, ANA, SALA_A)
    reservar(con, BETO, SALA_A, "11:00", "12:00")
    srv_salas.eliminar_sala(con, SALA_A)
    assert contar(con, sala_id=SALA_A) == 0
    with pytest.raises(NoEncontrado):
        srv_salas.obtener_sala(con, SALA_A)
