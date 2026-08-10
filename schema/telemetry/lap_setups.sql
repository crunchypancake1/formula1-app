-- Junction table linking completed laps to the car setup used
-- Only populated for player car (setup data is player-only in multiplayer)
CREATE TABLE IF NOT EXISTS telemetry.lap_setups (
    session_uid     VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES identity.users(id),
    lap_number      SMALLINT NOT NULL,
    setup_id        INTEGER NOT NULL REFERENCES telemetry.car_setups(setup_id),
    PRIMARY KEY (session_uid, user_id, lap_number)
);
