-- Teams lookup table for reference data
CREATE TABLE IF NOT EXISTS telemetry.teams (
    team_id SMALLINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL
);

-- Insert all known F1 25 teams
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
    (255, 'UNKNOWN', 'Unknown')
ON CONFLICT (team_id) DO UPDATE SET
    name = EXCLUDED.name,
    display_name = EXCLUDED.display_name;
