-- Race control events (session-level, no driver)
-- Covers: SSTA, SEND, LGOT, CHQF, RDFL, DRSE, DRSD, STLG, SCAR
CREATE TABLE IF NOT EXISTS telemetry.events_race_control (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    event_code                  VARCHAR(10) NOT NULL,
    session_time                FLOAT NOT NULL,
    safety_car_type             VARCHAR(30),
    safety_car_event_type       VARCHAR(30),
    num_lights                  SMALLINT,
    drs_disabled_reason         VARCHAR(50),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier, event_code)
);

-- No secondary indexes. The primary key (session_uid, overall_frame_identifier,
-- event_code) serves the dashboard feed's
-- "WHERE session_uid = $1 ORDER BY overall_frame_identifier DESC LIMIT n"
-- as a backward index scan; a bare event_code index spans nine values across
-- every session and is never selective enough to be chosen.
