"""Race scenario generator — produces a full sequence of binary packets for a simulated 3-lap race."""

from packets.constants import MAX_CARS

from .packet_builder import (
    build_car_damage_packet,
    build_car_status_packet,
    build_car_telemetry2_packet,
    build_car_telemetry_packet,
    build_event_chqf,
    build_event_coll,
    build_event_ftlp,
    build_event_ovtk,
    build_event_pena,
    build_event_rcwn,
    build_event_scar,
    build_event_send,
    build_event_sptp,
    build_event_ssta,
    build_final_classification_packet,
    build_lap_data_packet,
    build_lap_positions_packet,
    build_motion_packet,
    build_participants_packet,
    build_session_history_packet,
    build_session_packet,
)

SESSION_UID = 9999999999999999
TRACK_ID = 11          # Monza
SESSION_TYPE = 15      # Race
TOTAL_LAPS = 3
TRACK_LENGTH = 5793
NUM_DRIVERS = 24
FRAME_INTERVAL = 0.016  # ~60Hz

# Cars whose driver has Your Telemetry set to Restricted. The game zeroes their
# fuel/ERS/damage in our stream, so these indices drive the withheld-data paths
# end to end: NULL car-status extras and no car_frame_damage row at all.
RESTRICTED_CAR_INDICES = {3, 7}


class _FrameCounter:
    """Auto-incrementing frame counter with session_time tracking."""

    def __init__(self):
        self._frame = 0

    def next(self) -> tuple[int, float]:
        self._frame += 1
        return self._frame, (self._frame - 1) * FRAME_INTERVAL

    @property
    def current(self) -> int:
        return self._frame


def _build_frame_packets(
    fc: _FrameCounter,
    current_lap: int,
    lap_distance: float,
    positions: list[int],
    include_session: bool = False,
    session_time_left: int = 3600,
) -> list[bytes]:
    """Build the standard set of packets for a single frame.

    Includes a Car Damage packet at ~10Hz (every 6th frame).
    """
    frame_id, session_time = fc.next()
    packets = []

    if include_session:
        packets.append(build_session_packet(
            session_uid=SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            track_id=TRACK_ID,
            session_type=SESSION_TYPE,
            total_laps=TOTAL_LAPS,
            track_length=TRACK_LENGTH,
            session_time_left=session_time_left,
        ))

    packets.append(build_lap_data_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        current_lap_num=current_lap,
        lap_distance=lap_distance,
        track_length=TRACK_LENGTH,
        positions=positions,
    ))

    packets.append(build_motion_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        lap_distance=lap_distance,
        track_length=TRACK_LENGTH,
    ))

    packets.append(build_car_telemetry_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    packets.append(build_car_status_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    packets.append(build_car_telemetry2_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    # Car Damage at ~10Hz (every 6th frame of the 60Hz main loop)
    if frame_id % 6 == 0:
        tyre_wear = 5.0 + (current_lap - 1) * 2.0
        packets.append(build_car_damage_packet(
            session_uid=SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            num_drivers=NUM_DRIVERS,
            tyre_wear_pct=tyre_wear,
        ))

    return packets


def generate_race_scenario() -> list[bytes]:
    """
    Generate a complete 3-lap race packet sequence.

    Returns a list of raw binary packets in chronological order, suitable
    for feeding directly to dispatcher.handle_packet().
    """
    packets = []
    fc = _FrameCounter()
    positions = list(range(1, NUM_DRIVERS + 1))

    # === Frame 1: Session init ===
    frame_id, session_time = fc.next()

    packets.append(build_session_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        track_id=TRACK_ID,
        session_type=SESSION_TYPE,
        total_laps=TOTAL_LAPS,
        track_length=TRACK_LENGTH,
    ))

    packets.append(build_participants_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        restricted_indices=RESTRICTED_CAR_INDICES,
    ))

    packets.append(build_lap_data_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        current_lap_num=1,
        lap_distance=0.0,
        track_length=TRACK_LENGTH,
        positions=positions,
    ))

    packets.append(build_motion_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        lap_distance=0.0,
    ))

    packets.append(build_car_telemetry_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    packets.append(build_car_status_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
    ))

    packets.append(build_event_ssta(SESSION_UID, session_time, frame_id))

    # === Formation lap end → race start (SCAR safety_car_type=3, event_type=3) ===
    packets.append(build_event_scar(SESSION_UID, session_time, frame_id))

    # === Frames 2-29: Regular lap 1 frames ===
    for i in range(28):
        progress = (i + 1) / 29
        lap_distance = progress * (TRACK_LENGTH - 1)
        include_session = (i == 13)

        packets.extend(_build_frame_packets(
            fc=fc,
            current_lap=1,
            lap_distance=lap_distance,
            positions=positions,
            include_session=include_session,
        ))

    # === Lap 1→2 transition with session update + events ===
    swapped_positions = list(positions)
    swapped_positions[0] = 2
    swapped_positions[1] = 1

    frame_id, session_time = fc.next()
    packets.extend([
        build_session_packet(SESSION_UID, session_time, frame_id, TRACK_ID, SESSION_TYPE, TOTAL_LAPS, TRACK_LENGTH, 3500),
        build_lap_data_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, 2, 50.0, TRACK_LENGTH, swapped_positions),
        build_motion_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, 50.0),
        build_car_telemetry_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_car_status_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_event_ovtk(SESSION_UID, session_time, frame_id, 1, 0),
        build_event_sptp(SESSION_UID, session_time, frame_id, 0, 312.5),
    ])

    # === Session history for all cars (lap 1) — one frame per car ===
    for car_idx in range(NUM_DRIVERS):
        frame_id, session_time = fc.next()
        packets.append(build_session_history_packet(
            session_uid=SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            car_index=car_idx,
            num_laps=1,
            lap_times_ms=[88000 + car_idx * 500],
        ))

    # === Lap positions (lap 1) ===
    frame_id, session_time = fc.next()
    lap1_positions = {0: positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS)}
    packets.append(build_lap_positions_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        lap_positions=lap1_positions,
        lap_start=0,
    ))

    # === Lap 2 frames ===
    for i in range(27):
        progress = (i + 1) / 28
        lap_distance = progress * (TRACK_LENGTH - 1)
        include_session = (i == 13)

        packets.extend(_build_frame_packets(
            fc=fc,
            current_lap=2,
            lap_distance=lap_distance,
            positions=swapped_positions,
            include_session=include_session,
        ))

    # === Lap 2→3 transition with events ===
    frame_id, session_time = fc.next()
    packets.extend([
        build_session_packet(SESSION_UID, session_time, frame_id, TRACK_ID, SESSION_TYPE, TOTAL_LAPS, TRACK_LENGTH, 3400),
        build_lap_data_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, 3, 50.0, TRACK_LENGTH, swapped_positions),
        build_motion_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, 50.0),
        build_car_telemetry_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_car_status_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_event_ftlp(SESSION_UID, session_time, frame_id, 0, 87.5),
        build_event_pena(SESSION_UID, session_time, frame_id, 5, 6),
        build_event_coll(SESSION_UID, session_time, frame_id, 3, 4),
    ])

    # === Session history for all cars (lap 2) — one frame per car ===
    for car_idx in range(NUM_DRIVERS):
        frame_id, session_time = fc.next()
        packets.append(build_session_history_packet(
            session_uid=SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            car_index=car_idx,
            num_laps=2,
            lap_times_ms=[
                88000 + car_idx * 500,
                87500 + car_idx * 500,
            ],
        ))

    # === Lap positions (lap 2) ===
    frame_id, session_time = fc.next()
    lap2_positions = {
        0: positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS),
        1: swapped_positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS),
    }
    packets.append(build_lap_positions_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        lap_positions=lap2_positions,
        lap_start=0,
    ))

    # === Lap 3 frames ===
    for i in range(27):
        progress = (i + 1) / 28
        lap_distance = progress * (TRACK_LENGTH - 1)
        include_session = (i == 13)

        packets.extend(_build_frame_packets(
            fc=fc,
            current_lap=3,
            lap_distance=lap_distance,
            positions=swapped_positions,
            include_session=include_session,
        ))

    # === Chequered flag ===
    frame_id, session_time = fc.next()
    packets.extend([
        build_lap_data_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, 3, TRACK_LENGTH - 10, TRACK_LENGTH, swapped_positions),
        build_motion_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS, TRACK_LENGTH - 10),
        build_car_telemetry_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_car_status_packet(SESSION_UID, session_time, frame_id, NUM_DRIVERS),
        build_event_chqf(SESSION_UID, session_time, frame_id),
    ])

    # === Final session history (lap 3) — one frame per car ===
    for car_idx in range(NUM_DRIVERS):
        frame_id, session_time = fc.next()
        packets.append(build_session_history_packet(
            session_uid=SESSION_UID,
            session_time=session_time,
            frame_id=frame_id,
            car_index=car_idx,
            num_laps=3,
            lap_times_ms=[
                88000 + car_idx * 500,
                87500 + car_idx * 500,
                87000 + car_idx * 500,
            ],
        ))

    # === Final lap positions (lap 3) ===
    frame_id, session_time = fc.next()
    lap3_positions = {
        0: positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS),
        1: swapped_positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS),
        2: swapped_positions[:NUM_DRIVERS] + [0] * (MAX_CARS - NUM_DRIVERS),
    }
    packets.append(build_lap_positions_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        lap_positions=lap3_positions,
        lap_start=0,
    ))

    # === Race winner + Final Classification ===
    frame_id, session_time = fc.next()
    packets.append(build_event_rcwn(SESSION_UID, session_time, frame_id, 1))
    packets.append(build_final_classification_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        total_laps=TOTAL_LAPS,
    ))

    # === Session end ===
    frame_id, session_time = fc.next()
    packets.append(build_event_send(SESSION_UID, session_time, frame_id))

    # === Dummy flush trigger ===
    frame_id, session_time = fc.next()
    packets.append(build_lap_data_packet(
        session_uid=SESSION_UID,
        session_time=session_time,
        frame_id=frame_id,
        num_drivers=NUM_DRIVERS,
        current_lap_num=3,
        lap_distance=0.0,
    ))

    return packets
