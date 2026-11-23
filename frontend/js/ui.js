// Utilidades de interfaz compartidas por todas las páginas.
import { get } from "./api.js";
import { cerrarSesion, requerirSesion } from "./sesion.js";

// ---------- Construcción de elementos ----------
export function el(etiqueta, atributos = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor === false || valor === null || valor === undefined) continue;
    if (clave === "class") nodo.className = valor;
    else if (clave === "dataset") Object.assign(nodo.dataset, valor);
    else if (clave.startsWith("on") && typeof valor === "function") nodo.addEventListener(clave.slice(2), valor);
    else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, valor);
  }
  for (const hijo of hijos.flat()) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
  return nodo;
}

export const $ = (selector, raiz = document) => raiz.querySelector(selector);

// ---------- Fechas ----------
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

export function aFecha(iso) {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d);
}
export function aIso(fecha) {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}
export function sumarDias(iso, dias) {
  const f = aFecha(iso);
  f.setDate(f.getDate() + dias);
  return aIso(f);
}
export function fechaCorta(iso) {
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}-${m}-${a}`;
}
export function fechaLarga(iso) {
  const f = aFecha(iso);
  return `${DIAS[f.getDay()]} ${f.getDate()} de ${MESES[f.getMonth()]} ${f.getFullYear()}`;
}
export function partesFecha(iso) {
  const f = aFecha(iso);
  return { dia: f.getDate(), mes: MESES[f.getMonth()], semana: DIAS[f.getDay()].slice(0, 3) };
}
export const horaDe = (fechaHora) => fechaHora.slice(11, 16);

// ---------- Hora del sistema (la del servidor manda) ----------
let reglasCache = null;
export async function infoServidor() {
  if (!reglasCache) reglasCache = await get("/salud");
  return reglasCache;
}

// ---------- Íconos (trazos simples, heredan el color del texto) ----------
const ICONOS = {
  calendario: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4M8 14h2M12 14h2M16 14h0M8 17h2M12 17h2",
  mas: "M12 5v14M5 12h14M4 4h16v16H4z",
  lista: "M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01",
  grafico: "M4 20h16M7 16v-5M12 16V6M17 16v-8",
  puerta: "M5 21V4h10v17M15 6h4v15M3 21h18M12 12h.01",
  personas: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5c1.8.8 3 2.9 3 5.5",
  logo: "M4 5h16v14H4zM4 9h16M9 9v10M14 13h3",
};

export function icono(nombre) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", ICONOS[nombre]);
  svg.append(path);
  return svg;
}

// ---------- Cabecera y navegación ----------
// En el teléfono la navegación es una barra inferior; en el computador va en la cabecera.
const NAV = {
  estudiante: [
    ["disponibilidad.html", "Disponibilidad", "calendario"],
    ["nueva-reserva.html", "Reservar", "mas"],
    ["mis-reservas.html", "Mis reservas", "lista"],
  ],
  biblioteca: [
    ["disponibilidad.html", "Disponibilidad", "calendario"],
    ["reporte.html", "Reporte", "grafico"],
    ["salas.html", "Salas", "puerta"],
    ["usuarios.html", "Usuarios", "personas"],
  ],
};

export function montarPagina({ roles = [] } = {}) {
  const usuario = requerirSesion(roles);
  const actual = location.pathname.split("/").pop() || "index.html";
  const cabecera = $("#cabecera");
  cabecera.className = "cabecera";
  document.body.classList.add("con-nav");
  const primerNombre = usuario.nombre.split(" ")[0];
  cabecera.replaceChildren(
    el(
      "div",
      { class: "cabecera__contenido" },
      el(
        "a",
        { class: "marca", href: NAV[usuario.rol][0][0] },
        el("span", { class: "marca__icono" }, icono("logo")),
        el("span", { class: "marca__texto" }, "Salas de Estudio")
      ),
      el(
        "nav",
        { class: "nav", "aria-label": "Principal" },
        NAV[usuario.rol].map(([href, texto, nombreIcono]) =>
          el("a", { href, "aria-current": href === actual ? "page" : false }, icono(nombreIcono), el("span", {}, texto))
        )
      ),
      el(
        "div",
        { class: "usuario" },
        el("span", { class: "usuario__nombre", title: usuario.nombre },
          el("span", { class: "usuario__corto" }, primerNombre),
          el("span", { class: "usuario__largo" }, usuario.nombre)),
        el("span", { class: "usuario__rol" }, usuario.rol === "biblioteca" ? "· Biblioteca" : "· Estudiante"),
        el("button", { type: "button", onclick: () => { cerrarSesion(); location.replace("index.html"); } }, "Salir")
      )
    )
  );
  pintarReloj();
  return usuario;
}

// true en pantallas de teléfono (mismo corte que el CSS)
export const consultaMovil = window.matchMedia("(max-width: 759.98px)");
export const esMovil = () => consultaMovil.matches;

// Celda de tabla con etiqueta para la vista de tarjetas en el teléfono
export function celda(etiqueta, contenido, clase = "") {
  return el("td", { "data-label": etiqueta, class: clase || false }, contenido);
}

async function pintarReloj() {
  const destino = $("#reloj");
  if (!destino) return;
  try {
    const info = await infoServidor();
    destino.textContent = `Hora del sistema: ${fechaCorta(info.ahora)} ${horaDe(info.ahora)}`;
  } catch {
    destino.textContent = "";
  }
}

// ---------- Mensajes ----------
export function toast(mensaje, tipo = "ok") {
  let zona = $(".toast-zona");
  if (!zona) {
    zona = el("div", { class: "toast-zona", role: "status", "aria-live": "polite" });
    document.body.append(zona);
  }
  const nodo = el("div", { class: `toast ${tipo === "error" ? "toast--error" : ""}` }, mensaje);
  zona.append(nodo);
  setTimeout(() => nodo.remove(), 4200);
}

export function aviso(tipo, titulo, texto, ...extra) {
  return el(
    "div",
    { class: `aviso aviso--${tipo}`, role: tipo === "error" ? "alert" : "status" },
    titulo ? el("strong", {}, titulo) : null,
    texto ? el("span", {}, texto) : null,
    ...extra
  );
}

export function avisoError(error, titulo = "No se pudo completar la acción") {
  return aviso("error", titulo, error?.message || String(error));
}

export function marcarCampoConError(formulario, campo) {
  formulario.querySelectorAll(".campo--error").forEach((n) => n.classList.remove("campo--error"));
  if (!campo) return;
  const control = formulario.querySelector(`[name="${campo}"]`);
  control?.closest(".campo")?.classList.add("campo--error");
  control?.focus();
}

export function badgeEstado(estado) {
  return el("span", { class: `estado estado--${estado}` }, estado);
}

export function descargarCsv(nombre, filas) {
  const texto = filas
    .map((fila) => fila.map((v) => `"${String(v ?? "").replaceAll('"', '""')}"`).join(";"))
    .join("\r\n");
  const blob = new Blob(["﻿" + texto], { type: "text/csv;charset=utf-8" });
  const enlace = el("a", { href: URL.createObjectURL(blob), download: nombre });
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
}
