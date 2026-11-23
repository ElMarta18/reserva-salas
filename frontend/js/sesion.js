// Inicio de sesión simulado: se guarda el usuario elegido en el navegador.
const CLAVE = "reservas.sesion";

export function obtenerSesion() {
  try {
    const texto = localStorage.getItem(CLAVE);
    return texto ? JSON.parse(texto) : null;
  } catch {
    return null;
  }
}

export function guardarSesion(usuario) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(usuario));
  } catch {
    /* almacenamiento no disponible: la sesión dura solo esta página */
  }
}

export function cerrarSesion() {
  try {
    localStorage.removeItem(CLAVE);
  } catch {
    /* nada que limpiar */
  }
}

export function paginaInicio(usuario) {
  return usuario?.rol === "biblioteca" ? "reporte.html" : "disponibilidad.html";
}

// Exige sesión y, opcionalmente, uno de los roles. Si no cumple, redirige.
export function requerirSesion(roles = []) {
  const usuario = obtenerSesion();
  if (!usuario) {
    location.replace("index.html");
    throw new Error("Sin sesión");
  }
  if (roles.length && !roles.includes(usuario.rol)) {
    location.replace(paginaInicio(usuario));
    throw new Error("Rol sin permiso");
  }
  return usuario;
}
