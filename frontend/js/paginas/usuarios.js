// RF02 · Registrar usuarios con su rol (personal de biblioteca).
import { del, get, post, put } from "../api.js";
import { $, aviso, avisoError, celda, el, marcarCampoConError, montarPagina, toast } from "../ui.js";

const yo = montarPagina({ roles: ["biblioteca"] });
const form = $("#form-usuario");
let editando = null;
let filtroRol = "";

async function cargar() {
  try {
    const usuarios = await get("/usuarios", { rol: filtroRol });
    $("#tabla").replaceChildren(
      el("table", { class: "tabla tabla--tarjetas" },
        el("thead", {}, el("tr", {}, ["Nombre", "Correo", "Rol", ""].map((c) => el("th", {}, c)))),
        el("tbody", {}, usuarios.map((u) =>
          el("tr", {},
            celda("Nombre", [el("strong", {}, u.nombre), u.id === yo.id ? el("span", { class: "campo__ayuda" }, " (tú)") : ""], "celda-titulo"),
            celda("Correo", u.correo),
            celda("Rol", el("span", { class: `etiqueta-rol etiqueta-rol--${u.rol}` }, u.rol === "biblioteca" ? "Biblioteca" : "Estudiante")),
            celda("", el("div", { class: "grupo-botones" },
              el("button", { type: "button", class: "boton boton--secundario boton--chico", onclick: () => editar(u) }, "Editar"),
              u.id === yo.id ? null
                : el("button", { type: "button", class: "boton boton--peligro boton--chico", onclick: () => eliminar(u) }, "Eliminar")),
              "celda-acciones"))))
      )
    );
  } catch (error) {
    $("#tabla").replaceChildren(avisoError(error, "No se pudieron cargar los usuarios"));
  }
}

function limpiar() {
  editando = null;
  form.reset();
  $("#titulo-form").textContent = "Nuevo usuario";
  $("#guardar").textContent = "Agregar usuario";
  $("#cancelar-edicion").classList.add("oculto");
  marcarCampoConError(form, null);
}

function editar(u) {
  editando = u.id;
  form.nombre.value = u.nombre;
  form.correo.value = u.correo;
  form.rol.value = u.rol;
  $("#titulo-form").textContent = `Editar ${u.nombre}`;
  $("#guardar").textContent = "Guardar cambios";
  $("#cancelar-edicion").classList.remove("oculto");
  $("#mensaje").replaceChildren();
  form.scrollIntoView({ behavior: "smooth", block: "center" });
  form.nombre.focus({ preventScroll: true });
}

async function eliminar(u) {
  try {
    await del(`/usuarios/${u.id}`);
    toast(`${u.nombre} eliminado.`);
    if (editando === u.id) limpiar();
    cargar();
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, `No se pudo eliminar a ${u.nombre}`));
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = { nombre: form.nombre.value.trim(), correo: form.correo.value.trim(), rol: form.rol.value };
  try {
    const u = editando ? await put(`/usuarios/${editando}`, datos) : await post("/usuarios", datos);
    $("#mensaje").replaceChildren(aviso("exito", null, editando ? `Cambios guardados para ${u.nombre}.` : `${u.nombre} registrado como ${u.rol}.`));
    limpiar();
    cargar();
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, "Revisa los datos"));
    marcarCampoConError(form, error.campo);
  }
});
$("#cancelar-edicion").addEventListener("click", () => { limpiar(); $("#mensaje").replaceChildren(); });
$("#filtro-rol").addEventListener("click", (e) => {
  const boton = e.target.closest("button[data-rol]");
  if (!boton) return;
  filtroRol = boton.dataset.rol;
  $("#filtro-rol").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === boton)));
  cargar();
});

cargar();
