-- Auto-link trigger: Automatically links telemetry weekends to webapp races
-- Fires on INSERT of qualifying, sprint, and race sessions (not practice or time trial)

-- Function to auto-link a weekend to a race
CREATE OR REPLACE FUNCTION telemetry.auto_link_weekend()
RETURNS TRIGGER AS $$
DECLARE
    v_matched_race_id INTEGER;
    v_time_window INTERVAL := INTERVAL '4 hours';
    v_existing_session_count INTEGER;
BEGIN
    -- Skip practice sessions and time trials - only link on competitive sessions
    IF NEW.session_type IN (
        'UNKNOWN',
        'PRACTICE_1', 'PRACTICE_2', 'PRACTICE_3', 'SHORT_PRACTICE',
        'TIME_TRIAL'
    ) THEN
        RETURN NEW;
    END IF;

    -- Check if other sessions already exist for this weekend_link
    SELECT COUNT(*) INTO v_existing_session_count
    FROM telemetry.sessions
    WHERE weekend_link = NEW.weekend_link
      AND session_uid != NEW.session_uid;

    IF v_existing_session_count > 0 THEN
        RETURN NEW;
    END IF;

    -- Check if this weekend is already linked
    IF EXISTS (
        SELECT 1 FROM webapp.races
        WHERE weekend_link = NEW.weekend_link
    ) THEN
        RETURN NEW;
    END IF;

    -- Find matching unlinked race by track_id and datetime (within +/- 4 hours)
    SELECT sr.id INTO v_matched_race_id
    FROM webapp.races sr
    WHERE sr.weekend_link IS NULL
      AND sr.track_id = NEW.track_id
      AND sr.race_datetime_utc BETWEEN (NEW.created_at - v_time_window)
                                   AND (NEW.created_at + v_time_window)
    ORDER BY ABS(EXTRACT(EPOCH FROM (sr.race_datetime_utc - NEW.created_at)))
    LIMIT 1;

    IF v_matched_race_id IS NOT NULL THEN
        UPDATE webapp.races
        SET weekend_link = NEW.weekend_link,
            updated_at = NOW()
        WHERE id = v_matched_race_id;

        RAISE NOTICE 'Auto-linked race id=% to weekend_link=%',
                     v_matched_race_id, NEW.weekend_link;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger on session insert only
DROP TRIGGER IF EXISTS trg_auto_link_weekend ON telemetry.sessions;

CREATE TRIGGER trg_auto_link_weekend
    AFTER INSERT ON telemetry.sessions
    FOR EACH ROW
    EXECUTE FUNCTION telemetry.auto_link_weekend();

COMMENT ON FUNCTION telemetry.auto_link_weekend() IS
    'Automatically links telemetry weekends to webapp races based on track_id and datetime match within +/- 4 hours. Fires on INSERT of competitive sessions (quali/sprint/race). Skips practice and time trial.';
