// Cliente de la API: agrega la sesión, convierte JSON y unifica los errores.
import { API_URL } from "./config.js";
import { cerrarSesion, obtenerSesion } from "./sesion.js";

export class ApiError extends Error {
  constructor(status, error = {}) {
    super(error.mensaje || "Ocurrió un error.");
    this.status = status;
    this.codigo = error.codigo || "ERROR";
    this.campo = error.campo || null;
    this.sugerencias = error.sugerencias || {};
  }
}

export async function api(ruta, { metodo = "GET", cuerpo, consulta } = {}) {
  const url = new URL(API_URL + ruta);
  if (consulta) {
    for (const [clave, valor] of Object.entries(consulta)) {
      if (valor !== undefined && valor !== null && valor !== "") url.searchParams.set(clave, valor);
    }
  }
  const cabeceras = { Accept: "application/json" };
  const sesion = obtenerSesion();
  if (sesion) cabeceras["X-Usuario-Id"] = String(sesion.id);
  if (cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";

  let respuesta;
  try {
    respuesta = await fetch(url, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    });
  } catch {
    throw new ApiError(0, {
      codigo: "SIN_CONEXION",
      mensaje: `No se pudo conectar con el servidor (${API_URL}). Revisa que el backend esté corriendo.`,
    });
  }

  if (respuesta.status === 204) return null;
  let datos = null;
  try {
    datos = await respuesta.json();
  } catch {
    datos = null;
  }

  if (respuesta.status === 401 && sesion) {
    cerrarSesion();
    location.replace("index.html?sesion=expirada");
  }
  if (!respuesta.ok) throw new ApiError(respuesta.status, datos?.error);
  return datos;
}

export const get = (ruta, consulta) => api(ruta, { consulta });
export const post = (ruta, cuerpo = {}) => api(ruta, { metodo: "POST", cuerpo });
export const put = (ruta, cuerpo = {}) => api(ruta, { metodo: "PUT", cuerpo });
export const del = (ruta) => api(ruta, { metodo: "DELETE" });
