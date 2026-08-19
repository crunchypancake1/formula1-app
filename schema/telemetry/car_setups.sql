-- Car setup library (deduplicated by hash + track + driver)
-- Source: Car Setup packet (Packet 5)
--
-- Online you only ever receive your own setup — other players' entries arrive
-- as all zeroes regardless of their telemetry setting, and spectators get
-- none. The listener detects the all-zero case and does not persist it, so
-- every row here is a real setup.
CREATE TABLE IF NOT EXISTS telemetry.car_setups (
    setup_id        SERIAL PRIMARY KEY,
    setup_hash      BYTEA NOT NULL,
    track_id        SMALLINT NOT NULL,
    user_id         INTEGER,
    session_uid     VARCHAR(20),
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Aerodynamics
    front_wing      SMALLINT NOT NULL,
    rear_wing       SMALLINT NOT NULL,

    -- Transmission / Differential
    on_throttle     SMALLINT NOT NULL,
    off_throttle    SMALLINT NOT NULL,
    engine_braking  SMALLINT NOT NULL,

    -- Suspension Geometry
    front_camber    REAL NOT NULL,
    rear_camber     REAL NOT NULL,
    front_toe       REAL NOT NULL,
    rear_toe        REAL NOT NULL,

    -- Suspension
    front_suspension        SMALLINT NOT NULL,
    rear_suspension         SMALLINT NOT NULL,
    front_anti_roll_bar     SMALLINT NOT NULL,
    rear_anti_roll_bar      SMALLINT NOT NULL,
    front_ride_height       SMALLINT NOT NULL,
    rear_ride_height        SMALLINT NOT NULL,

    -- Brakes
    brake_pressure  SMALLINT NOT NULL,
    brake_bias      SMALLINT NOT NULL,

    -- Tyres
    front_left_tyre_pressure  REAL NOT NULL,
    front_right_tyre_pressure REAL NOT NULL,
    rear_left_tyre_pressure   REAL NOT NULL,
    rear_right_tyre_pressure  REAL NOT NULL,

    -- Other
    ballast         SMALLINT NOT NULL,
    fuel_load       REAL NOT NULL,

    UNIQUE (setup_hash, track_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_car_setups_track ON telemetry.car_setups(track_id);
CREATE INDEX IF NOT EXISTS idx_car_setups_session_driver
    ON telemetry.car_setups (session_uid, user_id);
