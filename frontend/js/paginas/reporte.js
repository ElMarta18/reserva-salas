// RF09 · Reporte de uso por sala y rango de fechas · RF10 · Gráfico de horas pico y filtros.
import { get } from "../api.js";
import {
  $, avisoError, celda, descargarCsv, el, esMovil, fechaCorta, infoServidor, montarPagina, sumarDias,
} from "../ui.js";

montarPagina({ roles: ["biblioteca"] });

const form = $("#filtros");
let ultimoReporte = null;
let ultimoPico = null;
let ocultarTooltip = () => {};
document.addEventListener("click", () => ocultarTooltip());   // tocar fuera cierra el tooltip
const NS = "http://www.w3.org/2000/svg";
const svg = (etiqueta, atributos = {}) => {
  const nodo = document.createElementNS(NS, etiqueta);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, v);
  return nodo;
};
const pct = (valor) => (valor === null || valor === undefined ? "—" : `${String(valor).replace(".", ",")} %`);

async function cargar() {
  const consulta = { desde: form.desde.value, hasta: form.hasta.value, sala_id: form.sala_id.value };
  $("#mensaje").replaceChildren();
  history.replaceState(null, "", `?${new URLSearchParams(consulta)}`);
  try {
    const [reporte, pico] = await Promise.all([get("/reporte", consulta), get("/reporte/horas-pico", consulta)]);
    ultimoReporte = reporte;
    ultimoPico = pico;
    const sala = form.sala_id.selectedOptions[0]?.textContent;
    $("#subtitulo").textContent =
      `Del ${fechaCorta(reporte.desde)} al ${fechaCorta(reporte.hasta)} · ${form.sala_id.value ? sala : "todas las salas"}`;
    pintarKpis(reporte.totales);
    pintarGrafico(pico);
    pintarTablaSalas(reporte);
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, "No se pudo generar el reporte"));
  }
}

// ---------- Indicadores ----------
function pintarKpis(t) {
  const kpi = (etiqueta, valor, notaTexto, color) =>
    el("div", { class: "kpi" },
      el("div", { class: "kpi__etiqueta" }, color ? el("i", { class: "punto", style: `background:${color}` }) : null, etiqueta),
      el("div", { class: "kpi__valor" }, valor),
      notaTexto ? el("div", { class: "kpi__nota" }, notaTexto) : null);
  $("#kpis").replaceChildren(
    kpi("Reservas", t.reservas, "sin contar canceladas"),
    kpi("Usadas", t.usadas, `${t.horas_usadas} horas de sala`, "var(--serie-usadas)"),
    kpi("No usadas", t.no_usadas, "liberadas a los 15 min", "var(--serie-no-usadas)"),
    kpi("Pendientes", t.pendientes, "aún no ocurren", "var(--serie-pendientes)"),
    kpi("Tasa de uso", pct(t.tasa_uso), "usadas ÷ (usadas + no usadas)"),
    kpi("Canceladas", t.canceladas, "por su titular")
  );
}

// ---------- Gráfico de horas pico (una serie: no necesita leyenda) ----------
// Se dibuja con el ancho real del contenedor, así el texto mide lo mismo en el teléfono y en el PC.
function pintarGrafico(datos) {
  const contenedor = $("#grafico");
  const bloques = datos.bloques;
  $("#pico-resumen").textContent = datos.maximo
    ? `Hora${datos.horas_pico.length > 1 ? "s" : ""} pico: ${datos.horas_pico.join(", ")} con ${datos.maximo} reserva${datos.maximo > 1 ? "s" : ""}.`
    : "Sin reservas en el rango elegido.";

  const ancho = Math.max(280, Math.round(contenedor.clientWidth || 760));
  const alto = esMovil() ? 210 : 250;
  const m = { arriba: 22, derecha: 4, abajo: 26, izquierda: 30 };
  const anchoUtil = ancho - m.izquierda - m.derecha;
  const altoUtil = alto - m.arriba - m.abajo;
  const paso = niceStep(datos.maximo);
  const tope = Math.max(paso, Math.ceil(datos.maximo / paso) * paso);
  const banda = anchoUtil / bloques.length;
  const anchoBarra = Math.max(6, Math.min(36, banda * 0.62));
  const cadaCuanto = banda < 26 ? 2 : 1;   // etiquetas del eje cada 2 horas si no caben
  const y = (v) => m.arriba + altoUtil - (v / tope) * altoUtil;
  const base = y(0);

  const lienzo = svg("svg", { viewBox: `0 0 ${ancho} ${alto}`, width: ancho, height: alto, role: "img",
    "aria-label": `Reservas por bloque horario. ${$("#pico-resumen").textContent}` });

  for (let v = 0; v <= tope; v += paso) {
    lienzo.append(svg("line", { class: v === 0 ? "eje-linea" : "rejilla", x1: m.izquierda, x2: ancho - m.derecha, y1: y(v), y2: y(v) }));
    const t = svg("text", { class: "eje", x: m.izquierda - 6, y: y(v) + 4, "text-anchor": "end" });
    t.textContent = v;
    lienzo.append(t);
  }

  const tooltip = el("div", { class: "tooltip oculto", role: "status" });
  let activa = null;
  const ocultar = () => {
    tooltip.classList.add("oculto");
    activa?.classList.remove("activa");
    activa = null;
  };

  bloques.forEach((b, i) => {
    const cx = m.izquierda + banda * i + banda / 2;
    const x = cx - anchoBarra / 2;
    const yTop = y(b.reservas);
    const h = base - yTop;

    const hit = svg("rect", { class: "barra-hit", x: m.izquierda + banda * i, y: m.arriba, width: banda, height: altoUtil });
    lienzo.append(hit);
    let barra = null;
    if (h > 0) {
      const r = Math.min(4, h, anchoBarra / 2);
      barra = svg("path", {
        class: "barra",
        d: `M${x},${base}V${yTop + r}Q${x},${yTop} ${x + r},${yTop}H${x + anchoBarra - r}Q${x + anchoBarra},${yTop} ${x + anchoBarra},${yTop + r}V${base}Z`,
      });
      lienzo.append(barra);
    }
    if (datos.maximo && b.reservas === datos.maximo) {
      const etiqueta = svg("text", { class: "etiqueta-valor", x: cx, y: yTop - 6, "text-anchor": "middle" });
      etiqueta.textContent = b.reservas;
      lienzo.append(etiqueta);
    }
    if (i % cadaCuanto === 0) {
      const eje = svg("text", { class: "eje", x: cx, y: alto - 8, "text-anchor": "middle" });
      eje.textContent = b.hora_inicio.slice(0, 2);
      lienzo.append(eje);
    }

    const mostrar = () => {
      ocultar();
      activa = barra;
      barra?.classList.add("activa");
      tooltip.replaceChildren(
        el("b", {}, `${b.hora_inicio} – ${b.hora_fin}`),
        `${b.reservas} reserva${b.reservas === 1 ? "" : "s"} · ${b.usadas} usada${b.usadas === 1 ? "" : "s"}`
      );
      // que el tooltip no se salga por los bordes en pantallas angostas
      const izquierda = Math.min(Math.max(cx, 70), ancho - 70);
      tooltip.style.left = `${izquierda}px`;
      tooltip.style.top = `${Math.max(yTop, m.arriba)}px`;
      tooltip.classList.remove("oculto");
    };
    hit.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") mostrar(); });
    hit.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") ocultar(); });
    hit.addEventListener("click", (e) => { e.stopPropagation(); mostrar(); });   // toque en el teléfono
  });

  const etiquetaEje = svg("text", { class: "eje", x: ancho - m.derecha, y: alto - 8, "text-anchor": "end" });
  etiquetaEje.textContent = "h";
  lienzo.append(etiquetaEje);
  contenedor.replaceChildren(lienzo, tooltip);
  ocultarTooltip = ocultar;

  $("#tabla-horas").replaceChildren(
    el("table", { class: "tabla" },
      el("thead", {}, el("tr", {}, el("th", {}, "Bloque"), el("th", { class: "num" }, "Reservas"), el("th", { class: "num" }, "Usadas"))),
      el("tbody", {}, bloques.map((b) =>
        el("tr", {}, el("td", {}, `${b.hora_inicio} – ${b.hora_fin}`), el("td", { class: "num" }, b.reservas), el("td", { class: "num" }, b.usadas)))))
  );
}

function niceStep(maximo) {
  if (maximo <= 5) return 1;
  const bruto = maximo / 4;
  const magnitud = 10 ** Math.floor(Math.log10(bruto));
  const normal = bruto / magnitud;
  return (normal <= 1 ? 1 : normal <= 2 ? 2 : normal <= 5 ? 5 : 10) * magnitud;
}

// Redibuja el gráfico si cambia el ancho (girar el teléfono, cambiar el tamaño de la ventana)
let anchoAnterior = 0;
let espera = null;
new ResizeObserver(([entrada]) => {
  const ancho = Math.round(entrada.contentRect.width);
  if (!ultimoPico || Math.abs(ancho - anchoAnterior) < 8) return;
  anchoAnterior = ancho;
  clearTimeout(espera);
  espera = setTimeout(() => pintarGrafico(ultimoPico), 120);
}).observe($("#grafico"));

// ---------- Tabla por sala (tarjetas en el teléfono) ----------
function barra(s) {
  const total = s.usadas + s.no_usadas + s.pendientes;
  if (!total) return el("span", { class: "campo__ayuda" }, "sin reservas");
  const tramo = (valor, color, nombre) =>
    valor ? el("span", { style: `width:${(valor / total) * 100}%;background:${color}`, title: `${nombre}: ${valor}` }) : null;
  return el("div", { class: "barra-apilada", role: "img",
    "aria-label": `${s.usadas} usadas, ${s.no_usadas} no usadas, ${s.pendientes} pendientes` },
    tramo(s.usadas, "var(--serie-usadas)", "Usadas"),
    tramo(s.no_usadas, "var(--serie-no-usadas)", "No usadas"),
    tramo(s.pendientes, "var(--serie-pendientes)", "Pendientes"));
}

const COLUMNAS = ["Sala", "Capacidad", "Reservas", "Usadas", "No usadas", "Pendientes", "Canceladas", "Horas usadas", "Tasa de uso", "Distribución"];

function pintarTablaSalas(reporte) {
  const t = reporte.totales;
  const fila = (titulo, s, capacidad, conBarra) =>
    el("tr", {},
      celda("Sala", titulo, "celda-titulo"),
      celda("Capacidad", capacidad, "num"),
      celda("Reservas", s.reservas, "num"),
      celda("Usadas", s.usadas, "num"),
      celda("No usadas", s.no_usadas, "num"),
      celda("Pendientes", s.pendientes, "num"),
      celda("Canceladas", s.canceladas, "num"),
      celda("Horas usadas", s.horas_usadas, "num"),
      celda("Tasa de uso", pct(s.tasa_uso), "num"),
      celda("Distribución", conBarra ? barra(s) : ""));
  $("#tabla-salas").replaceChildren(
    el("table", { class: "tabla tabla--tarjetas" },
      el("thead", {}, el("tr", {}, COLUMNAS.map((c, i) => el("th", { class: i > 0 && i < 9 ? "num" : "" }, c)))),
      el("tbody", {}, reporte.por_sala.map((s) =>
        fila([el("strong", {}, s.nombre), s.activa ? "" : el("span", { class: "campo__ayuda" }, " (inactiva)")], s, s.capacidad, true))),
      reporte.por_sala.length > 1 ? el("tfoot", {}, fila(el("strong", {}, "Total"), t, "", false)) : null)
  );
}

$("#exportar").addEventListener("click", () => {
  if (!ultimoReporte) return;
  const filas = [["Sala", "Capacidad", "Reservas", "Usadas", "No usadas", "Pendientes", "Canceladas", "Horas usadas", "Tasa de uso (%)"]];
  for (const s of ultimoReporte.por_sala) {
    filas.push([s.nombre, s.capacidad, s.reservas, s.usadas, s.no_usadas, s.pendientes, s.canceladas, s.horas_usadas, s.tasa_uso ?? ""]);
  }
  descargarCsv(`reporte_${ultimoReporte.desde}_${ultimoReporte.hasta}.csv`, filas);
});

form.addEventListener("submit", (e) => { e.preventDefault(); cargar(); });
form.sala_id.addEventListener("change", cargar);
form.querySelectorAll("[data-dias]").forEach((boton) =>
  boton.addEventListener("click", () => {
    form.desde.value = sumarDias(form.hasta.value, -(Number(boton.dataset.dias) - 1));
    cargar();
  })
);

(async () => {
  const p = new URLSearchParams(location.search);
  try {
    const [info, salas] = await Promise.all([infoServidor(), get("/salas", { incluir_inactivas: 1 })]);
    const hoy = info.ahora.slice(0, 10);
    form.hasta.value = p.get("hasta") || hoy;
    form.desde.value = p.get("desde") || sumarDias(hoy, -13);
    form.sala_id.append(...salas.map((s) => el("option", { value: s.id }, s.nombre + (s.activa ? "" : " (inactiva)"))));
    form.sala_id.value = p.get("sala_id") || "";
  } catch (error) {
    $("#mensaje").replaceChildren(avisoError(error, "No se pudo preparar el reporte"));
    return;
  }
  cargar();
})();
