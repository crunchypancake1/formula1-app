-- Combined car frame table (Motion + Telemetry + Lap Data + Car Status + Car Damage)
-- One row per frame per driver. All same-frequency packets in a single row.

CREATE TABLE IF NOT EXISTS telemetry.car_frame (
    -- Meta
    timestamp                   TIMESTAMPTZ NOT NULL,
    session_uid                 VARCHAR(255) NOT NULL,
    user_id                   INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    overall_frame_identifier    INTEGER NOT NULL,

    -- Motion / Packet 0
    world_pos_x REAL, world_pos_y REAL, world_pos_z REAL,
    world_velocity_x REAL, world_velocity_y REAL, world_velocity_z REAL,
    g_force_lateral REAL, g_force_longitudinal REAL, g_force_vertical REAL,
    yaw REAL, pitch REAL, roll REAL,

    -- Telemetry / Packet 6: scalars
    speed SMALLINT,
    throttle REAL, steer REAL, brake REAL,
    clutch SMALLINT, gear SMALLINT,
    engine_rpm SMALLINT, drs BOOLEAN,
    engine_temperature SMALLINT,

    -- Telemetry / Packet 6: per-wheel temps (RL=0, RR=1, FL=2, FR=3)
    brakes_temp_rl SMALLINT, brakes_temp_rr SMALLINT, brakes_temp_fl SMALLINT, brakes_temp_fr SMALLINT,
    tyres_surface_temp_rl SMALLINT, tyres_surface_temp_rr SMALLINT, tyres_surface_temp_fl SMALLINT, tyres_surface_temp_fr SMALLINT,
    tyres_inner_temp_rl SMALLINT, tyres_inner_temp_rr SMALLINT, tyres_inner_temp_fl SMALLINT, tyres_inner_temp_fr SMALLINT,
    tyres_pressure_rl REAL, tyres_pressure_rr REAL, tyres_pressure_fl REAL, tyres_pressure_fr REAL,

    -- Telemetry / Packet 6: per-wheel surface type (enum resolved to string)
    surface_type_rl VARCHAR(20), surface_type_rr VARCHAR(20), surface_type_fl VARCHAR(20), surface_type_fr VARCHAR(20),

    -- Lap Data / Packet 2: scalars
    current_lap_num SMALLINT,
    lap_distance REAL,
    current_lap_time_ms INTEGER,
    position SMALLINT,

    -- Lap Data / Packet 2: enums resolved to strings
    sector VARCHAR(10),
    pit_status VARCHAR(20),
    driver_status VARCHAR(20),
    result_status VARCHAR(20),

    -- Lap Data / Packet 2: gaps and pit timing
    gap_to_leader_ms INTEGER,
    gap_to_car_ahead_ms INTEGER,
    gap_to_car_behind_ms INTEGER,
    total_distance REAL,
    safety_car_delta REAL,
    num_pit_stops SMALLINT,
    pit_lane_timer_active BOOLEAN,
    pit_lane_time_ms SMALLINT,
    pit_stop_time_ms SMALLINT,
    pit_stop_should_serve_pen BOOLEAN,

    -- Car Status / Packet 7
    pit_limiter BOOLEAN,
    drs_allowed BOOLEAN,
    drs_activation_distance SMALLINT,
    actual_tyre_compound VARCHAR(30),
    visual_tyre_compound VARCHAR(30),
    tyres_age_laps SMALLINT,
    vehicle_fia_flags VARCHAR(20),
    network_paused BOOLEAN,

    -- Car Status / Packet 7: ERS/fuel/brake-bias
    front_brake_bias SMALLINT,
    fuel_in_tank REAL,
    fuel_remaining_laps REAL,
    ers_store_energy REAL,
    ers_deploy_mode SMALLINT,
    ers_deployed_this_lap REAL,

    PRIMARY KEY (timestamp, session_uid, user_id)
);

SELECT create_hypertable(
    'telemetry.car_frame', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

ALTER TABLE telemetry.car_frame SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'session_uid, user_id',
    timescaledb.compress_orderby = 'overall_frame_identifier DESC'
);

SELECT add_compression_policy('telemetry.car_frame', INTERVAL '7 days', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_car_frame_session_driver_frame
    ON telemetry.car_frame(session_uid, user_id, overall_frame_identifier DESC);
