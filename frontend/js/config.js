// Dirección del backend.
// Por defecto usa el mismo equipo desde el que se abrió la página, en el puerto 5000:
//   · en el computador:      http://localhost:5500      → API http://localhost:5000/api
//   · desde un teléfono:     http://192.168.1.20:5500   → API http://192.168.1.20:5000/api
// Para usar otra dirección, define window.RESERVAS_API_URL antes de cargar los scripts.
const PUERTO_API = 5000;
const host = location.hostname || "localhost";
const protocolo = location.protocol === "https:" ? "https:" : "http:";

export const API_URL = window.RESERVAS_API_URL || `${protocolo}//${host}:${PUERTO_API}/api`;
