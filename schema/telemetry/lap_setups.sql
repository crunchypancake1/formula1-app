-- Junction table linking completed laps to the car setup used.
-- Only populated for the player's car — setup data is player-only in multiplayer.
--
-- next_front_wing_value is the packet-level m_nextFrontWingValue: the front
-- wing the player has queued for their next pit stop. Player-only, so it is
-- NULL for anyone else.
CREATE TABLE IF NOT EXISTS telemetry.lap_setups (
    session_uid     VARCHAR(20) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES identity.users(id),
    lap_number      SMALLINT NOT NULL,
    setup_id        INTEGER NOT NULL REFERENCES telemetry.car_setups(setup_id),
    next_front_wing_value REAL,
    PRIMARY KEY (session_uid, user_id, lap_number)
);
