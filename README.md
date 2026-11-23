# Sistema de Reservas de Salas de Estudio

Taller de Ingeniería de Software · Proyecto Integrador 2026 · Grupo 3

Aplicación web para reservar salas de estudio de biblioteca por bloques de 1 hora.
Incluye confirmación de llegada, liberación automática a los 15 minutos y reporte de uso.

- **Backend:** Python 3.10+, Flask y SQLite. Es una API JSON organizada en capas.
- **Frontend:** HTML, CSS y JavaScript sin frameworks. Se sirve aparte y consume la API.

```
reservas-salas-estudio/
├── backend/
│   ├── reservas/
│   │   ├── __init__.py          create_app() y comando init-db
│   │   ├── config.py            configuración por variables de entorno
│   │   ├── api/                 CAPA 2 · Controlador: rutas Flask (un módulo por recurso)
│   │   │   ├── auth.py          salud e inicio de sesión simulado
│   │   │   ├── salas.py         RF01
│   │   │   ├── usuarios.py      RF02
│   │   │   ├── disponibilidad.py RF03
│   │   │   ├── reservas.py      RF04 a RF08
│   │   │   ├── reportes.py      RF09 y RF10
│   │   │   └── sesion.py        cabecera X-Usuario-Id y control de roles
│   │   ├── servicio/            CAPA 3 · Negocio (no depende de Flask)
│   │   │   ├── reglas.py        RN1 a RN6
│   │   │   ├── reservas.py      crear, cancelar, confirmar y liberar
│   │   │   ├── disponibilidad.py
│   │   │   ├── reportes.py
│   │   │   ├── salas.py
│   │   │   └── usuarios.py
│   │   ├── db.py                CAPA 4 · Datos: conexión y transacciones sqlite3
│   │   ├── schema.sql           CAPA 5 · Persistencia: 3 tablas, CHECK y disparador anti-traslape
│   │   ├── datos_ficticios.py   salas, usuarios e historial de demostración
│   │   ├── errores.py           errores de negocio y su código HTTP
│   │   └── reloj.py             hora del sistema (se puede fijar para demos)
│   ├── tests/                   61 pruebas pytest
│   ├── run.py                   API en el puerto 5000 (accesible desde la red)
│   └── requirements.txt
├── iniciar.py                   inicia API + frontend y muestra la dirección y QR para el teléfono
└── frontend/                    CAPA 1 · Interfaz (mobile-first)
    ├── servidor.py              sirve el frontend a la red, sin caché
    ├── index.html               inicio de sesión simulado
    ├── disponibilidad.html      RF03
    ├── nueva-reserva.html       RF04 (3 pasos)
    ├── mis-reservas.html        RF05, RF06 y RF08
    ├── reporte.html             RF09 y RF10
    ├── salas.html               RF01
    ├── usuarios.html            RF02
    ├── css/estilos.css
    ├── img/ · manifest.webmanifest   ícono para la pantalla de inicio del teléfono
    └── js/
        ├── config.js            URL de la API (se deduce de la dirección con que se abrió la página)
        ├── api.js  sesion.js  ui.js
        └── paginas/             un módulo por pantalla
```

---

## Cómo ejecutarlo

Necesitas Python 3.10 o superior. La aplicación está pensada primero para el teléfono, pero también funciona en cualquier computador.

### 1. Instalar (solo la primera vez)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
cd ..
```

> Usa `python -m pip` y no solo `pip`. Así la instalación queda dentro de `.venv`.

### 2. Iniciar todo con un comando

Ejecuta lo siguiente desde la carpeta raíz del proyecto, con el entorno activado:

```powershell
python iniciar.py
```

El comando levanta los dos servidores. Siguen siendo independientes: la API corre en el puerto **5000** y el frontend en el **5500**.
Además muestra dos direcciones:

```
  En este computador:   http://localhost:5500
  Teléfono / otro PC:   http://192.168.1.20:5500     ← la IP de tu red
```

y un **código QR** que puedes escanear con la cámara del teléfono.
Para detener los dos servidores, presiona `Ctrl+C`.

### 3. Abrirlo en el teléfono o en otro computador

1. Conecta el teléfono o el otro computador **a la misma red Wi-Fi** que el computador que ejecuta el proyecto.
2. Abre la dirección «Teléfono / otro PC» o escanea el QR.
3. **Windows:** la primera vez aparece un aviso del Firewall para Python. Marca **Redes privadas** y presiona *Permitir*.
   Si lo rechazaste, ve a *Firewall de Windows → Permitir una aplicación* y habilita `python.exe` en redes privadas.
   También revisa que tu Wi-Fi esté configurada como red **privada**, no pública.

> Las redes públicas o de la universidad suelen aislar los dispositivos entre sí.
> Si el teléfono no abre la página en esa red, comparte internet desde el teléfono (*hotspot*) y conecta el computador a esa red.

En el teléfono puedes usar *Compartir → Agregar a pantalla de inicio* para abrirlo como si fuera una app.

### Alternativa: dos terminales

```powershell
# Terminal 1
cd backend
python run.py                 # API en http://0.0.0.0:5000

# Terminal 2
cd frontend
python servidor.py            # frontend en http://0.0.0.0:5500, sin caché
```

### Base de datos y pruebas

La primera vez se crea `backend/instancia/reservas.db` con datos ficticios.

```bash
cd backend
flask --app reservas init-db           # borra todo y carga datos ficticios
flask --app reservas init-db --vacia   # solo las tablas
python -m pytest                       # 61 pruebas
```

---

## Diseño para teléfono (mobile-first)

Los estilos parten del teléfono. Desde 760 px de ancho se amplían para tablet y computador.

| Pantalla | Teléfono | Computador |
|---|---|---|
| Navegación | barra inferior con íconos, al alcance del pulgar | menú en la cabecera |
| Disponibilidad | una tarjeta por sala con bloques táctiles | grilla salas × horas |
| Nueva reserva | pasos apilados, botones − / + para las personas | pasos y resumen lateral fijo |
| Mis reservas | tarjetas con botones a todo el ancho | lista con acciones a la derecha |
| Reporte | indicadores en 2 columnas; el gráfico se ajusta al ancho y se toca para ver el detalle | 6 indicadores en una fila; detalle al pasar el mouse |
| Salas, usuarios, reporte por sala | cada fila se convierte en una tarjeta | tablas |

Otros detalles de la versión para teléfono:

- Los objetivos táctiles miden al menos 44 px.
- Los campos usan letra de 16 px para que iOS no haga zoom.
- La barra inferior respeta la zona segura del iPhone.
- La vista se adapta al girar el teléfono.
- Hay ícono para la pantalla de inicio.

---

## Usuarios de prueba

| Usuario | Correo | Rol |
|---|---|---|
| Paula Fernández | biblioteca@demo.cl | Biblioteca |
| Ana Muñoz | ana.munoz@alumnos.demo.cl | Estudiante |
| Benjamín Soto | benjamin.soto@alumnos.demo.cl | Estudiante |
| Camila Rojas | camila.rojas@alumnos.demo.cl | Estudiante |
| Diego Pérez | diego.perez@alumnos.demo.cl | Estudiante |
| Elena Castro | elena.castro@alumnos.demo.cl | Estudiante |
| Felipe Díaz | felipe.diaz@alumnos.demo.cl | Estudiante |

Salas: A (4 personas), B (6), C (8), D (12) y E (2, inactiva).

Los datos ficticios incluyen un historial de 14 días hábiles para que el reporte tenga datos.
También incluyen reservas futuras para que la grilla muestre bloques ocupados.

## Demostrar la confirmación y la liberación

La hora del sistema se puede fijar con `RESERVAS_AHORA`. Por ejemplo, para mostrar la confirmación en vivo:

```bash
# Windows PowerShell:  $env:RESERVAS_AHORA="2026-11-25 10:05"; python iniciar.py
RESERVAS_AHORA="2026-11-25 10:05" python iniciar.py
```

1. Arranca normalmente y reserva un bloque para mañana a las 10:00 como estudiante.
2. Reinicia el backend con `RESERVAS_AHORA` fijada en ese día a las 10:05. En «Mis reservas» aparece el botón **Confirmar llegada**.
3. Reinicia con 10:16 (o cualquier hora después de las 10:15). La reserva aparece como **liberada** y el bloque vuelve a estar libre.

Para que la reserva de mañana caiga en la fecha de la demo, crea la base una sola vez y no la borres entre reinicios.

---

## Trazabilidad

### Requisitos funcionales

| RF | Requisito | Backend | Frontend |
|---|---|---|---|
| RF01 | Registrar y administrar salas | `servicio/salas.py`, `api/salas.py` | `salas.html` |
| RF02 | Registrar usuarios con su rol | `servicio/usuarios.py`, `api/usuarios.py` | `usuarios.html` |
| RF03 | Consultar disponibilidad por fecha y sala | `servicio/disponibilidad.py` | `disponibilidad.html` |
| RF04 | Crear reserva validando RN1 a RN4 | `servicio/reservas.py::crear_reserva` | `nueva-reserva.html` |
| RF05 | Cancelar antes del inicio | `servicio/reservas.py::cancelar_reserva` | `mis-reservas.html` |
| RF06 | Confirmar llegada en 15 minutos | `servicio/reservas.py::confirmar_llegada` | `mis-reservas.html` |
| RF07 | Liberar reservas no confirmadas | `servicio/reservas.py::actualizar_estados` (antes de cada petición) | refresco automático |
| RF08 | Ver «Mis reservas» con su estado | `servicio/reservas.py::mis_reservas` | `mis-reservas.html` |
| RF09 | Reporte de uso por sala y rango | `servicio/reportes.py::reporte_uso` | `reporte.html` (+ CSV) |
| RF10 | Gráfico de horas pico y filtros | `servicio/reportes.py::horas_pico` | `reporte.html` |

### Reglas de negocio

| Regla | Dónde se valida |
|---|---|
| RN1 Sin traslapes (`inicio < fin_otro` y `fin > inicio_otro`) | `reglas.hay_choque` y el disparador `reserva_sin_traslape` en `schema.sql` |
| RN2 Bloques de 1 hora, 08:00 a 21:00, máximo 2 horas seguidas | `reglas.validar_bloque`, `reglas.horas_seguidas_con_propias` y CHECK en `schema.sql` |
| RN3 Capacidad | `reglas.excede_capacidad` |
| RN4 Máximo 2 reservas vigentes | `reglas.contar_vigentes` |
| RN5 Confirmar entre el inicio y 15 minutos después | `reglas.puede_confirmar` y `actualizar_estados` |
| RN6 Cancela solo el titular, antes del inicio | `reglas.puede_cancelar` y `cancelar_reserva` |

### Flujos alternativos de CU02

| Flujo | Respuesta de la API (409) | Qué hace la interfaz |
|---|---|---|
| A1 Horario ocupado | `RN1_CHOQUE` + `sugerencias.bloques_libres` | botones con los bloques libres de esa sala |
| A2 Supera la capacidad | `RN3_CAPACIDAD` + `sugerencias.salas` | botones con salas más grandes libres a esa hora |
| A3 Ya tiene 2 reservas | `RN4_LIMITE` | enlace a «Mis reservas» |

### Criterios de aceptación

CA01 a CA06 están en `tests/test_servicio.py` con el mismo nombre. La prueba
`tests/test_rendimiento.py` carga 1.000 reservas. Con esa carga verifica RNF04
(cada consulta responde en menos de 2 s) y RNF01 (no queda ninguna reserva superpuesta).

---

## API

Todas las rutas van bajo `/api`, salvo `GET /`. Para identificar al usuario se envía la cabecera `X-Usuario-Id`
(inicio de sesión simulado). Los errores tienen este formato:
`{"error": {"codigo", "mensaje", "campo"?, "sugerencias"?}}`.

| Método | Ruta | Rol | RF |
|---|---|---|---|
| GET | `/salud` | público | hora del sistema y parámetros de las reglas |
| GET | `/auth/usuarios-demo` | público | lista para el inicio de sesión simulado |
| POST | `/auth/login` | público | `{correo}` → usuario |
| GET | `/salas` (`?incluir_inactivas=1`) | ambos | RF01 |
| POST · PUT · DELETE | `/salas[/{id}]` | biblioteca | RF01 |
| GET · POST · PUT · DELETE | `/usuarios[/{id}]` | biblioteca | RF02 |
| GET | `/disponibilidad?fecha=` | ambos | RF03 |
| GET | `/disponibilidad/{sala}/bloques-libres?fecha=&duracion=` | ambos | RF03/RF04 |
| POST | `/reservas` | estudiante | RF04 · **201** creada · **409** regla · **400** datos |
| GET | `/reservas/mias` | estudiante | RF08 |
| GET | `/reservas?desde=&hasta=&sala_id=&estado=` | biblioteca | listado |
| POST | `/reservas/{id}/cancelar` | estudiante | RF05 |
| POST | `/reservas/{id}/confirmar` | estudiante | RF06 |
| GET | `/reporte?desde=&hasta=&sala_id=` | biblioteca | RF09 |
| GET | `/reporte/horas-pico?desde=&hasta=&sala_id=` | biblioteca | RF10 |

Códigos: 401 sin sesión · 403 rol sin permiso o no es el titular · 404 no existe.

---

## Configuración (variables de entorno del backend)

| Variable | Por defecto | Uso |
|---|---|---|
| `RESERVAS_DB` | `backend/instancia/reservas.db` | archivo SQLite |
| `RESERVAS_HOST` | `0.0.0.0` | `0.0.0.0` acepta teléfonos y otros PC de la red; `127.0.0.1` = solo este computador |
| `RESERVAS_CORS_RED_LOCAL` | `1` | permite llamar a la API desde cualquier dirección de la red local (192.168.x, 10.x, 172.16–31.x, localhost) |
| `RESERVAS_CORS` | (vacío) | orígenes extra permitidos, separados por coma (`*` = cualquiera) |
| `RESERVAS_AHORA` | (hora real) | fija la hora del sistema para demostraciones |
| `RESERVAS_AUTO_INIT` | `1` | crea la base con datos ficticios si no existe |
| `PORT` | `5000` | puerto de la API |
| `PUERTO_WEB` | `5500` | puerto del frontend en `iniciar.py` |

---

## Decisiones de diseño que precisan la presentación

- **Ciclo de vida.** Antes de cada petición, el servidor marca como «liberada» toda reserva activa cuyo inicio + 15 minutos ya pasó (RN5).
  En el mismo paso marca como «finalizada» toda reserva confirmada cuyo bloque terminó.
- **Ventana de confirmación inclusiva.** En un bloque de las 10:00 se puede confirmar desde las 10:00:00 hasta las 10:15:00.
  A las 10:15:01 la reserva ya se libera.
- **RN2 entre reservas propias.** Un estudiante no puede encadenar reservas para superar 2 horas seguidas.
  Por ejemplo, 10–12 y luego 12–13. Esto vale aunque las reservas sean en salas distintas.
  Tampoco puede estar en dos salas a la vez.
- **Solo bloques futuros.** No se puede reservar un bloque que ya comenzó.
- **Salas e historial.** Una sala con reservas no se elimina: se desactiva y deja de recibir reservas nuevas.
  Lo mismo aplica a los usuarios con historial.
- **Concurrencia.** La creación de una reserva usa `BEGIN IMMEDIATE`, así dos peticiones simultáneas no pueden validar el mismo bloque a la vez.
  Además, un disparador en la base rechaza cualquier traslape aunque se salte la capa de negocio.
