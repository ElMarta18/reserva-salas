import { get, post } from "../api.js";
import { guardarSesion, obtenerSesion, paginaInicio } from "../sesion.js";
import { $, aviso, avisoError, el } from "../ui.js";

const sesion = obtenerSesion();
if (sesion) location.replace(paginaInicio(sesion));

const mensaje = $("#mensaje");
if (new URLSearchParams(location.search).get("sesion") === "expirada") {
  mensaje.replaceChildren(aviso("alerta", null, "Tu sesión ya no es válida. Vuelve a ingresar."));
}

function entrar(usuario) {
  guardarSesion(usuario);
  location.replace(paginaInicio(usuario));
}

async function cargarUsuarios() {
  const lista = $("#lista-usuarios");
  try {
    const usuarios = await get("/auth/usuarios-demo");
    lista.replaceChildren(
      ...usuarios.map((u) =>
        el(
          "button",
          { type: "button", class: "usuario-demo", onclick: () => entrar(u) },
          el("span", {}, u.nombre, el("small", {}, u.correo)),
          el("span", { class: `etiqueta-rol etiqueta-rol--${u.rol}` }, u.rol === "biblioteca" ? "Biblioteca" : "Estudiante")
        )
      )
    );
  } catch (error) {
    lista.replaceChildren(avisoError(error, "No se pudo cargar la lista"));
  }
}

$("#form-login").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const correo = $("#correo").value.trim();
  if (!correo) {
    mensaje.replaceChildren(aviso("error", null, "Escribe tu correo."));
    return;
  }
  try {
    entrar(await post("/auth/login", { correo }));
  } catch (error) {
    mensaje.replaceChildren(avisoError(error, "No pudimos ingresar"));
  }
});

const registro = $("#form-registro");
const mostrarRegistro = $("#mostrar-registro");

mostrarRegistro.addEventListener("click", () => {
  registro.classList.toggle("oculto");
  mostrarRegistro.textContent = registro.classList.contains("oculto") ? "Regístrate aquí" : "Cancelar registro";
  if (!registro.classList.contains("oculto")) $("#nombre-registro").focus();
});

registro.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const nombre = $("#nombre-registro").value.trim();
  const correo = $("#correo-registro").value.trim();
  try {
    const usuario = await post("/auth/registro", { nombre, correo });
    registro.reset();
    registro.classList.add("oculto");
    mostrarRegistro.textContent = "Regístrate aquí";
    $("#correo").value = usuario.correo;
    mensaje.replaceChildren(aviso("exito", null, "Cuenta creada. Ya puedes ingresar con tu correo."));
  } catch (error) {
    mensaje.replaceChildren(avisoError(error, "No pudimos crear la cuenta"));
  }
});

cargarUsuarios();
