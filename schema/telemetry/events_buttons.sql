-- Button state events (source: Event packet, code BUTN)
--
-- Local player's controller state; the game emits one event per change, so
-- rows are sparse rather than sampled. button_status is the raw uint32 bit
-- field, buttons_pressed the resolved flag names for readability.
CREATE TABLE IF NOT EXISTS telemetry.events_buttons (
    session_uid                 VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    button_status               BIGINT NOT NULL,
    buttons_pressed             VARCHAR(40)[] NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier)
);

CREATE INDEX IF NOT EXISTS idx_events_buttons_session ON telemetry.events_buttons(session_uid);
