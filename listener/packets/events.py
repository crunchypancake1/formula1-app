import logging
import struct
from dataclasses import dataclass
from typing import Union

from enums import ButtonFlags, EventCodes

from .packet_header import PacketHeader

logger = logging.getLogger("telemetry.events")


_FASTEST_LAP_FORMAT = '<Bf'
_FASTEST_LAP_FORMAT_SIZE = struct.calcsize(_FASTEST_LAP_FORMAT)
@dataclass
class FastestLap:
    vehicle_index: int                  # uint8     |   Vehicle index of car achieving fastest lap
    lap_time: float                     # float     |   Lap time is in seconds

_RETIREMENT_FORMAT = '<BB'
_RETIREMENT_FORMAT_SIZE = struct.calcsize(_RETIREMENT_FORMAT)
@dataclass
class Retirement:
    vehicle_index: int                  # uint8     |   Vehicle index of car retiring
    reason: int                         # uint8     |   Reason - 0 = invalid, 1 = retired, 2 = finished, 3 = terminal damage, 4 = inactive, 5 = not enough laps completed
                                        #           |   6 = black flagged, 7 = red flagged, 8 = mechanical failure, 9 = session skipped, 10 = session simulated

_TEAM_MATE_IN_PITS_FORMAT = '<B'
_TEAM_MATE_IN_PITS_FORMAT_SIZE = struct.calcsize(_TEAM_MATE_IN_PITS_FORMAT)
@dataclass
class TeamMateInPits:
    vehicle_index: int                  # uint8     |   Vehicle index of team mate

_RACE_WINNER_FORMAT = '<B'
_RACE_WINNER_FORMAT_SIZE = struct.calcsize(_RACE_WINNER_FORMAT)
@dataclass
class RaceWinner:
    vehicle_index: int                  # uint8     |   Vehicle index of the race winner

_PENALTY_FORMAT = '<7B'
_PENALTY_FORMAT_SIZE = struct.calcsize(_PENALTY_FORMAT)
@dataclass
class Penalty:
    penalty_type: int                   # uint8     |   Penalty type – see Appendices
    infringement_type: int              # uint8     |   Infringement type – see Appendices
    vehicle_index: int                  # uint8     |   Vehicle index of the car the penalty is applied to
    other_vehicle_index: int            # uint8     |   Vehicle index of the other car involved
    time: int                           # uint8     |   Time gained, or time spent doing action in seconds
    lap_num: int                        # uint8     |   Lap the penalty occurred on
    places_gained: int                  # uint8     |   Number of places gained by this

_SPEED_TRAP_FORMAT = '<Bf3Bf'
_SPEED_TRAP_FORMAT_SIZE = struct.calcsize(_SPEED_TRAP_FORMAT)
@dataclass
class SpeedTrap:
    vehicle_index: int                  # uint8     |   Vehicle index of the vehicle triggering speed trap
    speed: float                        # float     |   Top speed achieved in kilometres per hour
    is_overall_fastest_in_session: int  # uint8     |   Overall fastest speed in session = 1, otherwise 0
    is_driver_fastest_in_session: int   # uint8     |   Fastest speed for driver in session = 1, otherwise 0
    fastest_vehicle_index_in_session: int # uint8     |   Vehicle index of the vehicle that is the fastest in this session
    fastest_speed_in_session: float     # float     |   Speed of the vehicle that is the fastest in this session

_START_LIGHTS_FORMAT = '<B'
_START_LIGHTS_FORMAT_SIZE = struct.calcsize(_START_LIGHTS_FORMAT)
@dataclass
class StartLights:
    num_of_lights: int                  # uint8     |   Number of lights showing

_DRIVE_THROUGH_PENALTY_SERVED_FORMAT = '<B'
_DRIVE_THROUGH_PENALTY_SERVED_FORMAT_SIZE = struct.calcsize(_DRIVE_THROUGH_PENALTY_SERVED_FORMAT)
@dataclass
class DriveThroughPenaltyServed:
    vehicle_index: int                  # uint8     |   Vehicle index of the vehicle serving drive through

_STOP_GO_PENALTY_SERVED_FORMAT = '<Bf'
_STOP_GO_PENALTY_SERVED_FORMAT_SIZE = struct.calcsize(_STOP_GO_PENALTY_SERVED_FORMAT)
@dataclass
class StopGoPenaltyServed:
    vehicle_index: int                  # uint8     |   Vehicle index of the vehicle serving stop go
    stop_time: float                    # float     |   Time spent serving stop go in seconds

_FLASHBACK_FORMAT = '<If'
_FLASHBACK_FORMAT_SIZE = struct.calcsize(_FLASHBACK_FORMAT)
@dataclass
class Flashback:
    flashback_frame_identifier: int     # uint32    |   Frame identifier flashed back to
    flashback_session_time: float       # float     |   Session time flashed back to

_BUTTONS_FORMAT = '<I'
_BUTTONS_FORMAT_SIZE = struct.calcsize(_BUTTONS_FORMAT)
@dataclass
class Buttons:
    button_status: int                  # uint32    |   Bit flags specifying which buttons are being pressed

_OVERTAKE_FORMAT = '<2B'
_OVERTAKE_FORMAT_SIZE = struct.calcsize(_OVERTAKE_FORMAT)
@dataclass
class Overtake:
    overtaking_vehicle_index: int       # uint8     |   Vehicle index of the vehicle overtaking
    being_overtaken_vehicle_index: int  # uint8     |   Vehicle index of the vehicle being overtaken

_SAFETY_CAR_FORMAT = '<2B'
_SAFETY_CAR_FORMAT_SIZE = struct.calcsize(_SAFETY_CAR_FORMAT)
@dataclass
class SafetyCar:
    safety_car_type: int                # uint8     |   0 = No Safety Car, 1 = Full Safety Car, 2 = Virtual Safety Car, 3 = Formation Lap Safety Car
    event_type: int                     # uint8     |   0 = Deployed, 1 = Returning, 2 = Returned, 3 = Resume Race

_COLLISION_FORMAT = '<3B'
_COLLISION_FORMAT_SIZE = struct.calcsize(_COLLISION_FORMAT)
@dataclass
class Collision:
    vehicle_1_index: int                # uint8     |   Vehicle index of the first vehicle involved in the collision
    vehicle_2_index: int                # uint8     |   Vehicle index of the second vehicle involved in the collision
    severity: int                       # uint8     |   Collision severity - 0 = low, 1 = medium, 2 = high

_EVENT_STRING_CODE_FORMAT = '<4B'
_EVENT_STRING_CODE_FORMAT_SIZE = struct.calcsize(_EVENT_STRING_CODE_FORMAT)

_DRS_DISABLED_FORMAT = '<B'
_DRS_DISABLED_FORMAT_SIZE = struct.calcsize(_DRS_DISABLED_FORMAT)

@dataclass
class DrsDisabled:
    reason: int                         # uint8     |   0 = Wet track, 1 = Safety car deployed, 2 = Red flag, 3 = Min lap not reached
@dataclass
class EventPacket:
    header: PacketHeader                #           |   Header
    event_string_code: str              # uint8[4]  |   Event string code (decoded ASCII)
    event: Union[
        FastestLap,
        Retirement,
        DrsDisabled,
        TeamMateInPits,
        RaceWinner,
        Penalty,
        SpeedTrap,
        StartLights,
        DriveThroughPenaltyServed,
        StopGoPenaltyServed,
        Flashback,
        Buttons,
        Overtake,
        SafetyCar,
        Collision,
        None,
    ]

def unpack_event_packet(packet_header: PacketHeader, data: bytes) -> 'EventPacket':
    """
    Unpack Event packet (Packet ID: 3).

    Contains various race control events like fastest lap, penalties, retirements,
    safety car, DRS status, etc. Event type determined by 4-character code.

    Args:
        packet_header: Unpacked packet header
        data: Packet body bytes

    Returns:
        EventPacket with event code and event-specific details
    """
    event_string_code_bytes = data[:_EVENT_STRING_CODE_FORMAT_SIZE]
    unpacked_event_string_code = struct.unpack(_EVENT_STRING_CODE_FORMAT, event_string_code_bytes)

    event_string_code = bytes(unpacked_event_string_code).decode('ascii')

    event_bytes = data[_EVENT_STRING_CODE_FORMAT_SIZE:]
    event = None

    match event_string_code:
        case EventCodes.FASTEST_LAP.value:
            event = FastestLap(*struct.unpack(_FASTEST_LAP_FORMAT, event_bytes[:_FASTEST_LAP_FORMAT_SIZE]))

        case EventCodes.RETIREMENT.value:
            event = Retirement(*struct.unpack(_RETIREMENT_FORMAT, event_bytes[:_RETIREMENT_FORMAT_SIZE]))

        case EventCodes.DRS_ENABLED.value:
            pass

        case EventCodes.DRS_DISABLED.value:
            event = DrsDisabled(*struct.unpack(_DRS_DISABLED_FORMAT, event_bytes[:_DRS_DISABLED_FORMAT_SIZE]))

        case EventCodes.TEAM_MATE_IN_PITS.value:
            event = TeamMateInPits(*struct.unpack(_TEAM_MATE_IN_PITS_FORMAT, event_bytes[:_TEAM_MATE_IN_PITS_FORMAT_SIZE]))

        case EventCodes.RACE_WINNER.value:
            event = RaceWinner(*struct.unpack(_RACE_WINNER_FORMAT, event_bytes[:_RACE_WINNER_FORMAT_SIZE]))

        case EventCodes.PENALTY_ISSUED.value:
            event = Penalty(*struct.unpack(_PENALTY_FORMAT, event_bytes[:_PENALTY_FORMAT_SIZE]))

        case EventCodes.SPEED_TRAP_TRIGGERED.value:
            event = SpeedTrap(*struct.unpack(_SPEED_TRAP_FORMAT, event_bytes[:_SPEED_TRAP_FORMAT_SIZE]))

        case EventCodes.START_LIGHTS.value:
            event = StartLights(*struct.unpack(_START_LIGHTS_FORMAT, event_bytes[:_START_LIGHTS_FORMAT_SIZE]))

        case EventCodes.LIGHTS_OUT.value:
            pass

        case EventCodes.DRIVE_THROUGH_SERVED.value:
            event = DriveThroughPenaltyServed(*struct.unpack(_DRIVE_THROUGH_PENALTY_SERVED_FORMAT, event_bytes[:_DRIVE_THROUGH_PENALTY_SERVED_FORMAT_SIZE]))

        case EventCodes.STOP_GO_SERVED.value:
            event = StopGoPenaltyServed(*struct.unpack(_STOP_GO_PENALTY_SERVED_FORMAT, event_bytes[:_STOP_GO_PENALTY_SERVED_FORMAT_SIZE]))

        case EventCodes.FLASHBACK.value:
            event = Flashback(*struct.unpack(_FLASHBACK_FORMAT, event_bytes[:_FLASHBACK_FORMAT_SIZE]))

        case EventCodes.RED_FLAG.value:
            pass

        case EventCodes.OVERTAKE.value:
            event = Overtake(*struct.unpack(_OVERTAKE_FORMAT, event_bytes[:_OVERTAKE_FORMAT_SIZE]))

        case EventCodes.SAFETY_CAR.value:
            event = SafetyCar(*struct.unpack(_SAFETY_CAR_FORMAT, event_bytes[:_SAFETY_CAR_FORMAT_SIZE]))

        case EventCodes.SESSION_STARTED.value:
            pass

        case EventCodes.SESSION_ENDED.value:
            pass

        case EventCodes.CHEQUERED_FLAG.value:
            pass

        case EventCodes.COLLISION.value:
            event = Collision(*struct.unpack(_COLLISION_FORMAT, event_bytes[:_COLLISION_FORMAT_SIZE]))

        case EventCodes.BUTTON_STATUS.value:
            event = Buttons(*struct.unpack(_BUTTONS_FORMAT, event_bytes[:_BUTTONS_FORMAT_SIZE]))
            pressed_buttons = [flag.name for flag in ButtonFlags if flag & event.button_status]
            logger.debug("Buttons pressed: %s", pressed_buttons)

        case _:
            try:
                event_name = EventCodes(event_string_code).name
            except ValueError:
                event_name = f"UNKNOWN_{event_string_code}"
            logger.warning("Event received but not implemented: %s", event_name)

    return EventPacket(packet_header, event_string_code, event)
