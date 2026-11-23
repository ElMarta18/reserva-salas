// RF01 · Registrar y administrar salas (personal de biblioteca).
import { del, get, post, put } from "../api.js";
import { $, aviso, avisoError, celda, el, marcarCampoConError, montarPagina, toast } from "../ui.js";

montarPagina({ roles: ["biblioteca"] });

const form = $("#form-sala");
let editando = null;

async function cargar() {
  try {
    const salas = await get("/salas", { incluir_inactivas: 1 });
    $("#tabla").replaceChildren(
      el("table", { class: "tabla tabla--tarjetas" },
        el("thead", {}, el("tr", {}, ["Nombre", "Capacidad", "Ubicación", "Estado", ""].map((c, i) =>
          el("th", { class: i === 1 ? "num" : "" }, c)))),
        el("tbody", {}, salas.map((s) =>
          el("tr", {},
            celda("Nombre", el("strong", {}, s.nombre), "celda-titulo"),
            celda("Capacidad", `${s.capacidad} personas`, "num"),
            celda("Ubicación", s.ubicacion || "—"),
            celda("Estado", el("span", { class: `estado estado--${s.activa ? "confirmada" : "finalizada"}` }, s.activa ? "activa" : "inactiva")),
            celda("", el("div", { class: "grupo-botones" },
              el("button", { type: "button", class: "boton boton--secundario boton--chico", onclick: () => editar(s) }, "Editar"),
              el("button", { type: "button", class: "boton boton--secundario boton--chico", onclick: () => alternar(s) },
                s.activa ? "Desactivar" : "Activar"),
              el("button", { type: "button", class: "boton boton--peligro boton--chico", onclick: () => eliminar(s) }, "Eliminar")),
              "celda-acciones"))))
      )
    );
  } catch (error) {
    $("#tabla").replaceChildren(avisoError(error, "No se pudieron cargar las salas"));
  }
}

function limpiar() {
  editando = null;
  form.reset();
  form.activa.checked = true;
  $("#titulo-form").textContent = "Nueva sala";
  $("#guardar").textContent = "Agregar sala";
  $("#cancelar-edicion").classList.add("oculto");
  marcarCampoConError(form, null);
}

function editar(s) {
  editando = s.id;
  form.nombre.value = s.nombre;
  form.capacidad.value = s.capacidad;
  form.ubicacion.value = s.ubicacion;
  form.activa.checked = s.activa;
  $("#titulo-form").textContent = `Editar ${s.nombre}`;
  $("#guardar").textContent = "Guardar cambios";
  $("#cancelar-edicion").classList.remove("oculto");
  $("#mensaje").replaceChildren();
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  form.nombre.focus({ preventScroll: true });
}

async function alternar(s) {
  try {
    await put(`/salas/${s.id}`, { activa: !s.activa });
    toast(`${s.nombre} ${s.activa ? "desactivada" : "activada"}.`);
    cargar();
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error));
  }
}

async function eliminar(s) {
  if (!confirm(`¿Eliminar la sala ${s.nombre} y todo su historial de reservas?`)) return;
  try {
    await del(`/salas/${s.id}`);
    toast(`${s.nombre} eliminada.`);
    if (editando === s.id) limpiar();
    cargar();
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, `No se pudo eliminar ${s.nombre}`));
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = {
    nombre: form.nombre.value.trim(),
    capacidad: Number(form.capacidad.value),
    ubicacion: form.ubicacion.value.trim(),
    activa: form.activa.checked,
  };
  try {
    const sala = editando ? await put(`/salas/${editando}`, datos) : await post("/salas", datos);
    $("#mensaje").replaceChildren(aviso("exito", null, editando ? `Cambios guardados en ${sala.nombre}.` : `${sala.nombre} agregada.`));
    limpiar();
    cargar();
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, "Revisa los datos"));
    marcarCampoConError(form, error.campo);
  }
});
$("#cancelar-edicion").addEventListener("click", () => { limpiar(); $("#mensaje").replaceChildren(); });

cargar();
