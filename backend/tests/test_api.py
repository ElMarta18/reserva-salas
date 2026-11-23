"""Pruebas de la API HTTP (capa de controlador)."""
from __future__ import annotations

from datetime import datetime

from conftest import ANA, BETO, FECHA, PAULA, SALA_A, como


def nueva(inicio="10:00", duracion=1, sala=SALA_A, asistentes=2):
    return {"sala_id": sala, "fecha": FECHA, "hora_inicio": inicio, "duracion": duracion, "asistentes": asistentes}


def test_salud_no_requiere_sesion(cliente):
    r = cliente.get("/api/salud")
    assert r.status_code == 200
    assert r.json["ahora"] == "2026-11-24 08:00:00"


def test_login_simulado_por_correo(cliente):
    r = cliente.post("/api/auth/login", json={"correo": "ANA@demo.cl"})
    assert r.status_code == 200 and r.json["rol"] == "estudiante"
    assert cliente.post("/api/auth/login", json={"correo": "nadie@demo.cl"}).status_code == 404


def test_sin_sesion_responde_401(cliente):
    assert cliente.get("/api/disponibilidad").status_code == 401
    assert cliente.get("/api/disponibilidad", headers={"X-Usuario-Id": "999"}).status_code == 401


def test_roles_se_respetan(cliente):
    assert cliente.get("/api/reporte", headers=como(ANA)).status_code == 403
    assert cliente.post("/api/salas", json={"nombre": "X", "capacidad": 2}, headers=como(ANA)).status_code == 403
    assert cliente.post("/api/reservas", json=nueva(), headers=como(PAULA)).status_code == 403
    assert cliente.get("/api/reporte", headers=como(PAULA)).status_code == 200


def test_crear_reserva_201_y_choque_409(cliente):
    r1 = cliente.post("/api/reservas", json=nueva("10:00"), headers=como(ANA))
    assert r1.status_code == 201
    assert r1.json["estado"] == "activa" and r1.json["sala"]["nombre"] == "Sala A"
    r2 = cliente.post("/api/reservas", json=nueva("10:00", duracion=2), headers=como(BETO))
    assert r2.status_code == 409
    assert r2.json["error"]["mensaje"] == "La sala ya está reservada en ese horario."
    assert r2.json["error"]["sugerencias"]["bloques_libres"]


def test_datos_incompletos_responden_400(cliente):
    r = cliente.post("/api/reservas", json={"sala_id": SALA_A}, headers=como(ANA))
    assert r.status_code == 400
    assert r.json["error"]["campo"] == "fecha"
    r = cliente.post("/api/reservas", data="no es json", content_type="application/json", headers=como(ANA))
    assert r.status_code == 400


def test_liberacion_corre_antes_de_cada_peticion(app, cliente):
    rid = cliente.post("/api/reservas", json=nueva("10:00"), headers=como(ANA)).json["id"]
    app.config["AHORA_FIJA"] = datetime(2026, 11, 24, 10, 16)
    mias = cliente.get("/api/reservas/mias", headers=como(ANA)).json
    assert next(r for r in mias if r["id"] == rid)["estado"] == "liberada"


def test_confirmar_y_cancelar_por_api(app, cliente):
    r1 = cliente.post("/api/reservas", json=nueva("10:00"), headers=como(ANA)).json
    r2 = cliente.post("/api/reservas", json=nueva("14:00"), headers=como(ANA)).json
    assert cliente.post(f"/api/reservas/{r2['id']}/cancelar", headers=como(BETO)).status_code == 403
    assert cliente.post(f"/api/reservas/{r2['id']}/cancelar", headers=como(ANA)).json["estado"] == "cancelada"
    app.config["AHORA_FIJA"] = datetime(2026, 11, 24, 10, 10)
    r = cliente.post(f"/api/reservas/{r1['id']}/confirmar", headers=como(ANA))
    assert r.status_code == 200 and r.json["estado"] == "confirmada"


def test_disponibilidad_por_fecha(cliente):
    cliente.post("/api/reservas", json=nueva("10:00"), headers=como(ANA))
    datos = cliente.get(f"/api/disponibilidad?fecha={FECHA}", headers=como(BETO)).json
    assert datos["fecha"] == FECHA and len(datos["horas"]) == 13
    sala_a = datos["salas"][0]
    assert sala_a["bloques"][2] == {"hora_inicio": "10:00", "hora_fin": "11:00", "estado": "ocupado"}


def test_administrar_salas(cliente):
    r = cliente.post("/api/salas", json={"nombre": "Sala Z", "capacidad": 3}, headers=como(PAULA))
    assert r.status_code == 201
    assert cliente.post("/api/salas", json={"nombre": "Sala Z", "capacidad": 3}, headers=como(PAULA)).status_code == 409
    sid = r.json["id"]
    assert cliente.put(f"/api/salas/{sid}", json={"activa": False}, headers=como(PAULA)).json["activa"] is False
    visibles = [s["nombre"] for s in cliente.get("/api/salas", headers=como(ANA)).json]
    assert "Sala Z" not in visibles
    todas = cliente.get("/api/salas?incluir_inactivas=1", headers=como(PAULA)).json
    assert "Sala Z" in [s["nombre"] for s in todas]
    assert cliente.delete(f"/api/salas/{sid}", headers=como(PAULA)).status_code == 204


def test_administrar_usuarios(cliente):
    r = cliente.post(
        "/api/usuarios", json={"nombre": "Carla", "correo": "carla@demo.cl", "rol": "estudiante"}, headers=como(PAULA)
    )
    assert r.status_code == 201
    assert cliente.delete(f"/api/usuarios/{PAULA}", headers=como(PAULA)).status_code == 409
    assert cliente.delete(f"/api/usuarios/{r.json['id']}", headers=como(PAULA)).status_code == 204


def test_reporte_y_horas_pico(cliente):
    cliente.post("/api/reservas", json=nueva("10:00", duracion=2), headers=como(ANA))
    rep = cliente.get(f"/api/reporte?desde={FECHA}&hasta={FECHA}", headers=como(PAULA)).json
    assert rep["totales"]["reservas"] == 1 and rep["totales"]["pendientes"] == 1
    pico = cliente.get(f"/api/reporte/horas-pico?desde={FECHA}&hasta={FECHA}", headers=como(PAULA)).json
    assert pico["horas_pico"] == ["10:00", "11:00"]
    assert cliente.get("/api/reporte?desde=2026-12-01&hasta=2026-11-01", headers=como(PAULA)).status_code == 400


def test_cors_para_el_frontend(cliente):
    r = cliente.get("/api/salud", headers={"Origin": "http://localhost:5500"})
    assert r.headers["Access-Control-Allow-Origin"] == "http://localhost:5500"
    otro = cliente.get("/api/salud", headers={"Origin": "http://malicioso.example"})
    assert "Access-Control-Allow-Origin" not in otro.headers
    # teléfonos y otros computadores de la red local
    for origen in ("http://192.168.1.20:5500", "http://10.0.0.7:5500", "http://mi-pc.local:5500"):
        r = cliente.get("/api/salud", headers={"Origin": origen})
        assert r.headers.get("Access-Control-Allow-Origin") == origen
    publica = cliente.get("/api/salud", headers={"Origin": "http://8.8.8.8:5500"})
    assert "Access-Control-Allow-Origin" not in publica.headers
    pre = cliente.options(
        "/api/reservas",
        headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST"},
    )
    assert pre.status_code == 200 and "X-Usuario-Id" in pre.headers["Access-Control-Allow-Headers"]


def test_rutas_desconocidas_responden_json(cliente):
    r = cliente.get("/api/no-existe")
    assert r.status_code == 404 and r.json["error"]["codigo"] == "HTTP_404"
