// RF03 · Consultar disponibilidad por fecha y sala.
// Teléfono: una tarjeta por sala con sus bloques. Computador: grilla salas × horas.
import { get } from "../api.js";
import { $, avisoError, consultaMovil, el, esMovil, fechaLarga, infoServidor, montarPagina, sumarDias } from "../ui.js";

const usuario = montarPagina();
const esEstudiante = usuario.rol === "estudiante";
const inputFecha = $("#fecha");
if (!esEstudiante) $("#leyenda-propia").classList.add("oculto");

let hoy = null;
let ultimosDatos = null;
const TEXTOS = { libre: "Libre", ocupado: "Ocupado", propia: "Tuya", pasado: "Pasó" };

function irA(fecha) {
  inputFecha.value = fecha;
  history.replaceState(null, "", `?fecha=${fecha}`);
  cargar();
}

async function cargar() {
  $("#mensaje").replaceChildren();
  try {
    ultimosDatos = await get("/disponibilidad", { fecha: inputFecha.value });
    const libres = ultimosDatos.salas.reduce((total, s) => total + s.bloques_libres, 0);
    $("#subtitulo").textContent =
      `${fechaLarga(ultimosDatos.fecha)} · ${libres} bloque${libres === 1 ? "" : "s"} libre${libres === 1 ? "" : "s"}` +
      (esEstudiante ? " · toca uno para reservarlo" : "");
    pintar();
  } catch (error) {
    $("#grilla").replaceChildren();
    $("#mensaje").replaceChildren(avisoError(error, "No se pudo cargar la disponibilidad"));
  }
}

function pintar() {
  if (!ultimosDatos) return;
  const contenedor = $("#grilla");
  if (!ultimosDatos.salas.length) {
    contenedor.replaceChildren(el("p", { class: "vacio" }, "No hay salas activas."));
    return;
  }
  contenedor.replaceChildren(esMovil() ? pintarTarjetas(ultimosDatos) : pintarGrilla(ultimosDatos));
}

function boton(sala, b, fecha, { conHora }) {
  const reservable = esEstudiante && b.estado === "libre";
  const etiqueta = `${sala.nombre}, ${b.hora_inicio} a ${b.hora_fin}: ${b.estado === "pasado" ? "ya pasó" : b.estado}`;
  return el(
    "button",
    {
      type: "button",
      class: `bloque bloque--${b.estado}`,
      title: etiqueta,
      "aria-label": etiqueta,
      disabled: !reservable,
      onclick: reservable
        ? () => {
            const q = new URLSearchParams({ fecha, sala: sala.id, hora: b.hora_inicio });
            location.href = `nueva-reserva.html?${q}`;
          }
        : null,
    },
    conHora ? [b.hora_inicio, el("small", {}, TEXTOS[b.estado])] : (b.estado === "pasado" ? "" : TEXTOS[b.estado])
  );
}

function pintarTarjetas(datos) {
  return el(
    "div",
    { class: "salas-lista" },
    datos.salas.map((sala) => {
      const nivel = nivelSala(sala);
      return el(
        "section",
        { class: `sala-card sala-card--${nivel}`, "aria-label": `${sala.nombre}, ${nombreNivelSala(sala)}` },
        el(
          "div",
          { class: "sala-card__cabeza" },
          el("div", {}, el("h3", {}, sala.nombre), el("small", {}, `${sala.capacidad} personas · ${sala.ubicacion}`)),
          el("span", { class: `sala-card__libres sala-card__libres--${nivel}` },
            sala.bloques_libres ? `${sala.bloques_libres} libre${sala.bloques_libres === 1 ? "" : "s"}` : "Llena")
        ),
        el("div", { class: "chips", "aria-disabled": String(nivel === "llena") },
          sala.bloques.map((b) => boton(sala, b, datos.fecha, { conHora: true })))
      );
    })
  );
}

function pintarGrilla(datos) {
  return el(
    "div",
    { class: "grilla-envoltura" },
    el(
      "table",
      { class: "grilla" },
      el("caption", { class: "sr-only" }, `Disponibilidad del ${fechaLarga(datos.fecha)}`),
      el("colgroup", {}, el("col", { class: "grilla__col-sala" }), datos.horas.map(() => el("col"))),
      el("thead", {}, el("tr", {}, el("th", { scope: "col", class: "grilla__sala" }, "Sala"),
        datos.horas.map((h) => el("th", { scope: "col" }, h)))),
      el(
        "tbody",
        {},
        datos.salas.map((sala) =>
          el(
            "tr",
            { class: `sala-fila sala-fila--${nivelSala(sala)}` },
            el("th", { scope: "row", class: "grilla__sala" }, sala.nombre,
              el("small", {}, `${sala.capacidad} personas · ${sala.ubicacion} · ${nombreNivelSala(sala)}`)),
            sala.bloques.map((b) => el("td", {}, boton(sala, b, datos.fecha, { conHora: false })))
          )
        )
      )
    )
  );
}

function nivelSala(sala) {
  const total = sala.bloques?.length || 0;
  if (!total || sala.bloques_libres === 0) return "llena";
  const proporcion = sala.bloques_libres / total;
  if (proporcion >= 0.75) return "verde";
  if (proporcion >= 0.50) return "amarilla";
  return "naranja";
}

function nombreNivelSala(sala) {
  return {
    verde: "Disponibilidad alta",
    amarilla: "Disponibilidad moderada",
    naranja: "Pocas horas disponibles",
    llena: "Sala llena",
  }[nivelSala(sala)];
}

$("#dia-anterior").addEventListener("click", () => irA(sumarDias(inputFecha.value, -1)));
$("#dia-siguiente").addEventListener("click", () => irA(sumarDias(inputFecha.value, 1)));
$("#hoy").addEventListener("click", () => irA(hoy));
inputFecha.addEventListener("change", () => inputFecha.value && irA(inputFecha.value));
consultaMovil.addEventListener("change", pintar);

(async () => {
  try {
    hoy = (await infoServidor()).ahora.slice(0, 10);
  } catch {
    hoy = new Date().toISOString().slice(0, 10);
  }
  inputFecha.value = new URLSearchParams(location.search).get("fecha") || hoy;
  cargar();
  setInterval(cargar, 60_000); // refleja liberaciones automáticas
})();
