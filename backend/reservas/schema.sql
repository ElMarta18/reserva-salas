-- Modelo de datos · Sistema de Reservas de Salas de Estudio
-- Tres tablas: usuario, sala y reserva.
-- Las reglas de integridad también viven en la base (RNF01).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT    NOT NULL CHECK (length(trim(nombre)) > 0),
    correo  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    rol     TEXT    NOT NULL CHECK (rol IN ('estudiante', 'biblioteca'))
);

CREATE TABLE IF NOT EXISTS sala (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (length(trim(nombre)) > 0),
    capacidad  INTEGER NOT NULL CHECK (capacidad > 0),
    ubicacion  TEXT    NOT NULL DEFAULT '',
    activa     INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1))
);

CREATE TABLE IF NOT EXISTS reserva (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuario (id),
    sala_id        INTEGER NOT NULL REFERENCES sala (id),
    fecha          TEXT    NOT NULL CHECK (fecha GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    hora_inicio    TEXT    NOT NULL CHECK (hora_inicio GLOB '[0-2][0-9]:00'),
    hora_fin       TEXT    NOT NULL CHECK (hora_fin GLOB '[0-2][0-9]:00'),
    asistentes     INTEGER NOT NULL CHECK (asistentes > 0),
    estado         TEXT    NOT NULL DEFAULT 'activa'
                   CHECK (estado IN ('activa', 'confirmada', 'cancelada', 'liberada', 'finalizada')),
    creada_en      TEXT    NOT NULL,
    confirmada_en  TEXT,
    -- RN2 a nivel de base: dentro del horario y con fin posterior al inicio
    CHECK (hora_inicio >= '08:00' AND hora_fin <= '21:00' AND hora_inicio < hora_fin)
);

-- Índice (sala_id, fecha) para detectar choques rápido
CREATE INDEX IF NOT EXISTS idx_reserva_sala_fecha     ON reserva (sala_id, fecha);
CREATE INDEX IF NOT EXISTS idx_reserva_usuario_estado ON reserva (usuario_id, estado);
CREATE INDEX IF NOT EXISTS idx_reserva_estado_fecha   ON reserva (estado, fecha);

-- RN1 como última línea de defensa: aunque la capa de negocio falle,
-- la base nunca acepta dos reservas que ocupan la misma sala al mismo tiempo.
CREATE TRIGGER IF NOT EXISTS reserva_sin_traslape
BEFORE INSERT ON reserva
WHEN NEW.estado IN ('activa', 'confirmada')
BEGIN
    SELECT RAISE(ABORT, 'RN1: la sala ya está reservada en ese horario')
    WHERE EXISTS (
        SELECT 1 FROM reserva
        WHERE sala_id = NEW.sala_id
          AND fecha = NEW.fecha
          AND estado IN ('activa', 'confirmada')
          AND hora_inicio < NEW.hora_fin
          AND hora_fin > NEW.hora_inicio
    );
END;
