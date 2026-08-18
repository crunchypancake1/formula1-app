-- Teams lookup table for reference data
CREATE TABLE IF NOT EXISTS telemetry.teams (
    team_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL
);

-- 2026 Season Pack: team_id can now exceed SMALLINT range (sentinel 65535).
ALTER TABLE telemetry.teams ALTER COLUMN team_id TYPE INTEGER;

-- Insert all known F1 25 / F1 26 teams
INSERT INTO telemetry.teams (team_id, name, display_name) VALUES
    (0, 'MERCEDES', 'Mercedes'),
    (1, 'FERRARI', 'Ferrari'),
    (2, 'RED_BULL_RACING', 'Red Bull Racing'),
    (3, 'WILLIAMS', 'Williams'),
    (4, 'ASTON_MARTIN', 'Aston Martin'),
    (5, 'ALPINE', 'Alpine'),
    (6, 'RB', 'RB'),
    (7, 'HAAS', 'Haas'),
    (8, 'MCLAREN', 'McLaren'),
    (9, 'SAUBER', 'Sauber'),
    -- Generic/Custom teams
    (41, 'F1_GENERIC', 'F1 Generic'),
    (104, 'F1_CUSTOM_TEAM', 'F1 Custom Team'),
    -- F2 and fictional teams
    (129, 'KONNERSPORT', 'Konnersport'),
    (142, 'APXGP_24', 'APXGP 24'),
    (154, 'APXGP_25', 'APXGP 25'),
    (155, 'KONNERSPORT_24', 'Konnersport 24'),
    (158, 'ART_GP_24', 'ART Grand Prix'),
    (159, 'CAMPOS_24', 'Campos Racing'),
    (160, 'RODIN_MOTORSPORT_24', 'Rodin Motorsport'),
    (161, 'AIX_RACING_24', 'AIX Racing'),
    (162, 'DAMS_24', 'DAMS'),
    (163, 'HITECH_24', 'Hitech'),
    (164, 'MP_MOTORSPORT_24', 'MP Motorsport'),
    (165, 'PREMA_24', 'Prema Racing'),
    (166, 'TRIDENT_24', 'Trident'),
    (167, 'VAN_AMERSFOORT_RACING_24', 'Van Amersfoort Racing'),
    (168, 'INVICTA_24', 'Invicta'),
    -- Alternative team IDs
    (185, 'MERCEDES_24', 'Mercedes 24'),
    (186, 'FERRARI_24', 'Ferrari 24'),
    (187, 'RED_BULL_RACING_24', 'Red Bull Racing 24'),
    (188, 'WILLIAMS_24', 'Williams 24'),
    (189, 'ASTON_MARTIN_24', 'Aston Martin 24'),
    (190, 'ALPINE_24', 'Alpine 24'),
    (191, 'RB_24', 'RB 24'),
    (192, 'HAAS_24', 'Haas 24'),
    (193, 'MCLAREN_24', 'McLaren 24'),
    (194, 'SAUBER_24', 'Sauber 24'),
    (255, 'LEGACY_UNKNOWN', 'Unknown'),
    -- F2 2025 teams
    (465, 'ART_GP_25', 'Art GP ''25'),
    (466, 'CAMPOS_25', 'Campos ''25'),
    (467, 'RODIN_MOTORSPORT_25', 'Rodin Motorsport ''25'),
    (468, 'AIX_RACING_25', 'AIX Racing ''25'),
    (469, 'DAMS_25', 'DAMS ''25'),
    (470, 'HITECH_25', 'Hitech ''25'),
    (471, 'MP_MOTORSPORT_25', 'MP Motorsport ''25'),
    (472, 'PREMA_25', 'Prema ''25'),
    (473, 'TRIDENT_25', 'Trident ''25'),
    (474, 'VAN_AMERSFOORT_RACING_25', 'Van Amersfoort Racing ''25'),
    (475, 'INVICTA_25', 'Invicta ''25'),
    -- F1 2026 grid
    (476, 'MERCEDES_26', 'Mercedes ''26'),
    (477, 'FERRARI_26', 'Ferrari ''26'),
    (478, 'RED_BULL_RACING_26', 'Red Bull Racing ''26'),
    (479, 'WILLIAMS_26', 'Williams ''26'),
    (480, 'ASTON_MARTIN_26', 'Aston Martin ''26'),
    (481, 'ALPINE_26', 'Alpine ''26'),
    (482, 'RB_26', 'RB ''26'),
    (483, 'HAAS_26', 'Haas ''26'),
    (484, 'MCLAREN_26', 'McLaren ''26'),
    (485, 'AUDI_26', 'Audi ''26'),
    (486, 'CADILLAC_26', 'Cadillac ''26'),
    (65535, 'UNKNOWN', 'Unknown')
ON CONFLICT (team_id) DO UPDATE SET
    name = EXCLUDED.name,
    display_name = EXCLUDED.display_name;
