// RF04 · Crear reserva por bloques (el servidor valida RN1–RN4).
import { get, post } from "../api.js";
import {
  $, aviso, avisoError, el, fechaLarga, horaDe, infoServidor, marcarCampoConError, montarPagina,
} from "../ui.js";

montarPagina({ roles: ["estudiante"] });

const form = $("#form-reserva");
const estado = { fecha: "", salaId: null, duracion: 1, hora: "", asistentes: 1 };
let salas = [];
let reglas = { max_reservas_vigentes: 2 };
let disponibilidadPorSala = new Map();

const salaActual = () => salas.find((s) => s.id === estado.salaId);

// ---------- Paso 1 · Fecha y sala ----------
function pintarSalas() {
  $("#salas").replaceChildren(
    ...salas.map((s) => {
      const disponibilidad = datosDisponibilidadSala(s);
      return el(
        "button",
        {
          type: "button",
          class: `opcion opcion--${disponibilidad.nivel}`,
          "aria-pressed": String(s.id === estado.salaId),
          disabled: disponibilidad.nivel === "llena",
          onclick: () => elegirSala(s.id),
        },
        el("strong", {}, s.nombre),
        el("span", {}, `Hasta ${s.capacidad} personas`),
        el("span", {}, s.ubicacion),
        el("small", { class: "opcion__estado" }, disponibilidad.texto)
      );
    })
  );
  form.sala_id.value = estado.salaId ?? "";
}

function elegirSala(id) {
  estado.salaId = id;
  pintarSalas();
  actualizarCapacidad();
  cargarHoras();
}

// ---------- Paso 2 · Horario ----------
async function cargarHoras() {
  const contenedor = $("#horas");
  if (!estado.fecha || !estado.salaId) {
    contenedor.replaceChildren(el("p", { class: "vacio" }, "Elige primero una fecha y una sala."));
    return pintarResumen();
  }
  contenedor.replaceChildren(el("p", { class: "vacio" }, "Buscando horarios libres…"));
  try {
    const datos = await get(`/disponibilidad/${estado.salaId}/bloques-libres`, {
      fecha: estado.fecha,
      duracion: estado.duracion,
    });
    if (estado.hora && !datos.bloques.some((b) => b.hora_inicio === estado.hora)) {
      $("#mensaje").replaceChildren(
        aviso("alerta", `Las ${estado.hora} ya no está disponible`,
          `En esta sala ese horario está ocupado, ya pasó o sumaría más de ${reglas.max_horas_seguidas ?? 2} horas seguidas con tus reservas. Elige otro bloque.`)
      );
      estado.hora = "";
    }
    if (!datos.bloques.length) {
      contenedor.replaceChildren(
        el("p", { class: "vacio" }, `No quedan bloques de ${estado.duracion} hora${estado.duracion > 1 ? "s" : ""} libres en esta sala para esa fecha. Prueba otra sala o fecha.`)
      );
    } else {
      contenedor.replaceChildren(
        ...datos.bloques.map((b) =>
          el(
            "button",
            {
              type: "button",
              class: "hora",
              "aria-pressed": String(b.hora_inicio === estado.hora),
              onclick: () => { estado.hora = b.hora_inicio; cargarHoras(); },
            },
            `${b.hora_inicio} – ${b.hora_fin}`
          )
        )
      );
    }
  } catch (error) {
    contenedor.replaceChildren(avisoError(error, "No se pudieron cargar los horarios"));
  }
  form.hora_inicio.value = estado.hora;
  pintarResumen();
}

$("#duracion").addEventListener("click", (evento) => {
  const boton = evento.target.closest("button[data-horas]");
  if (!boton) return;
  estado.duracion = Number(boton.dataset.horas);
  $("#duracion").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === boton)));
  cargarHoras();
});

// ---------- Paso 3 · Asistentes ----------
function actualizarCapacidad() {
  const sala = salaActual();
  const input = $("#asistentes");
  if (sala) {
    input.max = sala.capacidad;
    $("#ayuda-capacidad").textContent = `La ${sala.nombre} admite hasta ${sala.capacidad} personas, incluyéndote.`;
  }
  pintarResumen();
}

$("#asistentes").addEventListener("input", (e) => {
  estado.asistentes = Number(e.target.value) || 0;
  pintarResumen();
});
function cambiarAsistentes(delta) {
  const input = $("#asistentes");
  // Se permite pasar la capacidad: el servidor responde con salas más grandes (flujo A2)
  estado.asistentes = Math.min(50, Math.max(1, (Number(input.value) || 0) + delta));
  input.value = estado.asistentes;
  pintarResumen();
}
$("#menos").addEventListener("click", () => cambiarAsistentes(-1));
$("#mas").addEventListener("click", () => cambiarAsistentes(1));
$("#fecha").addEventListener("change", (e) => {
  estado.fecha = e.target.value;
  cargarDisponibilidadSalas();
});

// ---------- Resumen ----------
function horaFin() {
  if (!estado.hora) return "";
  const h = Number(estado.hora.slice(0, 2)) + estado.duracion;
  return `${String(h).padStart(2, "0")}:00`;
}

function pintarResumen() {
  const sala = salaActual();
  const filas = [
    ["Fecha", estado.fecha ? fechaLarga(estado.fecha) : "—"],
    ["Sala", sala ? sala.nombre : "—"],
    ["Horario", estado.hora ? `${estado.hora} – ${horaFin()}` : "—"],
    ["Personas", estado.asistentes || "—"],
  ];
  $("#resumen").replaceChildren(...filas.flatMap(([k, v]) => [el("div", {}, el("dt", {}, k), el("dd", {}, v))]));
  $("#paso-1").classList.toggle("paso--listo", Boolean(estado.fecha && sala));
  $("#paso-2").classList.toggle("paso--listo", Boolean(estado.hora));
  $("#paso-3").classList.toggle("paso--listo", estado.asistentes >= 1 && (!sala || estado.asistentes <= sala.capacidad));
}

async function pintarVigentes() {
  try {
    const mias = await get("/reservas/mias");
    const vigentes = mias.filter((r) => r.estado === "activa" || r.estado === "confirmada").length;
    const max = reglas.max_reservas_vigentes;
    $("#vigentes").replaceChildren(
      `Tienes ${vigentes} de ${max} reservas vigentes. `,
      vigentes >= max ? el("a", { href: "mis-reservas.html" }, "Ver mis reservas") : ""
    );
  } catch {
    $("#vigentes").textContent = "";
  }
}

// ---------- Envío ----------
form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const mensaje = $("#mensaje");
  mensaje.replaceChildren();
  marcarCampoConError(form, null);

  const faltante = !estado.fecha ? ["fecha", "Elige una fecha."]
    : !estado.salaId ? [null, "Elige una sala."]
    : !estado.hora ? [null, "Elige un horario libre."]
    : !(estado.asistentes >= 1) ? ["asistentes", "Indica cuántas personas asistirán."]
    : null;
  if (faltante) {
    mensaje.replaceChildren(aviso("error", "Falta un dato", faltante[1]));
    marcarCampoConError(form, faltante[0]);
    return;
  }

  const boton = $("#boton-reservar");
  boton.disabled = true;
  try {
    const reserva = await post("/reservas", {
      sala_id: estado.salaId,
      fecha: estado.fecha,
      hora_inicio: estado.hora,
      duracion: estado.duracion,
      asistentes: estado.asistentes,
    });
    mostrarExito(reserva);
  } catch (error) {
    mensaje.replaceChildren(avisoConSugerencias(error));
    marcarCampoConError(form, error.campo === "sala_id" ? null : error.campo);
  } finally {
    boton.disabled = false;
  }
});

// Flujos alternativos A1, A2 y A3: el error dice qué corregir y ofrece salidas.
function avisoConSugerencias(error) {
  const acciones = [];
  const { bloques_libres: bloques, salas: alternativas } = error.sugerencias || {};
  if (bloques?.length) {
    acciones.push(
      ...bloques.slice(0, 6).map((b) =>
        el("button", { type: "button", class: "boton boton--secundario boton--chico",
          onclick: () => { estado.hora = b.hora_inicio; $("#mensaje").replaceChildren(); cargarHoras(); } },
        `${b.hora_inicio} – ${b.hora_fin}`)
      )
    );
  }
  if (error.codigo === "RN3_CAPACIDAD") {
    if (alternativas?.length) {
      acciones.push(
        ...alternativas.map((s) =>
          el("button", { type: "button", class: "boton boton--secundario boton--chico",
            onclick: () => { $("#mensaje").replaceChildren(); elegirSala(s.id); } },
          `${s.nombre} (${s.capacidad} personas)`)
        )
      );
    } else {
      acciones.push(el("span", {}, "No hay salas más grandes libres en ese horario."));
    }
  }
  if (error.codigo === "RN4_LIMITE") {
    acciones.push(el("a", { class: "boton boton--secundario boton--chico", href: "mis-reservas.html" }, "Ir a Mis reservas"));
  }
  const titulo = {
    RN1_CHOQUE: "Horario ocupado · elige otro bloque libre",
    RN3_CAPACIDAD: "Supera la capacidad · prueba una sala más grande",
    RN4_LIMITE: "Límite de reservas alcanzado",
  }[error.codigo] || "No se pudo reservar";
  return aviso("error", titulo, error.message, acciones.length ? el("div", { class: "aviso__acciones" }, acciones) : null);
}

function mostrarExito(reserva) {
  form.classList.add("oculto");
  window.scrollTo({ top: 0, behavior: "smooth" });
  $("#exito").replaceChildren(
    el(
      "section",
      { class: "tarjeta" },
      aviso(
        "exito",
        "Reserva creada",
        `${reserva.sala.nombre} · ${fechaLarga(reserva.fecha)} · ${reserva.hora_inicio} – ${reserva.hora_fin} · ${reserva.asistentes} persona${reserva.asistentes > 1 ? "s" : ""}.`
      ),
      el(
        "div",
        { style: "margin-top:12px" },
        aviso(
          "alerta",
          "Recuerda confirmar tu llegada",
          `Confirma en «Mis reservas» entre las ${horaDe(reserva.confirmar_desde)} y las ${horaDe(reserva.confirmar_hasta)}. Si no, la sala se libera automáticamente.`
        )
      ),
      el(
        "div",
        { class: "grupo-botones", style: "margin-top:16px" },
        el("a", { class: "boton boton--primario", href: "mis-reservas.html" }, "Ver mis reservas"),
        el("a", { class: "boton boton--secundario", href: "nueva-reserva.html" }, "Hacer otra reserva")
      )
    )
  );
}

// ---------- Inicio ----------
(async () => {
  const parametros = new URLSearchParams(location.search);
  try {
    const [info, listaSalas] = await Promise.all([infoServidor(), get("/salas")]);
    reglas = info.reglas;
    salas = listaSalas;
    estado.fecha = parametros.get("fecha") || info.ahora.slice(0, 10);
    $("#fecha").min = info.ahora.slice(0, 10);
  } catch (error) {
    $("#salas").replaceChildren(avisoError(error, "No se pudieron cargar las salas"));
    return;
  }
  $("#fecha").value = estado.fecha;
  const salaParam = Number(parametros.get("sala"));
  if (salas.some((s) => s.id === salaParam)) estado.salaId = salaParam;
  estado.hora = parametros.get("hora") || "";
  pintarSalas();
  actualizarCapacidad();
  cargarHoras();
  pintarVigentes();
  cargarDisponibilidadSalas();
})();

function nivelSala(sala) {
  const disponibilidad = disponibilidadPorSala.get(sala.id);
  const total = disponibilidad?.bloques?.length || 0;
  const libres = disponibilidad?.bloques_libres || 0;
  if (!total || libres === 0) return "llena";
  const proporcion = libres / total;
  if (proporcion >= 0.75) return "verde";
  if (proporcion >= 0.50) return "amarilla";
  return "naranja";
}

function datosDisponibilidadSala(sala) {
  const nivel = nivelSala(sala);
  const libres = disponibilidadPorSala.get(sala.id)?.bloques_libres;
  return {
    nivel,
    texto: nivel === "llena" ? "Llena · sin horarios" : `${libres} horario${libres === 1 ? "" : "s"} libre${libres === 1 ? "" : "s"}`,
  };
}

async function cargarDisponibilidadSalas() {
  if (!estado.fecha) return;
  try {
    const datos = await get("/disponibilidad", { fecha: estado.fecha });
    disponibilidadPorSala = new Map(datos.salas.map((s) => [s.id, s]));
    if (estado.salaId && disponibilidadPorSala.get(estado.salaId)?.bloques_libres === 0) {
      estado.salaId = null;
      estado.hora = "";
    }
  } catch {
    disponibilidadPorSala = new Map();
  }
  pintarSalas();
  pintarResumen();
  await cargarHoras();
}
