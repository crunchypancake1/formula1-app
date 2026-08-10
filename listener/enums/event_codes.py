from enum import Enum


class EventCodes(Enum):
    SESSION_STARTED = "SSTA"           # Sent when the session starts
    SESSION_ENDED = "SEND"             # Sent when the session ends
    FASTEST_LAP = "FTLP"               # When a driver achieves the fastest lap
    RETIREMENT = "RTMT"                # When a driver retires
    DRS_ENABLED = "DRSE"               # Race control has enabled DRS
    DRS_DISABLED = "DRSD"              # Race control has disabled DRS
    TEAM_MATE_IN_PITS = "TMPT"         # Your team mate has entered the pits
    CHEQUERED_FLAG = "CHQF"            # The chequered flag has been waved
    RACE_WINNER = "RCWN"               # The race winner is announced
    PENALTY_ISSUED = "PENA"            # A penalty has been issued – details in event
    SPEED_TRAP_TRIGGERED = "SPTP"      # Speed trap has been triggered by fastest speed
    START_LIGHTS = "STLG"              # Start lights – number shown
    LIGHTS_OUT = "LGOT"               # Lights out
    DRIVE_THROUGH_SERVED = "DTSV"      # Drive through penalty served
    STOP_GO_SERVED = "SGSV"            # Stop go penalty served
    FLASHBACK = "FLBK"                 # Flashback activated
    BUTTON_STATUS = "BUTN"             # Button status changed
    RED_FLAG = "RDFL"                  # Red flag shown
    OVERTAKE = "OVTK"                  # Overtake occurred
    SAFETY_CAR = "SCAR"                # Safety car event – details in event
    COLLISION = "COLL"                 # Collision between two vehicles has occurred
