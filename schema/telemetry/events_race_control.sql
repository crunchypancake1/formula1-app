-- Race control events (session-level, no driver)
-- Covers: SSTA, SEND, LGOT, CHQF, RDFL, DRSE, DRSD, STLG, SCAR
CREATE TABLE IF NOT EXISTS telemetry.events_race_control (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
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

CREATE INDEX IF NOT EXISTS idx_events_race_control_session ON telemetry.events_race_control(session_uid);
CREATE INDEX IF NOT EXISTS idx_events_race_control_code ON telemetry.events_race_control(event_code);
