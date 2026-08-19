-- Car Damage (Packet 10) — 10Hz. Joins telemetry.car_frame on
-- (session_uid, user_id, overall_frame_identifier).
--
-- Split out from car_frame because the game withholds every field here for a
-- driver whose Your Telemetry setting is Restricted. Rather than store ~30
-- fake zeroes per frame, the listener omits the row entirely for those cars —
-- so "no row" means "withheld", not "undamaged".
--
-- timestamp is derived (sessions.session_start_utc + session_time), which is
-- what lets the primary key de-duplicate a re-delivered frame.

CREATE TABLE IF NOT EXISTS telemetry.car_frame_damage (
    timestamp               TIMESTAMPTZ NOT NULL,
    session_uid             VARCHAR(20) NOT NULL
                            REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id                 INTEGER NOT NULL,
    session_time            FLOAT NOT NULL,
    overall_frame_identifier INTEGER NOT NULL,

    -- Tyre wear (float, percentage per wheel)
    tyres_wear_rl           REAL,
    tyres_wear_rr           REAL,
    tyres_wear_fl           REAL,
    tyres_wear_fr           REAL,

    -- Tyre damage (uint8, percentage per wheel)
    tyres_damage_rl         SMALLINT,
    tyres_damage_rr         SMALLINT,
    tyres_damage_fl         SMALLINT,
    tyres_damage_fr         SMALLINT,

    -- Brakes damage (uint8, percentage per wheel)
    brakes_damage_rl        SMALLINT,
    brakes_damage_rr        SMALLINT,
    brakes_damage_fl        SMALLINT,
    brakes_damage_fr        SMALLINT,

    -- Tyre blisters (uint8, percentage per wheel)
    tyre_blisters_rl        SMALLINT,
    tyre_blisters_rr        SMALLINT,
    tyre_blisters_fl        SMALLINT,
    tyre_blisters_fr        SMALLINT,

    -- Body damage (uint8, percentage)
    front_left_wing_damage  SMALLINT,
    front_right_wing_damage SMALLINT,
    rear_wing_damage        SMALLINT,
    floor_damage            SMALLINT,
    diffuser_damage         SMALLINT,
    sidepod_damage          SMALLINT,

    -- Faults (boolean)
    drs_fault               BOOLEAN,
    ers_fault               BOOLEAN,

    -- Drivetrain damage (uint8, percentage)
    gearbox_damage          SMALLINT,
    engine_damage           SMALLINT,

    -- Engine component wear (uint8, percentage)
    engine_mguh_wear        SMALLINT,
    engine_es_wear          SMALLINT,
    engine_ce_wear          SMALLINT,
    engine_ice_wear         SMALLINT,
    engine_mguk_wear        SMALLINT,
    engine_tc_wear          SMALLINT,

    -- Engine faults (boolean)
    engine_blown            BOOLEAN,
    engine_seized           BOOLEAN,

    PRIMARY KEY (timestamp, session_uid, user_id, overall_frame_identifier)
);

SELECT create_hypertable(
    'telemetry.car_frame_damage', 'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

ALTER TABLE telemetry.car_frame_damage
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'session_uid, user_id',
         timescaledb.compress_orderby = 'overall_frame_identifier DESC');

SELECT add_compression_policy('telemetry.car_frame_damage',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_car_frame_damage_session_driver_frame
    ON telemetry.car_frame_damage (session_uid, user_id, overall_frame_identifier DESC);
