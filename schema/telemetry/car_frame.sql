-- Combined car frame (Motion 0 + Lap Data 2 + Car Telemetry 6 + Car Status 7
-- + Car Telemetry 2 16). One row per simulation frame per driver.
--
-- Car Damage (10) is split out to telemetry.car_frame_damage because the whole
-- packet is withheld for a Restricted driver, and Motion Ex (13) to
-- telemetry.car_frame_motion_ex because it only ever describes the player.
--
-- timestamp is derived (sessions.session_start_utc + session_time), never
-- clock_timestamp(), so the primary key below actually de-duplicates a frame
-- that arrives twice — a re-delivered datagram, a stale-frame sweep racing a
-- normal flush, or a listener restart mid-session.
--
-- Columns marked "restricted" are zeroed by the game for any *other* driver
-- whose Your Telemetry setting is Restricted. The listener stores NULL for
-- those, never the game's fake 0.

CREATE TABLE IF NOT EXISTS telemetry.car_frame (
    -- Meta
    timestamp                   TIMESTAMPTZ NOT NULL,
    session_uid                 VARCHAR(255) NOT NULL,
    user_id                     INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    overall_frame_identifier    INTEGER NOT NULL,

    -- Motion / Packet 0 (direction vectors normalised from int16 to -1.0..1.0,
    -- g-forces de-quantised from int16 by /1000.0)
    world_pos_x REAL, world_pos_y REAL, world_pos_z REAL,
    world_velocity_x REAL, world_velocity_y REAL, world_velocity_z REAL,
    world_forward_dir_x REAL, world_forward_dir_y REAL, world_forward_dir_z REAL,
    world_right_dir_x REAL, world_right_dir_y REAL, world_right_dir_z REAL,
    g_force_lateral REAL, g_force_longitudinal REAL, g_force_vertical REAL,
    yaw REAL, pitch REAL, roll REAL,

    -- Car Telemetry / Packet 6: scalars
    speed INTEGER,
    throttle REAL, steer REAL, brake REAL,
    clutch SMALLINT, gear SMALLINT,
    engine_rpm INTEGER, drs BOOLEAN,
    rev_lights_percent SMALLINT, rev_lights_bit_value INTEGER,
    engine_temperature SMALLINT,

    -- Car Telemetry / Packet 6: per-wheel (RL, RR, FL, FR — the game's order)
    brakes_temp_rl INTEGER, brakes_temp_rr INTEGER, brakes_temp_fl INTEGER, brakes_temp_fr INTEGER,
    tyres_surface_temp_rl SMALLINT, tyres_surface_temp_rr SMALLINT, tyres_surface_temp_fl SMALLINT, tyres_surface_temp_fr SMALLINT,
    tyres_inner_temp_rl SMALLINT, tyres_inner_temp_rr SMALLINT, tyres_inner_temp_fl SMALLINT, tyres_inner_temp_fr SMALLINT,
    tyres_pressure_rl REAL, tyres_pressure_rr REAL, tyres_pressure_fl REAL, tyres_pressure_fr REAL,
    surface_type_rl VARCHAR(20), surface_type_rr VARCHAR(20), surface_type_fl VARCHAR(20), surface_type_fr VARCHAR(20),

    -- Car Telemetry / Packet 6: packet-level, player car only (NULL elsewhere).
    -- 255 = MFD closed; suggested_gear 0 = none suggested.
    mfd_panel_index SMALLINT,
    mfd_panel_index_secondary_player SMALLINT,
    suggested_gear SMALLINT,

    -- Lap Data / Packet 2: timing (minutes/ms split fields already recombined)
    last_lap_time_ms BIGINT,
    current_lap_time_ms BIGINT,
    sector1_time_ms INTEGER,
    sector2_time_ms INTEGER,
    lap_distance REAL,
    total_distance REAL,
    safety_car_delta REAL,

    -- Lap Data / Packet 2: position and state
    position SMALLINT,
    grid_position SMALLINT,
    current_lap_num SMALLINT,
    sector VARCHAR(10),
    pit_status VARCHAR(20),
    driver_status VARCHAR(20),
    result_status VARCHAR(20),
    current_lap_invalid BOOLEAN,

    -- Lap Data / Packet 2: gaps (gap_to_car_behind_ms is derived from the car
    -- one position back, which reports it as its own gap-to-car-ahead)
    gap_to_leader_ms INTEGER,
    gap_to_car_ahead_ms INTEGER,
    gap_to_car_behind_ms INTEGER,

    -- Lap Data / Packet 2: pit
    num_pit_stops SMALLINT,
    pit_lane_timer_active BOOLEAN,
    pit_lane_time_ms INTEGER,
    pit_stop_time_ms INTEGER,
    pit_stop_should_serve_pen BOOLEAN,

    -- Lap Data / Packet 2: penalties and warnings
    penalties_seconds SMALLINT,
    total_warnings SMALLINT,
    corner_cutting_warnings SMALLINT,
    num_unserved_drive_through_pens SMALLINT,
    num_unserved_stop_go_pens SMALLINT,

    -- Lap Data / Packet 2: speed trap bests for this car
    speed_trap_fastest_speed REAL,
    speed_trap_fastest_lap SMALLINT,

    -- Car Status / Packet 7: never restricted
    pit_limiter BOOLEAN,
    drs_allowed BOOLEAN,
    drs_activation_distance INTEGER,
    actual_tyre_compound VARCHAR(30),
    visual_tyre_compound VARCHAR(30),
    tyres_age_laps SMALLINT,
    vehicle_fia_flags VARCHAR(20),
    network_paused BOOLEAN,
    traction_control SMALLINT,
    anti_lock_brakes BOOLEAN,
    max_rpm INTEGER,
    idle_rpm INTEGER,
    max_gears SMALLINT,

    -- Car Status / Packet 7: restricted (NULL for a Restricted driver)
    front_brake_bias SMALLINT,
    fuel_mix SMALLINT,
    fuel_in_tank REAL,
    fuel_capacity REAL,
    fuel_remaining_laps REAL,
    ers_store_energy REAL,
    ers_deploy_mode SMALLINT,
    ers_deployed_this_lap REAL,
    ers_harvest_limit_per_lap REAL,
    ers_harvested_this_lap_mguk REAL,
    ers_harvested_this_lap_mguh REAL,
    engine_power_ice REAL,
    engine_power_mguk REAL,

    -- Car Telemetry 2 / Packet 16. The aero and boost fields are only
    -- meaningful when is_2026_regulations is true; on a classic or F2 car they
    -- are stored NULL rather than a misleading 0.
    active_aero_mode SMALLINT,
    active_aero_available BOOLEAN,
    active_aero_activation_distance INTEGER,
    overtake_available BOOLEAN,
    overtake_active BOOLEAN,
    overtake_activation_distance INTEGER,
    is_2026_regulations BOOLEAN,
    driving_wrong_way BOOLEAN,

    PRIMARY KEY (timestamp, session_uid, user_id, overall_frame_identifier)
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
