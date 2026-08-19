"""
f1_enums.py - ID lookup tables for the F1 UDP telemetry feed.

Tables are the 2026 Season Pack superset; every 2025 ID is still present and
unchanged, so the same tables serve both formats. The 2026 pack only added
entries (teams 465-486, drivers 186-197, track 42), it did not renumber
anything.

Unknown IDs are normal - EA adds cars and drivers in patches - so every lookup
helper degrades to a readable placeholder rather than raising.
"""

# --------------------------------------------------------------------------
# Teams. Note the width change: m_teamId is uint8 in the 2025 format and
# uint16 in 2026, which is exactly why IDs above 255 could be added.
# --------------------------------------------------------------------------

TEAMS = {
    0: "Mercedes", 1: "Ferrari", 2: "Red Bull Racing", 3: "Williams",
    4: "Aston Martin", 5: "Alpine", 6: "RB", 7: "Haas", 8: "McLaren",
    9: "Sauber", 41: "F1 Generic", 104: "F1 Custom Team", 129: "Konnersport",
    142: "APXGP '24", 154: "APXGP '25", 155: "Konnersport '24",
    158: "Art GP '24", 159: "Campos '24", 160: "Rodin Motorsport '24",
    161: "AIX Racing '24", 162: "DAMS '24", 163: "Hitech '24",
    164: "MP Motorsport '24", 165: "Prema '24", 166: "Trident '24",
    167: "Van Amersfoort Racing '24", 168: "Invicta '24",
    185: "Mercedes '24", 186: "Ferrari '24", 187: "Red Bull Racing '24",
    188: "Williams '24", 189: "Aston Martin '24", 190: "Alpine '24",
    191: "RB '24", 192: "Haas '24", 193: "McLaren '24", 194: "Sauber '24",
    # 2026 Season Pack additions
    465: "Art GP '25", 466: "Campos '25", 467: "Rodin Motorsport '25",
    468: "AIX Racing '25", 469: "DAMS '25", 470: "Hitech '25",
    471: "MP Motorsport '25", 472: "Prema '25", 473: "Trident '25",
    474: "Van Amersfoort Racing '25", 475: "Invicta '25",
    476: "Mercedes '26", 477: "Ferrari '26", 478: "Red Bull Racing '26",
    479: "Williams '26", 480: "Aston Martin '26", 481: "Alpine '26",
    482: "RB '26", 483: "Haas '26", 484: "McLaren '26", 485: "Audi '26",
    486: "Cadillac '26",
}

# The eleven 2026-season F1 constructors, in team-ID order. Audi and Cadillac
# are the reason the car arrays grew from 22 to 24 slots.
TEAMS_2026_SEASON = [476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486]

# --------------------------------------------------------------------------
# Drivers. m_driverId is uint8 in 2025 (255 = network human) and uint16 in
# 2026 (65535 = network human). Always check the sentinel before looking up:
# a human player's name comes from m_name in the participants packet instead.
# --------------------------------------------------------------------------

DRIVERS = {
    0: "Carlos Sainz", 2: "Daniel Ricciardo", 3: "Fernando Alonso",
    4: "Felipe Massa", 7: "Lewis Hamilton", 9: "Max Verstappen",
    10: "Nico Hulkenberg", 11: "Kevin Magnussen", 14: "Sergio Perez",
    15: "Valtteri Bottas", 17: "Esteban Ocon", 19: "Lance Stroll",
    20: "Arron Barnes", 21: "Martin Giles", 22: "Alex Murray",
    23: "Lucas Roth", 24: "Igor Correia", 25: "Sophie Levasseur",
    26: "Jonas Schiffer", 27: "Alain Forest", 28: "Jay Letourneau",
    29: "Esto Saari", 30: "Yasar Atiyeh", 31: "Callisto Calabresi",
    32: "Naota Izumi", 33: "Howard Clarke", 34: "Lars Kaufmann",
    35: "Marie Laursen", 36: "Flavio Nieves", 38: "Klimek Michalski",
    39: "Santiago Moreno", 40: "Benjamin Coppens", 41: "Noah Visser",
    50: "George Russell", 54: "Lando Norris", 58: "Charles Leclerc",
    59: "Pierre Gasly", 62: "Alexander Albon", 70: "Rashid Nair",
    71: "Jack Tremblay", 77: "Ayrton Senna", 80: "Guanyu Zhou",
    83: "Juan Manuel Correa", 90: "Michael Schumacher", 94: "Yuki Tsunoda",
    102: "Aidan Jackson", 109: "Jenson Button", 110: "David Coulthard",
    112: "Oscar Piastri", 113: "Liam Lawson", 116: "Richard Verschoor",
    123: "Enzo Fittipaldi", 125: "Mark Webber", 126: "Jacques Villeneuve",
    127: "Callie Mayer", 132: "Logan Sargeant", 136: "Jack Doohan",
    137: "Amaury Cordeel", 138: "Dennis Hauger", 145: "Zane Maloney",
    146: "Victor Martins", 147: "Oliver Bearman", 148: "Jak Crawford",
    149: "Isack Hadjar", 152: "Roman Stanek", 153: "Kush Maini",
    156: "Brendon Leigh", 157: "David Tonizza", 158: "Jarno Opmeer",
    159: "Lucas Blakeley", 160: "Paul Aron", 161: "Gabriel Bortoleto",
    162: "Franco Colapinto", 163: "Taylor Barnard", 164: "Joshua Durksen",
    165: "Andrea-Kimi Antonelli", 166: "Ritomo Miyata",
    167: "Rafael Villagomez", 168: "Zak O'Sullivan", 169: "Pepe Marti",
    170: "Sonny Hayes", 171: "Joshua Pearce", 172: "Callum Voisin",
    173: "Matias Zagazeta", 174: "Nikola Tsolov", 175: "Tim Tramnitz",
    185: "Luca Cortez",
    # 2026 Season Pack additions
    186: "Luke Browning", 187: "Cian Shields", 188: "Arvid Lindblad",
    189: "Dino Beganovic", 190: "Leonardo Fornaroli", 191: "Oliver Goethe",
    192: "Gabriele Mini", 193: "Sebastian Montoya", 194: "Alexander Dunne",
    195: "Max Esterson", 196: "Sami Meguetounif", 197: "John Bennett",
}

NETWORK_HUMAN_DRIVER_ID = {2025: 255, 2026: 65535}
NO_TEAM_SELECTED = {2025: 255, 2026: 65535}

TRACKS = {
    0: "Melbourne", 2: "Shanghai", 3: "Sakhir (Bahrain)", 4: "Catalunya",
    5: "Monaco", 6: "Montreal", 7: "Silverstone", 9: "Hungaroring",
    10: "Spa", 11: "Monza", 12: "Singapore", 13: "Suzuka", 14: "Abu Dhabi",
    15: "Texas", 16: "Brazil", 17: "Austria", 19: "Mexico",
    20: "Baku (Azerbaijan)", 26: "Zandvoort", 27: "Imola", 29: "Jeddah",
    30: "Miami", 31: "Las Vegas", 32: "Losail", 39: "Silverstone (Reverse)",
    40: "Austria (Reverse)", 41: "Zandvoort (Reverse)",
    42: "Madrid",  # new in the 2026 Season Pack
}

NATIONALITIES = {
    1: "American", 2: "Argentinean", 3: "Australian", 4: "Austrian",
    5: "Azerbaijani", 6: "Bahraini", 7: "Belgian", 8: "Bolivian",
    9: "Brazilian", 10: "British", 11: "Bulgarian", 12: "Cameroonian",
    13: "Canadian", 14: "Chilean", 15: "Chinese", 16: "Colombian",
    17: "Costa Rican", 18: "Croatian", 19: "Cypriot", 20: "Czech",
    21: "Danish", 22: "Dutch", 23: "Ecuadorian", 24: "English",
    25: "Emirian", 26: "Estonian", 27: "Finnish", 28: "French",
    29: "German", 30: "Ghanaian", 31: "Greek", 32: "Guatemalan",
    33: "Honduran", 34: "Hong Konger", 35: "Hungarian", 36: "Icelander",
    37: "Indian", 38: "Indonesian", 39: "Irish", 40: "Israeli",
    41: "Italian", 42: "Jamaican", 43: "Japanese", 44: "Jordanian",
    45: "Kuwaiti", 46: "Latvian", 47: "Lebanese", 48: "Lithuanian",
    49: "Luxembourger", 50: "Malaysian", 51: "Maltese", 52: "Mexican",
    53: "Monegasque", 54: "New Zealander", 55: "Nicaraguan",
    56: "Northern Irish", 57: "Norwegian", 58: "Omani", 59: "Pakistani",
    60: "Panamanian", 61: "Paraguayan", 62: "Peruvian", 63: "Polish",
    64: "Portuguese", 65: "Qatari", 66: "Romanian", 68: "Salvadoran",
    69: "Saudi", 70: "Scottish", 71: "Serbian", 72: "Singaporean",
    73: "Slovakian", 74: "Slovenian", 75: "South Korean", 76: "South African",
    77: "Spanish", 78: "Swedish", 79: "Swiss", 80: "Thai", 81: "Turkish",
    82: "Uruguayan", 83: "Ukrainian", 84: "Venezuelan", 85: "Barbadian",
    86: "Welsh", 87: "Vietnamese", 88: "Algerian", 89: "Bosnian",
    90: "Filipino",
}

SESSION_TYPES = {
    0: "Unknown", 1: "Practice 1", 2: "Practice 2", 3: "Practice 3",
    4: "Short Practice", 5: "Qualifying 1", 6: "Qualifying 2",
    7: "Qualifying 3", 8: "Short Qualifying", 9: "One-Shot Qualifying",
    10: "Sprint Shootout 1", 11: "Sprint Shootout 2", 12: "Sprint Shootout 3",
    13: "Short Sprint Shootout", 14: "One-Shot Sprint Shootout", 15: "Race",
    16: "Race 2", 17: "Race 3", 18: "Time Trial",
}

GAME_MODES = {
    4: "Grand Prix '23", 5: "Time Trial", 6: "Splitscreen",
    7: "Online Custom", 15: "Online Weekly Event",
    17: "Story Mode (Braking Point)", 27: "My Team Career '25",
    28: "Driver Career '25", 29: "Career '25 Online",
    30: "Challenge Career '25", 75: "Story Mode (APXGP)", 127: "Benchmark",
}

RULESETS = {0: "Practice & Qualifying", 1: "Race", 2: "Time Trial",
            12: "Elimination"}

FORMULAS = {
    0: "F1 Modern", 1: "F1 Classic", 2: "F2", 3: "F1 Generic", 4: "Beta",
    6: "Esports", 8: "F1 World", 9: "F1 Elimination",
    13: "F1 26",  # new in the 2026 Season Pack
}

SURFACE_TYPES = {
    0: "Tarmac", 1: "Rumble strip", 2: "Concrete", 3: "Rock", 4: "Gravel",
    5: "Mud", 6: "Sand", 7: "Grass", 8: "Water", 9: "Cobblestone",
    10: "Metal", 11: "Ridged",
}

WEATHER = {0: "Clear", 1: "Light cloud", 2: "Overcast", 3: "Light rain",
           4: "Heavy rain", 5: "Storm"}

# --------------------------------------------------------------------------
# Tyres. m_actualTyreCompound is the real compound (C0-C6); the visual
# compound is what the sidewall shows (soft/medium/hard), and the mapping
# between them changes race to race - never assume actual 16 means "soft".
# --------------------------------------------------------------------------

ACTUAL_TYRE_COMPOUNDS = {
    16: "C5", 17: "C4", 18: "C3", 19: "C2", 20: "C1", 21: "C0", 22: "C6",
    7: "Intermediate", 8: "Wet",
    9: "Dry (Classic)", 10: "Wet (Classic)",
    11: "Super Soft (F2)", 12: "Soft (F2)", 13: "Medium (F2)",
    14: "Hard (F2)", 15: "Wet (F2)",
}

VISUAL_TYRE_COMPOUNDS = {
    16: "Soft", 17: "Medium", 18: "Hard", 7: "Intermediate", 8: "Wet",
    15: "Wet (F2 '20)", 19: "Super Soft (F2 '20)", 20: "Soft (F2 '20)",
    21: "Medium (F2 '20)", 22: "Hard (F2 '20)",
}

# ERS mode 3 is documented as "Overtake" in 2025 and renamed "Boost" for the
# 2026 regulations - same value, different official name.
ERS_DEPLOY_MODES = {0: "None", 1: "Medium", 2: "Hotlap", 3: "Boost/Overtake"}

DRIVER_STATUS = {0: "In garage", 1: "Flying lap", 2: "In lap", 3: "Out lap",
                 4: "On track"}

RESULT_STATUS = {0: "Invalid", 1: "Inactive", 2: "Active", 3: "Finished",
                 4: "Did not finish", 5: "Disqualified", 6: "Not classified",
                 7: "Retired"}

RESULT_REASON = {
    0: "Invalid", 1: "Retired", 2: "Finished", 3: "Terminal damage",
    4: "Inactive", 5: "Not enough laps completed", 6: "Black flagged",
    7: "Red flagged", 8: "Mechanical failure", 9: "Session skipped",
    10: "Session simulated",
}

PIT_STATUS = {0: "None", 1: "Pitting", 2: "In pit area"}

SAFETY_CAR_STATUS = {0: "No safety car", 1: "Full", 2: "Virtual",
                     3: "Formation lap"}

SAFETY_CAR_EVENT_TYPE = {0: "Deployed", 1: "Returning", 2: "Returned",
                         3: "Resume race"}

FIA_FLAGS = {-1: "Invalid/unknown", 0: "None", 1: "Green", 2: "Blue",
             3: "Yellow"}

PLATFORMS = {1: "Steam", 3: "PlayStation", 4: "Xbox", 6: "Origin",
             255: "Unknown"}

PENALTY_TYPES = {
    0: "Drive through", 1: "Stop Go", 2: "Grid penalty",
    3: "Penalty reminder", 4: "Time penalty", 5: "Warning", 6: "Disqualified",
    7: "Removed from formation lap", 8: "Parked too long timer",
    9: "Tyre regulations", 10: "This lap invalidated",
    11: "This and next lap invalidated", 12: "This lap invalidated without reason",
    13: "This and next lap invalidated without reason",
    14: "This and previous lap invalidated",
    15: "This and previous lap invalidated without reason",
    16: "Retired", 17: "Black flag timer",
}

INFRINGEMENT_TYPES = {
    0: "Blocking by slow driving", 1: "Blocking by wrong way driving",
    2: "Reversing off the start line", 3: "Big collision", 4: "Small collision",
    5: "Collision failed to hand back position single",
    6: "Collision failed to hand back position multiple",
    7: "Corner cutting gained time", 8: "Corner cutting overtake single",
    9: "Corner cutting overtake multiple", 10: "Crossed pit exit lane",
    11: "Ignoring blue flags", 12: "Ignoring yellow flags",
    13: "Ignoring drive through", 14: "Too many drive throughs",
    15: "Drive through reminder serve within n laps",
    16: "Drive through reminder serve this lap", 17: "Pit lane speeding",
    18: "Parked for too long", 19: "Ignoring tyre regulations",
    20: "Too many penalties", 21: "Multiple warnings",
    22: "Approaching disqualification", 23: "Tyre regulations select single",
    24: "Tyre regulations select multiple",
    25: "Lap invalidated corner cutting", 26: "Lap invalidated running wide",
    27: "Corner cutting ran wide gained time minor",
    28: "Corner cutting ran wide gained time significant",
    29: "Corner cutting ran wide gained time extreme",
    30: "Lap invalidated wall riding", 31: "Lap invalidated flashback used",
    32: "Lap invalidated reset to track", 33: "Blocking the pitlane",
    34: "Jump start", 35: "Safety car to car collision",
    36: "Safety car illegal overtake", 37: "Safety car exceeding allowed pace",
    38: "Virtual safety car exceeding allowed pace",
    39: "Formation lap below allowed speed", 40: "Formation lap parking",
    41: "Retired mechanical failure", 42: "Retired terminally damaged",
    43: "Safety car falling too far back", 44: "Black flag timer",
    45: "Unserved stop go penalty", 46: "Unserved drive through penalty",
    47: "Engine component change", 48: "Gearbox change", 49: "Parc Ferme change",
    50: "League grid penalty", 51: "Retry penalty", 52: "Illegal time gain",
    53: "Mandatory pitstop", 54: "Attribute assigned",
}

BUTTON_FLAGS = {
    0x00000001: "Cross or A", 0x00000002: "Triangle or Y",
    0x00000004: "Circle or B", 0x00000008: "Square or X",
    0x00000010: "D-pad Left", 0x00000020: "D-pad Right",
    0x00000040: "D-pad Up", 0x00000080: "D-pad Down",
    0x00000100: "Options or Menu", 0x00000200: "L1 or LB",
    0x00000400: "R1 or RB", 0x00000800: "L2 or LT", 0x00001000: "R2 or RT",
    0x00002000: "Left Stick Click", 0x00004000: "Right Stick Click",
    0x00008000: "Right Stick Left", 0x00010000: "Right Stick Right",
    0x00020000: "Right Stick Up", 0x00040000: "Right Stick Down",
    0x00080000: "Special",
    **{0x00100000 << i: f"UDP Action {i + 1}" for i in range(12)},
}


def _lookup(table, key, label):
    return table.get(key, f"{label} {key}")


def team_name(team_id, packet_format=2026):
    if team_id == NO_TEAM_SELECTED.get(packet_format):
        return "No team"
    return _lookup(TEAMS, team_id, "Team")


def driver_name(driver_id, participant_name=None, packet_format=2026):
    """Resolve a driver, preferring the participant packet's name for humans."""
    if driver_id == NETWORK_HUMAN_DRIVER_ID.get(packet_format):
        return participant_name or "Human player"
    return participant_name or _lookup(DRIVERS, driver_id, "Driver")


def track_name(track_id):
    return "Unknown" if track_id < 0 else _lookup(TRACKS, track_id, "Track")


def tyre_name(actual_compound, visual_compound=None):
    """e.g. 'C3 (Medium)' - the pairing is what strategy tools actually need."""
    actual = _lookup(ACTUAL_TYRE_COMPOUNDS, actual_compound, "Compound")
    if visual_compound is None:
        return actual
    return f"{actual} ({_lookup(VISUAL_TYRE_COMPOUNDS, visual_compound, 'Visual')})"


def buttons_pressed(button_status):
    """Decode a BUTN event's bitmask into a list of button names."""
    return [name for bit, name in BUTTON_FLAGS.items() if button_status & bit]
