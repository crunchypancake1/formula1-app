CREATE SCHEMA IF NOT EXISTS telemetry;

-- Tracks table
CREATE TABLE IF NOT EXISTS telemetry.tracks (
    track_id SMALLINT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    track_length INTEGER,
    sector2_start FLOAT,
    sector3_start FLOAT,
    marshal_zones JSONB,
    pit_speed_limit SMALLINT
);

-- Seed tracks with info from F1 25 game (track_length in meters, pit_speed_limit in km/h)
INSERT INTO telemetry.tracks (track_id, name, display_name, country, track_length, pit_speed_limit) VALUES
    (0,  'MELBOURNE',           'Albert Park',                        'Australia',            5278, 80),
    (2,  'SHANGHAI',            'Shanghai International Circuit',     'China',                5451, 80),
    (3,  'SAKHIR_BAHRAIN',      'Bahrain International Circuit',      'Bahrain',              5412, 80),
    (4,  'CATALUNYA',           'Circuit de Barcelona-Catalunya',     'Spain',                4657, 80),
    (5,  'MONACO',              'Circuit de Monaco',                  'Monaco',               3337, 60),
    (6,  'MONTREAL',            'Circuit Gilles Villeneuve',          'Canada',               4361, 80),
    (7,  'SILVERSTONE',         'Silverstone Circuit',                'United Kingdom',       5891, 80),
    (9,  'HUNGARORING',         'Hungaroring',                        'Hungary',              4381, 80),
    (10, 'SPA',                 'Circuit de Spa-Francorchamps',       'Belgium',              7004, 80),
    (11, 'MONZA',               'Autodromo Nazionale Monza',          'Italy',                5793, 80),
    (12, 'SINGAPORE',           'Marina Bay Street Circuit',          'Singapore',            4940, 80),
    (13, 'SUZUKA',              'Suzuka International Racing Course', 'Japan',                5807, 80),
    (14, 'ABU_DHABI',           'Yas Marina Circuit',                 'United Arab Emirates', 5281, 80),
    (15, 'TEXAS',               'Circuit of the Americas',            'United States',        5513, 80),
    (16, 'BRAZIL',              'Autódromo José Carlos Pace',         'Brazil',               4309, 80),
    (17, 'AUSTRIA',             'Red Bull Ring',                      'Austria',              4318, 80),
    (19, 'MEXICO',              'Autódromo Hermanos Rodríguez',       'Mexico',               4304, 80),
    (20, 'BAKU_AZERBAIJAN',     'Baku City Circuit',                  'Azerbaijan',           6003, 80),
    (26, 'ZANDVOORT',           'Circuit Zandvoort',                  'Netherlands',          4259, 80),
    (27, 'IMOLA',               'Autodromo Enzo e Dino Ferrari',      'Italy',                4909, 80),
    (29, 'JEDDAH',              'Jeddah Corniche Circuit',            'Saudi Arabia',         6174, 80),
    (30, 'MIAMI',               'Miami International Autodrome',      'United States',        5412, 80),
    (31, 'LAS_VEGAS',           'Las Vegas Strip Circuit',            'United States',        6201, 80),
    (32, 'LOSAIL',              'Lusail International Circuit',       'Qatar',                5419, 80),
    (39, 'SILVERSTONE_REVERSE', 'Silverstone Circuit (Reverse)',      'United Kingdom',       5891, 80),
    (40, 'AUSTRIA_REVERSE',     'Red Bull Ring (Reverse)',            'Austria',              4318, 80),
    (41, 'ZANDVOORT_REVERSE',   'Circuit Zandvoort (Reverse)',        'Netherlands',          4259, 80),
    (255,'UNKNOWN',             'Unknown Track',                      'Unknown',              NULL, NULL)
ON CONFLICT (track_id) DO UPDATE SET
    track_length = COALESCE(telemetry.tracks.track_length, EXCLUDED.track_length),
    pit_speed_limit = COALESCE(telemetry.tracks.pit_speed_limit, EXCLUDED.pit_speed_limit);
