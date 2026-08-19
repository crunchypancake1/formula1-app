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
--
-- Enum-valued columns hold the game's raw integer, not a resolved name. At this
-- table's row count a name costs ~8 bytes against a SMALLINT's 2, and there are
-- eleven of them. Resolution happens in @f1/db (packages/db/src/enums.ts).
--
-- A native PostgreSQL ENUM type would be the usual answer and is the wrong one
-- here: an unrecognised value must never fail a write (see safe_enum_name), and
-- an enum would reject a member added by a game patch outright. An integer
-- stores anything the game sends and the query layer degrades it to
-- UNKNOWN_<n>, which is the same contract the listener used to apply on write.

CREATE TABLE IF NOT EXISTS telemetry.car_frame (
    -- Meta
    timestamp                   TIMESTAMPTZ NOT NULL,
    session_uid                 VARCHAR(20) NOT NULL
                                REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
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

    -- Car Telemetry / Packet 6: scalars.
    -- speed and engine_rpm are uint16 on the wire and fit SMALLINT;
    -- rev_lights_bit_value is uint16 too but is a bit field, so values above
    -- 32767 are reachable and it stays INTEGER.
    speed SMALLINT,
    throttle REAL, steer REAL, brake REAL,
    clutch SMALLINT, gear SMALLINT,
    engine_rpm SMALLINT, drs BOOLEAN,
    rev_lights_percent SMALLINT, rev_lights_bit_value INTEGER,
    engine_temperature SMALLINT,

    -- Car Telemetry / Packet 6: per-wheel (RL, RR, FL, FR — the game's order)
    brakes_temp_rl SMALLINT, brakes_temp_rr SMALLINT, brakes_temp_fl SMALLINT, brakes_temp_fr SMALLINT,
    tyres_surface_temp_rl SMALLINT, tyres_surface_temp_rr SMALLINT, tyres_surface_temp_fl SMALLINT, tyres_surface_temp_fr SMALLINT,
    tyres_inner_temp_rl SMALLINT, tyres_inner_temp_rr SMALLINT, tyres_inner_temp_fl SMALLINT, tyres_inner_temp_fr SMALLINT,
    tyres_pressure_rl REAL, tyres_pressure_rr REAL, tyres_pressure_fl REAL, tyres_pressure_fr REAL,
    -- SurfaceType code per wheel (0 = TARMAC … 11 = RIDGED)
    surface_type_rl SMALLINT, surface_type_rr SMALLINT, surface_type_fl SMALLINT, surface_type_fr SMALLINT,

    -- Car Telemetry / Packet 6: packet-level, player car only (NULL elsewhere).
    -- 255 = MFD closed; suggested_gear 0 = none suggested.
    mfd_panel_index SMALLINT,
    mfd_panel_index_secondary_player SMALLINT,
    suggested_gear SMALLINT,

    -- Lap Data / Packet 2: timing (minutes/ms split fields already recombined).
    -- uint32 on the wire; INTEGER covers 24 days of milliseconds, and keeping
    -- these out of BIGINT is what stops them arriving in the Workers as strings
    -- (Hyperdrive runs with fetch_types: false).
    last_lap_time_ms INTEGER,
    current_lap_time_ms INTEGER,
    sector1_time_ms INTEGER,
    sector2_time_ms INTEGER,
    lap_distance REAL,
    total_distance REAL,
    safety_car_delta REAL,

    -- Lap Data / Packet 2: position and state
    position SMALLINT,
    grid_position SMALLINT,
    current_lap_num SMALLINT,
    -- Enum codes: Sector (0-2), PitStatus (0-2), DriverStatus (0-4),
    -- ResultStatus (0-7). Resolved to names by @f1/db.
    sector SMALLINT,
    pit_status SMALLINT,
    driver_status SMALLINT,
    result_status SMALLINT,
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
    -- Enum codes: ActualTyreCompound, VisualTyreCompound, FlagStatus
    -- (FlagStatus uses -1 for UNKNOWN, hence a signed type).
    actual_tyre_compound SMALLINT,
    visual_tyre_compound SMALLINT,
    tyres_age_laps SMALLINT,
    vehicle_fia_flags SMALLINT,
    network_paused BOOLEAN,
    traction_control SMALLINT,
    anti_lock_brakes BOOLEAN,
    max_rpm SMALLINT,
    idle_rpm SMALLINT,
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

-- The primary key leads with `timestamp`, so per-driver frame lookups need
-- their own index. This is the one the dashboard's DISTINCT ON (user_id) walks
-- to pull each car's latest frame.
--
-- It does not, on its own, keep those reads cheap as the database grows:
-- `timestamp` is the partitioning column, so a query naming only session_uid
-- cannot exclude chunks and opens every one of them. Callers should add
-- `timestamp >= <session_start_utc>` — always available from telemetry.sessions
-- — which narrows the scan to the chunks the session actually occupies.
CREATE INDEX IF NOT EXISTS idx_car_frame_session_driver_frame
    ON telemetry.car_frame(session_uid, user_id, overall_frame_identifier DESC);
