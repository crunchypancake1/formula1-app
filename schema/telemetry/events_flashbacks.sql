-- Flashback events (source: Event packet, code FLBK)
--
-- A flashback rewinds m_frameIdentifier and m_sessionTime but NOT
-- m_overallFrameIdentifier, so without this record there is no way to tell,
-- after the fact, that a stretch of car_frame rows describes a run that was
-- undone. The listener deletes frame rows above flashback_session_time when it
-- sees the event; this table keeps the audit trail of what was rewound.
CREATE TABLE IF NOT EXISTS telemetry.events_flashbacks (
    session_uid                 VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    overall_frame_identifier    INTEGER NOT NULL,
    session_time                FLOAT NOT NULL,
    flashback_frame_identifier  BIGINT NOT NULL,
    flashback_session_time      FLOAT NOT NULL,
    rows_discarded              INTEGER,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, overall_frame_identifier)
);

-- No secondary index: session_uid is a prefix of the primary key.
