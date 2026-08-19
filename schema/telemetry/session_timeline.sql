-- Session timeline (source: Session packet, Packet 1) — the live half of the
-- session state, sampled at packet rate. Static configuration is on
-- telemetry.sessions.
--
-- timestamp is derived (sessions.session_start_utc + session_time), not
-- wall-clock at insert, so re-delivered packets collapse onto the same row.

CREATE TABLE IF NOT EXISTS telemetry.session_timeline (
    timestamp TIMESTAMPTZ NOT NULL,
    session_uid VARCHAR(255) NOT NULL,
    session_time FLOAT NOT NULL,
    overall_frame_identifier INTEGER NOT NULL,
    session_time_left FLOAT NOT NULL,
    total_laps SMALLINT,

    -- Weather / track conditions
    weather_state VARCHAR(50) NOT NULL,
    weather_track_temp SMALLINT NOT NULL,
    weather_air_temp SMALLINT NOT NULL,

    -- Race control
    safety_car_status VARCHAR(50) NOT NULL,
    marshal_zone_flags VARCHAR(20)[],
    num_safety_car_periods SMALLINT,
    num_virtual_safety_car_periods SMALLINT,
    num_red_flag_periods SMALLINT,

    -- Local session state
    game_paused BOOLEAN,
    is_spectating BOOLEAN,
    spectator_car_index SMALLINT,

    -- Player-only pit strategy window (0 / 255 when not applicable)
    pit_stop_window_ideal_lap SMALLINT,
    pit_stop_window_latest_lap SMALLINT,
    pit_stop_rejoin_position SMALLINT,

    PRIMARY KEY (timestamp, session_uid)
);

-- Convert to hypertable with 1-day chunks
-- (Sessions are 1-2 hours; multiple sessions per chunk keeps indexes small)
SELECT create_hypertable(
    'telemetry.session_timeline',
    'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Index for per-session time-range queries
CREATE INDEX IF NOT EXISTS idx_timeline_session_time
ON telemetry.session_timeline(session_uid, timestamp);

-- Index for accurate frame-based ordering within a session
-- overall_frame_identifier is monotonically increasing and survives flashbacks
CREATE INDEX IF NOT EXISTS idx_timeline_session_frame
ON telemetry.session_timeline(session_uid, overall_frame_identifier);

-- Enable compression (segment by session for efficient per-session queries)
-- Order by frame_identifier for game-accurate ordering within segments
ALTER TABLE telemetry.session_timeline SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'session_uid',
    timescaledb.compress_orderby = 'overall_frame_identifier DESC'
);

-- Auto-compress chunks older than 7 days
SELECT add_compression_policy(
    'telemetry.session_timeline',
    INTERVAL '7 days',
    if_not_exists => true
);
