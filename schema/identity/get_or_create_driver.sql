-- Atomic upsert: find or create a user by driver_name (case-insensitive).
-- Used by the listener when a new driver name appears in telemetry.
-- Discord fields are left NULL — only populated via Discord OAuth.
CREATE OR REPLACE FUNCTION identity.get_or_create_driver(p_driver_name VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Case-insensitive lookup
    SELECT id INTO v_id
    FROM identity.users
    WHERE lower(driver_name) = lower(p_driver_name);

    IF v_id IS NOT NULL THEN
        RETURN v_id;
    END IF;

    -- Insert new user (discord fields default to NULL)
    BEGIN
        INSERT INTO identity.users (driver_name)
        VALUES (p_driver_name)
        RETURNING id INTO v_id;
    EXCEPTION WHEN unique_violation THEN
        -- Race condition: another transaction inserted first
        SELECT id INTO v_id
        FROM identity.users
        WHERE lower(driver_name) = lower(p_driver_name);
    END;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;
