// RF08 · Mis reservas · RF05 · Cancelar (RN6) · RF06 · Confirmar llegada (RN5).
import { get, post } from "../api.js";
import { $, aviso, avisoError, badgeEstado, el, fechaCorta, horaDe, montarPagina, partesFecha, toast } from "../ui.js";

montarPagina({ roles: ["estudiante"] });

let reservas = [];
let pestana = "proximas";
const VIGENTES = ["activa", "confirmada"];

async function cargar() {
  try {
    reservas = await get("/reservas/mias");
    $("#mensaje").replaceChildren();
    pintar();
  } catch (error) {
    $("#lista").replaceChildren();
    $("#mensaje").replaceChildren(avisoError(error, "No se pudieron cargar tus reservas"));
  }
}

function pintar() {
  const proximas = reservas
    .filter((r) => VIGENTES.includes(r.estado))
    .sort((a, b) => (a.fecha + a.hora_inicio).localeCompare(b.fecha + b.hora_inicio));
  const historial = reservas.filter((r) => !VIGENTES.includes(r.estado));
  $("#n-proximas").textContent = proximas.length;
  $("#n-historial").textContent = historial.length;
  $("#tab-proximas").setAttribute("aria-selected", String(pestana === "proximas"));
  $("#tab-historial").setAttribute("aria-selected", String(pestana === "historial"));

  const lista = pestana === "proximas" ? proximas : historial;
  if (!lista.length) {
    $("#lista").replaceChildren(
      el("div", { class: "tarjeta vacio" },
        pestana === "proximas"
          ? ["No tienes reservas próximas. ", el("a", { href: "disponibilidad.html" }, "Revisa la disponibilidad")]
          : "Aún no tienes reservas pasadas.")
    );
    return;
  }
  $("#lista").replaceChildren(...lista.map(tarjeta));
}

function nota(r) {
  const desde = horaDe(r.confirmar_desde);
  const hasta = horaDe(r.confirmar_hasta);
  switch (r.estado) {
    case "activa":
      return r.puede_confirmar
        ? el("p", { class: "reserva__nota reserva__nota--urgente" }, `Confirma ahora: tienes hasta las ${hasta}.`)
        : el("p", { class: "reserva__nota" }, `Confirma tu llegada entre las ${desde} y las ${hasta}.`);
    case "confirmada":
      return el("p", { class: "reserva__nota" }, `Llegada confirmada a las ${horaDe(r.confirmada_en)}.`);
    case "liberada":
      return el("p", { class: "reserva__nota" }, `Se liberó porque no se confirmó antes de las ${hasta}.`);
    case "cancelada":
      return el("p", { class: "reserva__nota" }, "La cancelaste antes del inicio.");
    case "finalizada":
      return el("p", { class: "reserva__nota" }, "Usada y terminada.");
    default:
      return null;
  }
}

function tarjeta(r) {
  const f = partesFecha(r.fecha);
  const acciones = el("div", { class: "reserva__acciones" });
  if (r.puede_confirmar) {
    acciones.append(el("button", { type: "button", class: "boton boton--exito", onclick: () => confirmar(r) }, "Confirmar llegada"));
  }
  if (r.puede_cancelar) {
    acciones.append(el("button", { type: "button", class: "boton boton--peligro", onclick: () => pedirCancelacion(r, acciones) }, "Cancelar"));
  }
  return el(
    "article",
    { class: "reserva" },
    el("div", { class: "reserva__fecha" },
      el("div", { class: "reserva__semana" }, f.semana),
      el("div", { class: "reserva__dia" }, f.dia),
      el("div", { class: "reserva__mes" }, f.mes)),
    el("div", {},
      el("div", { class: "reserva__titulo" }, el("h3", {}, `${r.sala.nombre} · ${r.hora_inicio} – ${r.hora_fin}`), badgeEstado(r.estado)),
      el("p", { class: "reserva__detalle" },
        `${fechaCorta(r.fecha)} · ${r.asistentes} persona${r.asistentes > 1 ? "s" : ""} · ${r.sala.ubicacion}`),
      nota(r)),
    acciones
  );
}

function pedirCancelacion(r, contenedor) {
  contenedor.replaceChildren(
    el("div", { class: "confirmacion-inline" },
      el("span", {}, "¿Cancelar esta reserva?"),
      el("button", { type: "button", class: "boton boton--peligro boton--chico", onclick: () => cancelar(r) }, "Sí, cancelar"),
      el("button", { type: "button", class: "boton boton--secundario boton--chico", onclick: pintar }, "No"))
  );
}

async function cancelar(r) {
  try {
    await post(`/reservas/${r.id}/cancelar`);
    toast(`Reserva cancelada: ${r.sala.nombre}, ${r.hora_inicio}. El bloque quedó libre.`);
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, "No se pudo cancelar"));
  }
  cargar();
}

async function confirmar(r) {
  try {
    await post(`/reservas/${r.id}/confirmar`);
    toast(`Llegada confirmada en ${r.sala.nombre}.`);
  } catch (error) {
    $("#mensaje").replaceChildren(aviso("error", "No se pudo confirmar", error.message));
  }
  cargar();
}

$("#tab-proximas").addEventListener("click", () => { pestana = "proximas"; pintar(); });
$("#tab-historial").addEventListener("click", () => { pestana = "historial"; pintar(); });

cargar();
setInterval(cargar, 30_000); // la liberación a los 15 minutos se refleja sola
