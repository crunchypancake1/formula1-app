-- Weather forecast table (source: Session packet, Packet 1)
-- Stores latest forecast predictions only (max 64 rows per session)
-- Uses upsert to keep forecasts current throughout session
CREATE TABLE IF NOT EXISTS telemetry.weather_forecast (
    session_uid VARCHAR(255) NOT NULL REFERENCES telemetry.sessions(session_uid) ON DELETE CASCADE,
    forecast_index SMALLINT NOT NULL,
    time_offset_minutes SMALLINT NOT NULL,
    weather VARCHAR(50) NOT NULL,
    track_temperature SMALLINT NOT NULL,
    track_temperature_change VARCHAR(50) NOT NULL,
    air_temperature SMALLINT NOT NULL,
    air_temperature_change VARCHAR(50) NOT NULL,
    rain_percentage SMALLINT NOT NULL,
    overall_frame_identifier INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_uid, forecast_index),
    CONSTRAINT ck_weather_forecast_index_valid CHECK (forecast_index >= 0 AND forecast_index <= 63)
);

CREATE INDEX IF NOT EXISTS idx_weather_forecast_session ON telemetry.weather_forecast(session_uid);

COMMENT ON COLUMN telemetry.weather_forecast.time_offset_minutes IS 'Minutes from session start when this weather is predicted';
COMMENT ON COLUMN telemetry.weather_forecast.overall_frame_identifier IS 'Overall frame identifier when this forecast was last updated';
