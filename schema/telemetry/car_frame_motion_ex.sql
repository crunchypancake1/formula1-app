-- Motion Ex (Packet 13) — 60Hz, player car ONLY. Joins telemetry.car_frame on
-- (session_uid, user_id, overall_frame_identifier).
--
-- The packet has no car index: it always describes header.player_car_index and
-- no other car, in every session type. Written unbuffered on arrival.
--
-- timestamp is derived (sessions.session_start_utc + session_time), which is
-- what lets the primary key de-duplicate a re-delivered frame.

CREATE TABLE IF NOT EXISTS telemetry.car_frame_motion_ex (
    timestamp               TIMESTAMPTZ NOT NULL,
    session_uid             VARCHAR(20) NOT NULL
                            REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id                 INTEGER NOT NULL,
    session_time            FLOAT NOT NULL,
    overall_frame_identifier INTEGER NOT NULL,

    -- Suspension per wheel (RL, RR, FL, FR)
    suspension_position_rl  REAL,
    suspension_position_rr  REAL,
    suspension_position_fl  REAL,
    suspension_position_fr  REAL,
    suspension_velocity_rl  REAL,
    suspension_velocity_rr  REAL,
    suspension_velocity_fl  REAL,
    suspension_velocity_fr  REAL,
    suspension_acceleration_rl REAL,
    suspension_acceleration_rr REAL,
    suspension_acceleration_fl REAL,
    suspension_acceleration_fr REAL,

    -- Wheel dynamics per wheel
    wheel_speed_rl          REAL,
    wheel_speed_rr          REAL,
    wheel_speed_fl          REAL,
    wheel_speed_fr          REAL,
    wheel_slip_ratio_rl     REAL,
    wheel_slip_ratio_rr     REAL,
    wheel_slip_ratio_fl     REAL,
    wheel_slip_ratio_fr     REAL,
    wheel_slip_angle_rl     REAL,
    wheel_slip_angle_rr     REAL,
    wheel_slip_angle_fl     REAL,
    wheel_slip_angle_fr     REAL,
    wheel_lat_force_rl      REAL,
    wheel_lat_force_rr      REAL,
    wheel_lat_force_fl      REAL,
    wheel_lat_force_fr      REAL,
    wheel_long_force_rl     REAL,
    wheel_long_force_rr     REAL,
    wheel_long_force_fl     REAL,
    wheel_long_force_fr     REAL,
    wheel_vert_force_rl     REAL,
    wheel_vert_force_rr     REAL,
    wheel_vert_force_fl     REAL,
    wheel_vert_force_fr     REAL,
    wheel_camber_rl         REAL,
    wheel_camber_rr         REAL,
    wheel_camber_fl         REAL,
    wheel_camber_fr         REAL,
    wheel_camber_gain_rl    REAL,
    wheel_camber_gain_rr    REAL,
    wheel_camber_gain_fl    REAL,
    wheel_camber_gain_fr    REAL,

    -- Vehicle-level physics
    height_of_cog_above_ground REAL,
    local_velocity_x        REAL,
    local_velocity_y        REAL,
    local_velocity_z        REAL,
    angular_velocity_x      REAL,
    angular_velocity_y      REAL,
    angular_velocity_z      REAL,
    angular_acceleration_x  REAL,
    angular_acceleration_y  REAL,
    angular_acceleration_z  REAL,
    front_wheels_angle      REAL,

    -- Aero heights
    front_aero_height       REAL,
    rear_aero_height        REAL,

    -- Roll angles
    front_roll_angle        REAL,
    rear_roll_angle         REAL,

    -- Chassis attitude
    chassis_yaw             REAL,
    chassis_pitch           REAL,

    PRIMARY KEY (timestamp, session_uid, user_id, overall_frame_identifier)
);

SELECT create_hypertable(
    'telemetry.car_frame_motion_ex', 'timestamp',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day'
);

ALTER TABLE telemetry.car_frame_motion_ex
    SET (timescaledb.compress,
         timescaledb.compress_segmentby = 'session_uid, user_id',
         timescaledb.compress_orderby = 'overall_frame_identifier DESC');

SELECT add_compression_policy('telemetry.car_frame_motion_ex',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_car_frame_motion_ex_session_driver_frame
    ON telemetry.car_frame_motion_ex (session_uid, user_id, overall_frame_identifier DESC);
